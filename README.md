# Upload to GCS Action & Course Deployment Workflow

A GitHub Action and reusable workflow for deploying educational courses to qBraid's learning platform with automated validation and GCS storage.

## Overview

This repository provides two main components:

1. **Upload Action** - A GitHub Action for uploading files to Google Cloud Storage
2. **Deploy Course Workflow** - A complete reusable workflow for deploying educational courses to qBraid

## Features

### Upload Action
- 🚀 Upload files and directories to GCS bucket
- 🔐 Secure authentication using qBraid API key
- 📁 Flexible source and destination path configuration
- 🎯 Pattern-based file exclusion
- 📊 Detailed upload status and metrics
- 🔒 Preconfigured GCS bucket (no bucket configuration needed)

### Deploy Course Workflow
- ✅ Validates course.json structure
- 📓 Verifies all notebook files exist
- 🖼️ Checks image references in notebooks
- ☁️ Uploads course content to GCS
- 🎓 Creates course via qBraid API
- ⏱️ Polls for processing completion
- 📬 Sends deployment notifications

---

## 🎓 Deploy Course Workflow (Recommended for Course Creators)

If you're creating educational courses for qBraid, use the **reusable workflow** which handles the complete deployment process.

### Quick Start

1. Create a `course.json` file in your repository root
2. Add `QBRAID_API_KEY` to your repository secrets
3. Create a workflow file:

```yaml
name: Deploy Course

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    uses: courseBuilderNelson/UploadActionRepo/.github/workflows/deploy-course.yml@v1
    secrets:
      QBRAID_API_KEY: ${{ secrets.QBRAID_API_KEY }}
```

📚 **[Complete Workflow Documentation →](WORKFLOW_GUIDE.md)**

---

## 📦 Upload Action (For Advanced Use Cases)

For direct file uploads to GCS without course validation, use the action directly.

### Prerequisites

1. A qBraid API key
2. Add the API key to your repository secrets as `QBRAID_API_KEY`

**Note:** The GCS bucket and credentials are preconfigured in the action. You only need to provide your qBraid API key for authentication.

### Basic Example

```yaml
name: Upload to GCS

on:
  push:
    branches: [ main ]

jobs:
  upload:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Upload to GCS
        uses: courseBuilderNelson/UploadActionRepo@v1
        with:
          api-key: ${{ secrets.QBRAID_API_KEY }}
```

### Advanced Example

```yaml
name: Upload to GCS with Custom Settings

on:
  release:
    types: [published]

jobs:
  upload:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Upload to GCS
        uses: courseBuilderNelson/UploadActionRepo@v1
        with:
          api-key: ${{ secrets.QBRAID_API_KEY }}
          source-path: './dist'
          destination-path: 'releases/${{ github.ref_name }}'
          exclude-patterns: '*.log,*.tmp,.git/**,node_modules/**'
```

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `api-key` | qBraid API key for authentication | Yes | - |
| `source-path` | Path to the directory or file to upload (relative to repository root) | No | `.` (repository root) |
| `destination-path` | Destination path in the GCS bucket | No | `` (bucket root) |
| `exclude-patterns` | Comma-separated list of glob patterns to exclude from upload | No | `.git/**,node_modules/**,.github/**` |

## Outputs

| Output | Description |
|--------|-------------|
| `upload-status` | Status of the upload operation (`success`, `failed`, or `skipped`) |
| `files-uploaded` | Number of files successfully uploaded |
| `upload-url` | Base URL of the uploaded content in GCS |

## Setting Up the QBRAID_API_KEY Secret

1. Go to your repository on GitHub
2. Navigate to Settings → Secrets and variables → Actions
3. Click "New repository secret"
4. Name: `QBRAID_API_KEY`
5. Value: Your qBraid API key (obtained from qBraid)
6. Click "Add secret"

## API Key Format

The action expects the `QBRAID_API_KEY` to be a valid qBraid API key string. You can obtain this key from your qBraid account.

**Note:** The GCS service account credentials are preconfigured within the action itself. You do not need to provide GCS credentials - only your qBraid API key for authentication.

## Example Workflows

### Upload on Every Commit

```yaml
on: [push]

jobs:
  upload:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: courseBuilderNelson/UploadActionRepo@v1
        with:
          api-key: ${{ secrets.QBRAID_API_KEY }}
```

### Upload Specific Directory

```yaml
on: [push]

jobs:
  upload:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build project
        run: npm run build
      - uses: courseBuilderNelson/UploadActionRepo@v1
        with:
          api-key: ${{ secrets.QBRAID_API_KEY }}
          source-path: './build'
          destination-path: 'production'
```

## Troubleshooting

### No Files Uploaded

Check the `exclude-patterns` input. The default excludes `.git/**`, `node_modules/**`, and `.github/**`. Adjust as needed.

### Authentication Failures

Verify that:
1. The `QBRAID_API_KEY` secret is properly set in your repository
2. The API key is valid and active
3. You have obtained the correct API key from your qBraid account
2. The API key is in valid JSON format
3. The service account has not been disabled or deleted

## License

MIT

## Support

For issues and questions, please open an issue in this repository.
