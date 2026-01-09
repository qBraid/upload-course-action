import sys
from typing import Any, Dict, Optional

from common import Config, setup_logging
from qbraid_core import QbraidSessionV1

logger = setup_logging(__name__)


class AuthValidator:
    """Validates the qBraid API key."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    def validate(self) -> None:
        """
        Validate the qBraid API key using the verification endpoint.

        Raises:
            SystemExit: If validation fails.
        """

        try:
            # Use qbraid-core session for authentication
            session = QbraidSessionV1(api_key=self.api_key)
            session.base_url = Config.API_BASE_URL
            response = session.get(
                "/users/verify", timeout=Config.REQUEST_TIMEOUT_SECONDS
            )

            if response.status_code == 200:
                logger.info("✅ API key is valid.")
                try:
                    user_data: Dict[str, Any] = response.json()
                    # Print user info if available
                    if "email" in user_data:
                        logger.info(f"Authenticated as: {user_data['email']}")
                except Exception:
                    pass
                # Success
                return
            elif response.status_code == 401:
                logger.error("❌ Error: Invalid API key.")
            else:
                logger.error(f"❌ Error: Unexpected status code {response.status_code}")

        except Exception as e:
            logger.error(f"❌ Error: Exception during API key validation: {e}")

        sys.exit(1)


def validate_api_key(api_key: str):
    validator = AuthValidator(api_key)
    validator.validate()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        logger.error("Usage: python validate_api_key.py <api_key>")
        sys.exit(1)
    validate_api_key(sys.argv[1])
