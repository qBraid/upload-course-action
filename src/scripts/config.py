import os

# Default to production URLs
DEFAULT_API_BASE_URL = "https://e78dd5569a6c.ngrok-free.app/app1"
DEFAULT_WORKER_BASE_URL = "https://e78dd5569a6c.ngrok-free.app/app4"

# Allow override via environment variables
API_BASE_URL = os.getenv("QBRAID_API_BASE_URL", DEFAULT_API_BASE_URL)
WORKER_BASE_URL = os.getenv("QBRAID_WORKER_BASE_URL", DEFAULT_WORKER_BASE_URL)
