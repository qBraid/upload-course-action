# Copyright (C) 2026 qBraid

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import requests
from common import ActionError, ArticleType, Config, ValidationError, setup_logging
from qbraid_core import QbraidSessionV1
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

logger = setup_logging(__name__)


class CourseCreator:
    """Handles course creation on qBraid."""

    def __init__(
        self,
        api_key: str,
        repo_read_token: str,
        repo_url: str,
        commit_sha: str,
        article_type: str = "course",
        force_duplicate_questions: bool = True,
    ):
        self.api_key = api_key
        try:
            self.article_type = ArticleType(article_type)
        except ValueError:
            logger.warning(
                f"Invalid article type '{article_type}'. Defaulting to 'course'."
            )
            self.article_type = ArticleType.COURSE

        self.force_duplicate_questions = force_duplicate_questions
        self.repo_read_token = repo_read_token
        self.repo_url = repo_url
        self.commit_sha = commit_sha
        self.session = QbraidSessionV1(api_key=api_key)
        self.session.base_url = Config.API_BASE_URL

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(2),
        retry=retry_if_exception_type((requests.RequestException,)),
        reraise=True,
    )
    def post_course(
        self, url: str, headers: Dict[str, str], payload: Dict[str, Any]
    ) -> requests.Response:
        """Post course data with retries."""
        response = self.session.post(
            url,
            data=json.dumps(payload),
            headers=headers,
            timeout=Config.REQUEST_TIMEOUT_SECONDS,
        )
        return response

    def run(self) -> None:
        """
        Creates a course on qBraid using the API.
        Raises:
            ActionError: If creation fails.
        """
        if not self.repo_read_token or not self.repo_url or not self.commit_sha:
            raise ActionError(
                "repo_read_token, repo_url, and commit_sha must be provided."
            )

        course_data_path = Path(Config.COURSE_DATA_FILE_NAME)
        if not course_data_path.exists():
            raise ActionError(
                f"{Config.COURSE_DATA_FILE_NAME} not found. Run validation first."
            )

        try:
            with open(course_data_path, "r") as f:
                course_data = json.load(f)
        except Exception as e:
            raise ActionError(f"Failed to read {Config.COURSE_DATA_FILE_NAME}: {e}")

        logger.info(f"Creating article of type: {self.article_type.value}")

        # Call qBraid API to create course
        try:
            url = f"/learn/articles/{self.article_type.value}/ingest"
            payload = {
                "data": course_data,
                "forceDuplicateQuestions": self.force_duplicate_questions,
                "repoReadToken": self.repo_read_token,
                "repoUrl": self.repo_url,
                "commitSha": self.commit_sha,
            }
            headers = {"X-API-Key": self.api_key, "Content-Type": "application/json"}

            # Use static method
            response = self.post_course(url, headers, payload)

            if response.status_code in [200, 201]:
                logger.info("✅ Course created successfully via qBraid API")
                try:
                    resp_json = response.json()
                    course_id = resp_json.get("article", {}).get("customId")
                    if course_id:
                        logger.info(f"Course ID: {course_id}")
                        from common import write_github_output
                        write_github_output("course_name", str(course_id))
                        write_github_output("course_custom_id", str(course_id))
                except Exception:
                    pass
            else:
                try:
                    logger.error(f"Response: {response.text}")
                except Exception:
                    pass
                raise ActionError(
                    f"Failed to create course. Status: {response.status_code}"
                )

        except requests.RequestException as e:
            raise ActionError(f"Network error creating course: {e}")
        except Exception as e:
            # If it's already an ActionError, re-raise it
            if isinstance(e, ActionError):
                raise
            raise ActionError(f"Unexpected error creating course: {e}")


def create_course(
    api_key: str,
    repo_read_token: str,
    repo_url: str,
    commit_sha: str,
    article_type: str = "course",
    force_duplicate_questions: bool = True,
):
    """Wrapper for backwards compatibility."""
    creator = CourseCreator(
        api_key,
        repo_read_token,
        repo_url,
        commit_sha,
        article_type,
        force_duplicate_questions,
    )
    try:
        creator.run()
    except ActionError as e:
        logger.error(str(e))
        sys.exit(1)


def validate_api_key(api_key: str) -> str:
    """Validate API key is not empty."""
    if not api_key or not api_key.strip():
        raise ValidationError("API key cannot be empty")
    return api_key.strip()


def validate_article_type(article_type: str) -> str:
    """Validate article type is one of the allowed values."""
    if not article_type or not article_type.strip():
        raise ValidationError("Article type cannot be empty")
    article_type = article_type.strip().lower()
    try:
        ArticleType(article_type)
    except ValueError:
        valid_types = ", ".join([e.value for e in ArticleType])
        raise ValidationError(
            f"Invalid article type '{article_type}'. Must be one of: {valid_types}"
        )
    return article_type


