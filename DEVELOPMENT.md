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
- `validate_api_key.py`: Verifies the qBraid API key.
- `validate_course.py`: Validates `course.json` structure.
- `verify_notebooks.py`: Checks existence of notebook files.
- `check_images.py`: Validates image references in notebooks.
- `upload_files.py`: Handles file scanning and upload via Signed URLs.
- `create_course.py`: Calls qBraid API to create the course.
- `poll_worker.py`: Polls for course processing completion.

### 3. requirements.txt
Python dependencies required by the scripts:
- `requests`
- `nbformat`

## Authentication

The action uses a **Signed URL** approach for secure uploads:

1.  **User Authentication**: Users provide a qBraid API key via the `api-key` input.
2.  **Upload Authorization**: The action requests upload URLs from the qBraid API using the user's API key.
3.  **Direct Upload**: Files are uploaded directly to Google Cloud Storage using the pre-signed URLs returned by the API.

**Note:** No GCS Service Account Keys are stored or used within this action.

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

✅ **No Secrets in Action**: The action does not store or require GCS credentials.
✅ **API Key Validation**: The API key is validated before any operations.
✅ **Signed URLs**: Uploads are scoped and time-limited by the backend.
✅ **Input Validation**: All user inputs are validated by the scripts.
