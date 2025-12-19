import os

# Default to production URLs
DEFAULT_API_BASE_URL = "https://647efe91b5433c.lhr.life"
DEFAULT_WORKER_BASE_URL = "https://daa44e817bcab7.lhr.life"

# Allow override via environment variables
API_BASE_URL = os.getenv("QBRAID_API_BASE_URL", DEFAULT_API_BASE_URL)
WORKER_BASE_URL = os.getenv("QBRAID_WORKER_BASE_URL", DEFAULT_WORKER_BASE_URL)
