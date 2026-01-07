import json
import requests
import sys
import os
from typing import Optional, Dict, Any
from pathlib import Path
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from common import setup_logging, Config, ActionError, ArticleType
from qbraid_core import QbraidSessionV1

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
                        if "GITHUB_OUTPUT" in os.environ:
                            try:
                                with open(os.environ["GITHUB_OUTPUT"], "a") as f:
                                    f.write(f"course_custom_id={course_id}\n")
                            except IOError as e:
                                logger.warning(f"Failed to write to GITHUB_OUTPUT: {e}")
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


if __name__ == "__main__":
    if len(sys.argv) < 7:
        logger.error(
            "Usage: python create_course.py <api_key> <article_type> "
            "<force_duplicate_questions> <repo_read_token> <repo_url> <commit_sha>"
        )
        sys.exit(1)

    create_course(
        sys.argv[1],
        sys.argv[2],
        sys.argv[3],
        sys.argv[4],
        sys.argv[5],
        sys.argv[6].lower() == "true",
    )
