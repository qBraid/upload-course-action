# Upload to GCS Action

A GitHub Action that uploads repository contents to Google Cloud Storage (GCS) buckets with qBraid API key authentication.

## Description

This action allows you to automatically upload files from your GitHub repository to a Google Cloud Storage bucket. It's designed to work with qBraid's authentication system, making it easy to publish your repository contents to GCS as part of your CI/CD workflow.

## Features

- 🚀 Upload files and directories to GCS buckets
- 🔐 Secure authentication using qBraid API key
- 📁 Flexible source and destination path configuration
- 🎯 Pattern-based file exclusion
- 📊 Detailed upload status and metrics

## Usage

### Prerequisites

1. A Google Cloud Storage bucket
2. A qBraid API key with permissions to write to the bucket
3. Add the API key to your repository secrets as `QBRAID_API_KEY`

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
          bucket-name: 'my-gcs-bucket'
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
          bucket-name: 'my-gcs-bucket'
          api-key: ${{ secrets.QBRAID_API_KEY }}
          source-path: './dist'
          destination-path: 'releases/${{ github.ref_name }}'
          exclude-patterns: '*.log,*.tmp,.git/**,node_modules/**'
```

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `bucket-name` | Name of the GCS bucket to upload to | Yes | - |
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
5. Value: Your qBraid API key (should be in JSON format for service account authentication)
6. Click "Add secret"

## API Key Format

The action expects the `QBRAID_API_KEY` to be a valid Google Cloud Service Account key in JSON format. Example:

```json
{
  "type": "service_account",
  "project_id": "your-project-id",
  "private_key_id": "key-id",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "your-service-account@your-project.iam.gserviceaccount.com",
  "client_id": "123456789",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/..."
}
```

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
          bucket-name: 'my-bucket'
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
          bucket-name: 'my-bucket'
          api-key: ${{ secrets.QBRAID_API_KEY }}
          source-path: './build'
          destination-path: 'production'
```

## Troubleshooting

### Permission Denied Errors

Ensure your service account has the necessary permissions:
- `storage.objects.create`
- `storage.objects.delete` (if overwriting)
- `storage.buckets.get`

### No Files Uploaded

Check the `exclude-patterns` input. The default excludes `.git/**`, `node_modules/**`, and `.github/**`. Adjust as needed.

### Authentication Failures

Verify that:
1. The `QBRAID_API_KEY` secret is properly set
2. The API key is in valid JSON format
3. The service account has not been disabled or deleted

## License

MIT

## Support

For issues and questions, please open an issue in this repository.
