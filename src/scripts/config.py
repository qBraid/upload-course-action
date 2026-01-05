import os

# Default to production URLs
# NOTE: This URL should be updated to the actual production qBraid API endpoint
# Ngrok URLs are temporary and should only be used for development/testing
DEFAULT_API_BASE_URL = "https://api.qbraid.com"

# Allow override via environment variables for testing/development
API_BASE_URL = os.getenv("QBRAID_API_BASE_URL", DEFAULT_API_BASE_URL)
