# Deploy Course to qBraid [BETA]

> **⚠️ Beta Status**: This is a beta release of the qBraid Course Deployment Action. It uses our staging environment and may undergo breaking changes. Not recommended for production use until stable release.

A GitHub Action for deploying educational courses to qBraid learning platform with automated validation and secure file upload.

## Overview

This action provides a complete end-to-end solution for deploying courses:

1.  **Validate API Key** - Verifies your qBraid credentials.
2.  **Validate course.json** - Ensures the course configuration file has the correct structure.
3.  **Verify notebooks** - Confirms all referenced notebook files exist and validates content security.
4.  **Check image references** - Validates all images referenced in notebooks exist and are under 1MB.
5.  **Create course** - Registers the course with qBraid API using repository information.
6.  **Poll for completion** - Waits for course processing to complete.
7.  **Notify** - Sends notification with the deployed course URL.

## Quick Start

1.  Create a `course.json` file in your repository root.
2.  Add `QBRAID_API_KEY` to your repository secrets.
3.  **Enable Permissions**: Go to **Settings** > **Actions** > **General** > **Workflow permissions** and select **Read and write permissions**. This is required for the action to post deployment notifications.
4.  Create a workflow file (e.g., `.github/workflows/deploy.yml`):

```yaml
name: Deploy Course

on:
  push:
    branches: [ main ]

permissions:
  contents: write

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v6

      - name: Deploy to qBraid
        uses: qBraid/upload-course-api@v0.1.0-beta
        with:
          api-key: ${{ secrets.QBRAID_API_KEY }}
          repo-read-token: ${{ secrets.GITHUB_TOKEN }}
```

**Note:** This is a beta release using staging API. For production use, wait for stable release. Pin to this specific beta version (`@v0.1.0-beta`) for reproducibility. See [CHANGELOG.md](CHANGELOG.md) for version history.

## Inputs

| Input | Description | Required | Default |
| :--- | :--- | :--- | :--- |
| `api-key` | Your qBraid API key (store in secrets) | **Yes** | N/A |
| `repo-read-token` | GitHub token with read access to the repository | **Yes** | N/A |
| `course-json-path` | Path to `course.json` file | No | `course.json` |
| `article-type` | Type of article to create (`course` or `blog`) | No | `course` |
| `force-duplicate-questions` | Whether to force upload duplicate questions (`true` or `false`) | No | `false` |
| `max-poll-attempts` | Maximum polling attempts before timing out | No | `20` |
| `poll-interval-seconds` | Seconds to wait between polling attempts | No | `15` |
| `max-consecutive-errors` | Maximum consecutive polling errors before failing | No | `5` |

## Optional Environment Variables

| Variable | Description | Default |
| :--- | :--- | :--- |
| `QBRAID_API_BASE_URL` | Override the qBraid API base URL (useful for local/dev testing) | `https://api-v2.qbraid.com/api/v1` |
| `QBRAID_MAX_POLL_ATTEMPTS` | Maximum polling attempts before timing out | `15` |
| `QBRAID_POLL_INTERVAL_SECONDS` | Seconds to wait between polling attempts | `15` |
| `QBRAID_MAX_CONSECUTIVE_ERRORS` | Maximum consecutive polling request errors before failing | `5` |
| `QBRAID_REQUEST_TIMEOUT_SECONDS` | HTTP request timeout for qBraid API calls | `30` |

## Outputs

| Output | Description |
| :--- | :--- |
| `course_name` | Name of the deployed course |
| `course-custom-id` | Custom ID of the deployed course |
| `qbook_url` | URL of the deployed course |

## How it Works

This action validates your course structure and creates it via the qBraid API:

1.  **Validation**: The action validates your API key, course.json structure, notebook files, and image references.
2.  **API Integration**: Course data and repository information are sent to the qBraid API.
3.  **Course Creation**: The API processes your course content directly from your GitHub repository.
4.  **Progress Monitoring**: The action polls for completion and reports the deployed course URL.

**Security Benefit:** The action only sends metadata and repository references to qBraid - your API key is validated but files are accessed securely via GitHub tokens.

## Versioning

This project follows [Semantic Versioning](https://semver.org/). See [CHANGELOG.md](CHANGELOG.md) for a detailed list of changes.

**Current Version:** `v0.1.0-beta`

**Recommended Usage:**
- Beta Testing: Pin to `@v0.1.0-beta`
- Development: Use `@main` or a specific commit SHA
- Production: Wait for stable release before use
- Local Testing: Use `@main` with `QBRAID_API_BASE_URL` override

## Beta Status & Limitations

### Current Beta Status
- **Environment**: Uses qBraid staging API (`api-v2.qbraid.com`)
- **Stability**: May undergo breaking changes
- **Production Use**: Not recommended until stable release
- **Support**: Community feedback encouraged

### Known Limitations
- Staging environment may have rate limits
- Data persistence not guaranteed in staging
- Some features may be in development
- Performance may differ from production

### Feedback & Issues
Please report issues and provide feedback:
- [GitHub Issues](https://github.com/qBraid/upload-course-api/issues)
- Include "BETA" in issue title for prioritization

## Security

This action implements several security measures:

### Authentication & Authorization
- API keys are validated before any operations
- GitHub tokens are used with read-only repository access
- No credentials are stored in the action code

### Content Security
- Notebooks are scanned for potentially malicious content (XSS, script injection)
- File size limits enforced (5MB for notebooks, 1MB for images)
- Credential detection patterns check for exposed API keys, tokens, and passwords

### Configuration Security
- API base URL can be overridden via `QBRAID_API_BASE_URL` environment variable for testing
- Default production URL: `https://api.qbraid.com`
- Polling behavior can be tuned using `QBRAID_MAX_POLL_ATTEMPTS`, `QBRAID_POLL_INTERVAL_SECONDS`, and `QBRAID_MAX_CONSECUTIVE_ERRORS`
- Default API base URL: `https://api-v2.qbraid.com/api/v1`
- Request timeout can be configured via `QBRAID_REQUEST_TIMEOUT_SECONDS` (must be a positive integer)
- Timeouts on all API requests prevent hanging operations

### Best Practices
- Store your `QBRAID_API_KEY` in GitHub repository secrets (never in code)
- Use GitHub's `GITHUB_TOKEN` for the `repo-read-token` input
- Enable "Read and write permissions" in repository settings for deployment notifications
- Review the course content before deployment to ensure no sensitive data is included
