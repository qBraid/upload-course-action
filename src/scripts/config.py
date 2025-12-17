import os

# Default to production URLs
DEFAULT_API_BASE_URL = "https://293512f3a9c3.ngrok-free.app"
DEFAULT_WORKER_BASE_URL = "http://api-worker.qbraid.com"

# Allow override via environment variables
API_BASE_URL = os.getenv("QBRAID_API_BASE_URL", DEFAULT_API_BASE_URL)
WORKER_BASE_URL = os.getenv("QBRAID_WORKER_BASE_URL", DEFAULT_WORKER_BASE_URL)
