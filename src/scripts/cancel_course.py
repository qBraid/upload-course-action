# Copyright (C) 2026 qBraid

import argparse
import sys

from common import Config, setup_logging
from deploy_common import validate_api_key, validate_course_id
from qbraid_core import QbraidSessionV1

logger = setup_logging(__name__)


def cancel_course_operation(api_key: str, course_custom_id: str):
    """Cancels the course operation on qBraid."""
    logger.info(f"Cancelling operation for course: {course_custom_id}")

    # Endpoint structure assumed to be POST /learn/articles/{course_id}/cancel
    url = f"/learn/articles/{course_custom_id}/cancel"
    headers = {"X-API-Key": api_key}

    session = QbraidSessionV1(api_key=api_key)
    session.base_url = Config.API_BASE_URL

    try:
        # Using POST as cancellation is typically a state change
        response = session.post(
            url, headers=headers, timeout=Config.REQUEST_TIMEOUT_SECONDS
        )

        if response.status_code == 200:
            logger.info("✅ Course operation cancelled successfully.")
        elif response.status_code == 404:
            logger.warning(
                f"Course {course_custom_id} not found or operation not active."
            )
        else:
            logger.warning(
                f"Failed to cancel course operation. Status: {response.status_code}. Response: {response.text}"
            )

    except Exception as e:
        logger.error(f"Error cancelling course operation: {e}")
        # robustly handle errors during cancellation so we don't confuse users with extra errors
        sys.exit(0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cancel course operation on qBraid")
    parser.add_argument("--api-key", required=True, type=validate_api_key)
    parser.add_argument("course_custom_id", type=validate_course_id)

    try:
        args = parser.parse_args()
        cancel_course_operation(args.api_key, args.course_custom_id)
    except Exception as e:
        logger.error(f"Failed to execute cancel script: {e}")
        sys.exit(1)
