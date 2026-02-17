# Copyright (C) 2026 qBraid

import logging
import os
import sys
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional, Set


# Configure Logging
def setup_logging(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


def _get_env_int(name: str, default: int) -> int:
    """Parse a positive integer from env vars, falling back to default."""
    value = os.getenv(name)
    if value is None:
        return default
    try:
        parsed = int(value)
        if parsed > 0:
            return parsed
    except ValueError:
        pass
    return default


@dataclass(frozen=True)
class Config:
    """Application configuration constants."""

    # API Configuration
    # DEFAULT_API_BASE_URL: str = "https://api-v2.qbraid.com/api/v1"
    DEFAULT_API_BASE_URL: str = "https://303a-117-213-58-151.ngrok-free.app/app1/api/v1"
    API_BASE_URL: str = os.getenv("QBRAID_API_BASE_URL", DEFAULT_API_BASE_URL)
    REQUEST_TIMEOUT_SECONDS: int = _get_env_int("QBRAID_REQUEST_TIMEOUT_SECONDS", 30)
    MAX_POLL_ATTEMPTS: int = _get_env_int("QBRAID_MAX_POLL_ATTEMPTS", 20)
    POLL_INTERVAL_SECONDS: int = _get_env_int("QBRAID_POLL_INTERVAL_SECONDS", 15)
    MAX_CONSECUTIVE_ERRORS: int = _get_env_int("QBRAID_MAX_CONSECUTIVE_ERRORS", 5)

    # Validation Configuration
    MAX_NOTEBOOK_SIZE_MB: int = 5
    MAX_IMAGE_SIZE_MB: int = 15
    VALID_DOMAINS: frozenset = frozenset({"qbraid.com", "quera.com"})

    # Paths
    COURSE_FILE_NAME: str = "course.json"
    COURSE_DATA_FILE_NAME: str = "course_data.json"


class ArticleType(str, Enum):
    """Enumeration of valid article types."""

    COURSE = "course"
    BLOG = "blog"


class ActionError(Exception):
    """Base exception for action failures."""

    pass


class ValidationError(ActionError):
    """Raised when validation fails."""

    pass


class AuthenticationError(ActionError):
    """Raised when authentication fails."""

    pass


class WorkerProcessingError(ActionError):
    """Raised when course processing fails."""

    pass


class PollTimeoutError(ActionError):
    """Raised when polling times out."""

    pass


def write_github_output(key: str, value: str) -> None:
    """
    Safely write a key-value pair to GITHUB_OUTPUT.

    Handles both single-line and multiline values. For multiline values,
    uses the delimiter syntax to prevent parsing errors.

    Args:
        key: The output key name
        value: The output value (may contain newlines)
    """
    if "GITHUB_OUTPUT" not in os.environ:
        return

    try:
        output_file = os.environ["GITHUB_OUTPUT"]

        # Check if value contains newlines
        if "\n" in value:
            # Use delimiter syntax for multiline values
            # Choose a unique delimiter that won't appear in the value
            delimiter = f"GITHUB_OUTPUT_DELIMITER_{key.upper()}"
            # Ensure delimiter doesn't appear in value
            while delimiter in value:
                delimiter = f"{delimiter}_ALT"

            with open(output_file, "a") as f:
                f.write(f"{key}<<{delimiter}\n")
                f.write(value)
                if not value.endswith("\n"):
                    f.write("\n")
                f.write(f"{delimiter}\n")
        else:
            # Simple key=value format for single-line values
            with open(output_file, "a") as f:
                f.write(f"{key}={value}\n")
    except (IOError, OSError) as e:
        # Use basic print to avoid circular import issues
        # This function may be called before logging is set up
        print(f"Warning: Failed to write to GITHUB_OUTPUT: {e}", file=sys.stderr)
