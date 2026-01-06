# Development Guide

## Overview
This repository contains a Composite GitHub Action that validates and uploads course content to qBraid using Python scripts.

## Key Components

### 1. action.yml
- Defines the composite action metadata.
- Specifies inputs (`api-key`, `course-json-path`, etc.).
- Orchestrates the execution of Python scripts in `src/scripts/`.

### 2. src/scripts/
Contains the core logic in Python:
- `config.py`: Configuration for API base URL (supports environment override).
- `validate_api_key.py`: Verifies the qBraid API key.
- `validate_course.py`: Validates `course.json` structure and file sizes.
- `verify_notebooks.py`: Checks existence and security of notebook files.
- `check_images.py`: Validates image references in notebooks.
- `create_course.py`: Calls qBraid API to create the course with repository metadata.
- `poll_files_progress.py`: Polls for course processing completion.

### 3. requirements.txt
Python dependencies required by the scripts:
- `requests`
- `nbformat`

## Authentication

The action integrates with qBraid's API using secure authentication:

1.  **User Authentication**: Users provide a qBraid API key via the `api-key` input (stored in GitHub secrets).
2.  **Repository Access**: Uses GitHub token (`repo-read-token`) to grant qBraid read access to repository files.
3.  **API Integration**: Course metadata and repository information are sent to qBraid API, which processes files directly from GitHub.

**Security Notes:**
- API keys are validated before any operations
- GitHub tokens are scoped for read-only access
- Repository URL and commit SHA are sent to enable secure file access
- No direct file uploads from the action - files are accessed by qBraid from GitHub

## Development Workflow

1.  **Modify Scripts**: Edit the Python scripts in `src/scripts/`.
2.  **Test Locally**: You can run the scripts locally if you have a valid `course.json` and API key.
    ```bash
    # Example: Validate API Key
    python src/scripts/validate_api_key.py "YOUR_API_KEY"
    ```
3.  **Update Action**: If you change inputs/outputs, update `action.yml`.
4.  **Commit**: Commit changes to `main`. Since this is a composite action, no build step is required.

## Security Considerations

✅ **No Secrets in Action**: The action does not store GCS credentials or other sensitive data.
✅ **API Key Validation**: The API key is validated before any operations.
✅ **Secure Repository Access**: Uses GitHub tokens with read-only scope.
✅ **Input Validation**: All user inputs and file content are validated by the scripts.
✅ **Content Security**: Notebooks are scanned for XSS vulnerabilities, malicious scripts, and embedded credentials.
✅ **Size Limits**: Enforces file size limits (5MB for notebooks, 1MB for images).
✅ **Environment Override**: API base URL can be overridden via `QBRAID_API_BASE_URL` environment variable for testing.
