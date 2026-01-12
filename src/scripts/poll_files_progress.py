# Copyright (C) 2026 qBraid

import os
import sys
import time
from enum import Enum
from typing import Any, Dict

import requests
from common import (
    ActionError,
    Config,
    PollTimeoutError,
    WorkerProcessingError,
    setup_logging,
)
from qbraid_core import QbraidSessionV1
from tenacity import (
    RetryError,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_fixed,
)

logger = setup_logging(__name__)


class ProcessingStatus(Enum):
    UNPROCESSED = "unprocessed"
    PROCESSING = "processing"
    FAILED = "failed"
    PROCESSED = "processed"
    UNKNOWN = "unknown"

    @classmethod
    def _missing_(cls, value):
        return cls.UNKNOWN


class ProgressPoller:
    """Manages polling of the course file processing status."""

    def __init__(self, api_key: str, course_custom_id: str):
        self.api_key = api_key
        self.course_custom_id = course_custom_id
        self.url = f"/learn/articles/files/status/{course_custom_id}"
        self.headers = {"X-API-Key": api_key}
        self.session = QbraidSessionV1(api_key=api_key)
        self.session.base_url = Config.API_BASE_URL

    @retry(
        stop=stop_after_attempt(Config.MAX_CONSECUTIVE_ERRORS),
        wait=wait_fixed(3),  # Short retry wait to distinguish from polling interval
        retry=retry_if_exception_type((requests.RequestException,)),
        reraise=True,
    )
    def fetch_status(self) -> Dict[str, Any]:
        """Fetch status from API with retries."""
        response = self.session.get(
            self.url, headers=self.headers, timeout=Config.REQUEST_TIMEOUT_SECONDS
        )
        if response.status_code != 200:
            raise requests.RequestException(f"Status code {response.status_code}")
        return response.json()

    def run(self) -> None:
        """
        Polls the status of course file processing.
        Raises:
            ActionError: On polling errors or retry exhaustion.
            WorkerProcessingError: When course processing fails.
            PollTimeoutError: When polling times out.
            SystemExit: On success (exit code 0).
        """
        for attempt in range(1, Config.MAX_POLL_ATTEMPTS + 1):
            try:
                # Use self.class.fetch_status or ProgressPoller.fetch_status if static
                data = self.fetch_status()

                # Check for qBook URL (success indicator)
                if "qbookUrl" in data:
                    qbook_url = data["qbookUrl"]
                    logger.info("✅ Course processing complete!")
                    logger.info(f"qBook URL: {qbook_url}")

                    from common import write_github_output
                    write_github_output("qbook_url", str(qbook_url))

                    # qBook URL is treated as a success indicator; stop polling.
                    sys.exit(0)

                status = ProcessingStatus(data.get("status", "unknown"))

                if status == ProcessingStatus.PROCESSED:
                    logger.info("✅ Course processing complete!")
                    sys.exit(0)
                elif status == ProcessingStatus.FAILED:
                    raise WorkerProcessingError(
                        "Course file processing failed. Please check the logs or contact contact@qbraid.com"
                    )
                elif status == ProcessingStatus.UNPROCESSED:
                    logger.info(
                        f"Attempt {attempt}/{Config.MAX_POLL_ATTEMPTS}: Course files are unprocessed..."
                    )
                elif status == ProcessingStatus.PROCESSING:
                    logger.info(
                        f"Attempt {attempt}/{Config.MAX_POLL_ATTEMPTS}: Course files are still being processed..."
                    )
                else:
                    logger.warning(
                        f"Attempt {attempt}/{Config.MAX_POLL_ATTEMPTS}: Unknown status '{data.get('status')}'"
                    )

            except RetryError:
                logger.error("Too many consecutive errors polling worker.")
                raise ActionError("Too many consecutive errors polling worker.")
            except WorkerProcessingError as e:
                logger.error(str(e))
                raise
            except Exception as e:
                # If it's already an ActionError, re-raise it
                if isinstance(e, ActionError):
                    raise
                logger.warning(f"Error polling worker: {e}")
                raise ActionError(f"Unexpected error polling worker: {e}")

            # Wait before next attempt if not finished
            if attempt < Config.MAX_POLL_ATTEMPTS:
                time.sleep(Config.POLL_INTERVAL_SECONDS)

        raise PollTimeoutError(
            f"Worker service did not complete within the timeout period "
            f"({Config.MAX_POLL_ATTEMPTS} attempts)"
        )


def poll_worker(api_key: str, course_custom_id: str):
    """Backwards compatibility wrapper."""
    try:
        poller = ProgressPoller(api_key, course_custom_id)
        poller.run()
    except (ActionError, WorkerProcessingError, PollTimeoutError) as e:
        logger.error(str(e))
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        logger.error(
            "Usage: python poll_files_progress.py <api_key> <course_custom_id>"
        )
        sys.exit(1)
    poll_worker(sys.argv[1], sys.argv[2])
