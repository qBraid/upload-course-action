# Copyright (C) 2026 qBraid

import argparse
import sys
from typing import Any, Dict, Optional

from common import ActionError, ArticleType, ValidationError, setup_logging
from deploy_common import (
    CourseDeployer,
    build_certificate_settings,
    validate_api_key,
    validate_article_type,
    validate_boolean,
    validate_certificate_criteria_type,
    validate_certificate_criteria_value,
    validate_commit_sha,
    validate_course_id,
    validate_repo_token,
    validate_repo_url,
)

logger = setup_logging(__name__)


class CourseUpdater(CourseDeployer):
    """Handles course update on qBraid."""

    def __init__(
        self,
        api_key: str,
        course_custom_id: str,
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
        self.course_custom_id = course_custom_id
        try:
            self._article_type_enum = ArticleType(article_type)
        except ValueError:
            logger.warning(
                f"Invalid article type '{article_type}'. Defaulting to 'course'."
            )
            self._article_type_enum = ArticleType.COURSE
            self.article_type = "course"

    def run(self) -> None:
        """Updates a course on qBraid using the API."""
        logger.info(
            f"Updating article: {self.course_custom_id} (type: {self._article_type_enum.value})"
        )

        # Taking a best guess at the update endpoint based on the creates endpoint structure
        # Create: /learn/articles/{type}/ingest
        # Update: /learn/articles/{type}/{id}
        url = f"/learn/articles/{self._article_type_enum.value}/{self.course_custom_id}"

        headers = {"X-API-Key": self.api_key, "Content-Type": "application/json"}
        payload = self.get_common_payload()

        try:
            response = self.make_request("PUT", url, headers, payload)
            self.handle_response(
                response, f"✅ Course {self.course_custom_id} updated successfully"
            )
        except Exception as e:
            if isinstance(e, ActionError):
                raise
            raise ActionError(f"Unexpected error updating course: {e}")


def update_course(
    api_key: str,
    course_custom_id: str,
    repo_read_token: str,
    repo_url: str,
    commit_sha: str,
    article_type: str = "course",
    force_duplicate_questions: bool = True,
    certificate_settings: Optional[Dict[str, Any]] = None,
):
    """Wrapper for execution."""
    updater = CourseUpdater(
        api_key,
        course_custom_id,
        repo_read_token,
        repo_url,
        commit_sha,
        article_type,
        force_duplicate_questions,
        certificate_settings,
    )
    try:
        updater.run()
    except ActionError as e:
        logger.error(str(e))
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update a course on qBraid")

    parser.add_argument("--api-key", required=True, type=validate_api_key)
    parser.add_argument("--course-custom-id", required=True, type=validate_course_id)
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
        update_course(
            args.api_key,
            args.course_custom_id,
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
