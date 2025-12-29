import os

# Default to production URLs
DEFAULT_API_BASE_URL = "https://a6a1342cabda.ngrok-free.app/app1"

# Allow override via environment variables
API_BASE_URL = os.getenv("QBRAID_API_BASE_URL", DEFAULT_API_BASE_URL)
