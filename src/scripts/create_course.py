# Copyright (C) 2026 qBraid

import argparse
import json
import sys
from typing import Any, Dict, Optional

from common import ActionError, ArticleType, Config, ValidationError, setup_logging
from deploy_common import (
    CourseDeployer,
    build_certificate_settings,
    validate_api_key,
    validate_article_type,
    validate_boolean,
    validate_certificate_criteria_type,
    validate_certificate_criteria_value,
    validate_commit_sha,
    validate_repo_token,
    validate_repo_url,
)

logger = setup_logging(__name__)


class CourseCreator(CourseDeployer):
    """Handles course creation on qBraid."""

    def __init__(
        self,
        api_key: str,
        repo_read_token: str,
        repo_url: str,
        commit_sha: str,
        article_type: str = "course",
        force_duplicate_questions: bool = True,
        certificate_settings: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            api_key,
            repo_read_token,
            repo_url,
            commit_sha,
            article_type,
            force_duplicate_questions,
            certificate_settings,
        )
        try:
            self._article_type_enum = ArticleType(article_type)
        except ValueError:
            logger.warning(
                f"Invalid article type '{article_type}'. Defaulting to 'course'."
            )
            self._article_type_enum = ArticleType.COURSE
            self.article_type = "course"

    def run(self) -> None:
        """Creates a course on qBraid using the API."""
        logger.info(f"Creating article of type: {self._article_type_enum.value}")

        url = f"/learn/articles/{self._article_type_enum.value}/ingest"
        headers = {"X-API-Key": self.api_key, "Content-Type": "application/json"}
        payload = self.get_common_payload()

        try:
            response = self.make_request("POST", url, headers, payload)
            self.handle_response(
                response, "✅ Course created successfully via qBraid API"
            )
        except Exception as e:
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
    certificate_settings: Optional[Dict[str, Any]] = None,
):
    """Wrapper for execution."""
    creator = CourseCreator(
        api_key,
        repo_read_token,
        repo_url,
        commit_sha,
        article_type,
        force_duplicate_questions,
        certificate_settings,
    )
    try:
        creator.run()
    except ActionError as e:
        logger.error(str(e))
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create a course on qBraid")

    parser.add_argument("--api-key", required=True, type=validate_api_key)
    parser.add_argument("--repo-read-token", required=True, type=validate_repo_token)
    parser.add_argument("--repo-url", required=True, type=validate_repo_url)
    parser.add_argument("--commit-sha", required=True, type=validate_commit_sha)
    parser.add_argument("--article-type", required=True, type=validate_article_type)
    parser.add_argument(
        "--force-duplicate-questions", required=True, type=validate_boolean
    )
    parser.add_argument(
        "--certificate-enabled", required=False, type=validate_boolean, default=False
    )
    parser.add_argument(
        "--certificate-criteria-type",
        required=False,
        type=validate_certificate_criteria_type,
        default="completion",
    )
    parser.add_argument(
        "--certificate-criteria-value",
        required=False,
        type=validate_certificate_criteria_value,
        default=None,
    )

    try:
        args = parser.parse_args()
        certificate_settings = build_certificate_settings(
            args.certificate_enabled,
            args.certificate_criteria_type,
            args.certificate_criteria_value,
        )
        create_course(
            args.api_key,
            args.repo_read_token,
            args.repo_url,
            args.commit_sha,
            args.article_type,
            args.force_duplicate_questions,
            certificate_settings,
        )
    except (ValidationError, argparse.ArgumentError) as e:
        logger.error(f"Validation error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)
