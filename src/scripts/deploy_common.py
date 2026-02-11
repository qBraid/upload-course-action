# Copyright (C) 2026 qBraid

import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import requests
from common import (
    ActionError,
    ArticleType,
    Config,
    ValidationError,
    setup_logging,
    write_github_output,
)
from qbraid_core import QbraidSessionV1
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

logger = setup_logging(__name__)


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


def validate_course_id(course_id: str) -> str:
    """Validate course ID is not empty."""
    if not course_id or not course_id.strip():
        raise ValidationError("Course ID cannot be empty")
    return course_id.strip()


class CourseDeployer:
    """Base class for handling course deployment (create or update) on qBraid."""

    def __init__(
        self,
        api_key: str,
        repo_read_token: str,
        repo_url: str,
        commit_sha: str,
        force_duplicate_questions: bool = True,
    ):
        self.api_key = api_key
        self.repo_read_token = repo_read_token
        self.repo_url = repo_url
        self.commit_sha = commit_sha
        self.force_duplicate_questions = force_duplicate_questions
        self.session = QbraidSessionV1(api_key=api_key)
        self.session.base_url = Config.API_BASE_URL

    def load_course_data(self) -> Dict[str, Any]:
        """Loads course data from the JSON file."""
        course_data_path = Path(Config.COURSE_DATA_FILE_NAME)
        if not course_data_path.exists():
            raise ActionError(
                f"{Config.COURSE_DATA_FILE_NAME} not found. Run validation first."
            )

        try:
            with open(course_data_path, "r") as f:
                return json.load(f)
        except Exception as e:
            raise ActionError(f"Failed to read {Config.COURSE_DATA_FILE_NAME}: {e}")

    def get_common_payload(self) -> Dict[str, Any]:
        """Returns the common payload parameters."""
        course_data = self.load_course_data()
        run_attempt = os.getenv("GITHUB_RUN_ATTEMPT")
        payload = {
            "data": course_data,
            "forceDuplicateQuestions": self.force_duplicate_questions,
            "repoReadToken": self.repo_read_token,
            "repoUrl": self.repo_url,
            "commitSha": self.commit_sha,
        }

        if run_attempt:
            try:
                payload["runAttempt"] = int(run_attempt)
            except ValueError:
                logger.warning(f"Invalid GITHUB_RUN_ATTEMPT value: {run_attempt}")

        return payload

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(2),
        retry=retry_if_exception_type((requests.RequestException,)),
        reraise=True,
    )
    def make_request(
        self, method: str, url: str, headers: Dict[str, str], payload: Dict[str, Any]
    ) -> requests.Response:
        """Make API request with retries."""
        response = self.session.request(
            method,
            url,
            data=json.dumps(payload),
            headers=headers,
            timeout=Config.REQUEST_TIMEOUT_SECONDS,
        )
        return response

    def handle_response(
        self, response: requests.Response, success_message: str
    ) -> None:
        """Handles the API response."""
        if response.status_code in [200, 201]:
            logger.info(success_message)
            try:
                resp_json = response.json()
                # Support both legacy payloads ({article: {...}})
                # and JSend payloads ({status: "success", data: {article: {...}}}).
                payload = resp_json.get("data", resp_json)
                course_id = payload.get("article", {}).get("customId")
                if course_id:
                    logger.info(f"Course ID: {course_id}")
                    write_github_output("course_name", str(course_id))
                    write_github_output("course_custom_id", str(course_id))
                else:
                    logger.warning(
                        "Course created/updated but customId was not found in response payload."
                    )
            except Exception:
                logger.warning("Could not parse API response JSON for course customId.")
        else:
            try:
                logger.error(f"Response: {response.text}")
            except Exception:
                pass
            raise ActionError(
                f"Operation failed. Status: {response.status_code}. Response: {response.text}"
            )