def validate_boolean(value: str) -> bool:
    """Validate and convert string to boolean."""
    if not value:
        raise ValidationError("Boolean value cannot be empty")
    value_lower = value.strip().lower()
    if value_lower in ("true", "1", "yes", "on"):
        return True
    elif value_lower in ("false", "0", "no", "off"):
        return False
    else:
        raise ValidationError(
            f"Invalid boolean value '{value}'. Must be one of: true, false, 1, 0, yes, no, on, off"
        )


def validate_repo_token(token: str) -> str:
    """Validate repository read token is not empty."""
    if not token or not token.strip():
        raise ValidationError("Repository read token cannot be empty")
    return token.strip()


def validate_repo_url(url: str) -> str:
    """Validate repository URL format."""
    if not url or not url.strip():
        raise ValidationError("Repository URL cannot be empty")
    url = url.strip()
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise ValidationError(
            f"Invalid repository URL format '{url}'. Must be a valid URL (e.g., https://github.com/owner/repo)"
        )
    if parsed.scheme not in ("http", "https"):
        raise ValidationError(
            f"Repository URL must use http or https scheme, got: {parsed.scheme}"
        )
    return url


def validate_commit_sha(sha: str) -> str:
    """Validate commit SHA format (should be 40 hex characters for full SHA, or at least 7)."""
    if not sha or not sha.strip():
        raise ValidationError("Commit SHA cannot be empty")
    sha = sha.strip()
    # Git commit SHA can be 7-40 hex characters
    if not re.match(r"^[0-9a-fA-F]{7,40}$", sha):
        raise ValidationError(
            f"Invalid commit SHA format '{sha}'. Must be 7-40 hexadecimal characters"
        )
    return sha


if __name__ == "__main__":
    # Check if we're using positional arguments (backward compatibility)
    # Positional args: api_key repo_read_token repo_url commit_sha article_type force_duplicate_questions
    if len(sys.argv) > 1 and not sys.argv[1].startswith("--"):
        # Using positional arguments (for backward compatibility with action.yml)
        if len(sys.argv) < 7:
            logger.error(
                "Usage: python create_course.py <api_key> <repo_read_token> <repo_url> "
                "<commit_sha> <article_type> <force_duplicate_questions>"
            )
            logger.error("Or use named arguments: python create_course.py --help")
            sys.exit(1)

        try:
            api_key = validate_api_key(sys.argv[1])
            repo_read_token = validate_repo_token(sys.argv[2])
            repo_url = validate_repo_url(sys.argv[3])
            commit_sha = validate_commit_sha(sys.argv[4])
            article_type = validate_article_type(sys.argv[5])
            force_duplicate_questions = validate_boolean(sys.argv[6])
        except ValidationError as e:
            logger.error(f"Validation error: {e}")
            sys.exit(1)
    else:
        # Using named arguments (recommended)
        parser = argparse.ArgumentParser(
            description="Create a course/article on qBraid",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  python create_course.py --api-key KEY --article-type course --force-duplicate-questions true \\
      --repo-read-token TOKEN --repo-url https://github.com/owner/repo --commit-sha abc1234
            """,
        )
        parser.add_argument(
            "--api-key",
            required=True,
            type=validate_api_key,
            help="qBraid API key",
        )
        parser.add_argument(
            "--article-type",
            required=True,
            type=validate_article_type,
            help=f"Article type (one of: {', '.join([e.value for e in ArticleType])})",
        )
        parser.add_argument(
            "--force-duplicate-questions",
            required=True,
            type=validate_boolean,
            help="Force duplicate questions (true/false, 1/0, yes/no, on/off)",
        )
        parser.add_argument(
            "--repo-read-token",
            required=True,
            type=validate_repo_token,
            help="Repository read token",
        )
        parser.add_argument(
            "--repo-url",
            required=True,
            type=validate_repo_url,
            help="Repository URL (e.g., https://github.com/owner/repo)",
        )
        parser.add_argument(
            "--commit-sha",
            required=True,
            type=validate_commit_sha,
            help="Git commit SHA (7-40 hexadecimal characters)",
        )

        try:
            args = parser.parse_args()
            api_key = args.api_key
            repo_read_token = args.repo_read_token
            repo_url = args.repo_url
            commit_sha = args.commit_sha
            article_type = args.article_type
            force_duplicate_questions = args.force_duplicate_questions
        except (ValidationError, argparse.ArgumentError) as e:
            logger.error(f"Validation error: {e}")
            sys.exit(1)

    try:
        create_course(
            api_key,
            repo_read_token,
            repo_url,
            commit_sha,
            article_type,
            force_duplicate_questions,
        )
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)
