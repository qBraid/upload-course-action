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


@dataclass(frozen=True)
class Config:
    """Application configuration constants."""

    # API Configuration
    DEFAULT_API_BASE_URL: str = "https://api-staging.qbraid.com/api/v1"
    API_BASE_URL: str = os.getenv("QBRAID_API_BASE_URL", DEFAULT_API_BASE_URL)
    REQUEST_TIMEOUT_SECONDS: int = 15
    MAX_POLL_ATTEMPTS: int = 60
    POLL_INTERVAL_SECONDS: int = 30
    MAX_CONSECUTIVE_ERRORS: int = 5

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
