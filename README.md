# Deploy Course Action

A GitHub Action for deploying educational courses to  learning platform with automated validation and secure file upload.

## Overview

This action provides a complete end-to-end solution for deploying courses:

1.  **Validate API Key** - Verifies your qBraid credentials.
2.  **Validate course.json** - Ensures the course configuration file has the correct structure.
3.  **Verify notebooks** - Confirms all referenced notebook files exist.
4.  **Check image references** - Validates all images referenced in notebooks exist.
5.  **Upload to GCS** - Securely uploads course files using Signed URLs (no GCS keys required).
6.  **Create course** - Registers the course with qBraid API.
7.  **Poll for completion** - Waits for course processing to complete.
8.  **Notify** - Sends notification with the deployed course URL.

## Quick Start

1.  Create a `course.json` file in your repository root.
2.  Add `QBRAID_API_KEY` to your repository secrets.
3.  Create a workflow file (e.g., `.github/workflows/deploy.yml`):

```yaml
name: Deploy Course

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Deploy to qBraid
        uses: courseBuilderNelson/UploadActionRepo@latest
        with:
          api-key: ${{ secrets.QBRAID_API_KEY }}
```

## Inputs

| Input | Description | Required | Default |
| :--- | :--- | :--- | :--- |
| `api-key` | Your qBraid API key (store in secrets) | **Yes** | N/A |
| `course-json-path` | Path to `course.json` file | No | `course.json` |
| `source-path` | Directory to upload (relative to root) | No | `.` |
| `exclude-patterns` | Glob patterns to exclude | No | `.git/**,node_modules/**,.github/**` |

## Outputs

| Output | Description |
| :--- | :--- |
| `formatted_course_name` | Sanitized course name used for storage |
| `qbook_url` | URL of the deployed course |

## How it Works

This action uses a **Signed URL** approach for secure uploads.
1.  The action scans your files and requests upload permissions from the qBraid API.
2.  The API returns temporary, pre-authorized URLs for each file.
3.  The action uploads files directly to Google Cloud Storage using these URLs.
4.  **Security Benefit:** You do not need to share any GCS credentials or Service Account Keys.

## License

MIT
