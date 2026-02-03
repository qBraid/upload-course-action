# Agent Integration Guide

This document provides guidance for AI agents and automated systems that interact with the Deploy Course to qBraid GitHub Action.

## Overview

The Deploy Course Action is a composite GitHub Action that automates the deployment of educational courses to the qBraid platform. This guide helps AI agents understand how to programmatically interact with and use this action.

## Action Interface

### Action Identifier
- **Repository**: `qBraid/upload-course-api`
- **Latest Version**: `@v0.1.0-beta` (beta), `@main` for development

### Required Inputs

| Input | Type | Description | Example |
|-------|------|-------------|---------|
| `api-key` | string | qBraid API key (must be stored in GitHub secrets) | `${{ secrets.QBRAID_API_KEY }}` |
| `repo-read-token` | string | GitHub token with read access to repository | `${{ secrets.GITHUB_TOKEN }}` |

### Optional Inputs

| Input | Type | Default | Description |
|-------|------|---------|-------------|
| `course-json-path` | string | `course.json` | Path to course configuration file |
| `article-type` | string | `course` | Type of article (`course` or `blog`) |
| `force-duplicate-questions` | string | `false` | Force upload duplicate questions (`true` or `false`) |
| `draft` | string | `false` | Create draft course (`true` or `false`) |

### Outputs

| Output | Description |
|--------|-------------|
| `course_name` | Name of the deployed course |
| `course-custom-id` | Custom ID of the deployed course |
| `qbook_url` | URL of the deployed course on qBraid |

## Workflow Integration Pattern

### Basic Workflow Template

```yaml
name: Deploy Course

on:
  push:
    branches: [ main ]
  workflow_dispatch:

permissions:
  contents: write

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v6

      - name: Deploy to qBraid
        id: deploy
        uses: qBraid/upload-course-api@v0.1.0-beta
        with:
          api-key: ${{ secrets.QBRAID_API_KEY }}
          repo-read-token: ${{ secrets.GITHUB_TOKEN }}

      - name: Use deployment outputs
        run: |
          echo "Course: ${{ steps.deploy.outputs.course_name }}"
          echo "URL: ${{ steps.deploy.outputs.qbook_url }}"
```

## Prerequisites for Agents

### 1. Repository Setup

Before an agent can use this action, ensure:

- **course.json exists**: The repository must contain a valid `course.json` file in the root (or at the path specified by `course-json-path`)
- **API Key configured**: `QBRAID_API_KEY` must be set in repository secrets
- **Permissions enabled**: Repository must have "Read and write permissions" enabled in Settings > Actions > General > Workflow permissions

### 2. course.json Structure

Agents should validate or generate `course.json` with the following structure:

```json
{
  "courseName": "Course Name",
  "courseDescription": "Course description",
  "visibility": "public",
  "imageLink": {
    "darkLogo": "https://example.com/dark-logo.jpg",
    "lightLogo": "https://example.com/light-logo.jpg"
  },
  "tags": ["tag1", "tag2"],
  "deployedTo": ["qbraid.com"],
  "content": [
    {
      "chapterName": "Chapter Name",
      "chapterNumber": 1,
      "baseFilePath": "./path/to/notebook.ipynb",
      "kernelName": "python3",
      "kernelId": "Python 3",
      "sections": []
    }
  ]
}
```

### 3. File Requirements

- **Notebooks**: Must exist at paths specified in `course.json`, max 5MB each
- **Images**: Referenced images must exist and be under 1MB
- **Security**: Notebooks are scanned for XSS, script injection, and credential exposure

## Agent Workflow Steps

### Step 1: Validate Repository Structure

Before triggering the action, agents should:

1. Check for `course.json` existence
2. Validate JSON structure
3. Verify all referenced notebook files exist
4. Check image file existence and sizes

### Step 2: Trigger Deployment

Agents can trigger deployment by:

- **Push to branch**: Commit changes and push to trigger workflow
- **Workflow dispatch**: Use GitHub API to trigger `workflow_dispatch` event
- **Pull request**: Create PR that triggers workflow (if configured)

### Step 3: Monitor Deployment

The action performs these stages automatically:

1. **Stage 0**: Validate API Key
2. **Stage 1**: Validate course.json structure
3. **Stage 2**: Verify all notebooks exist
4. **Stage 3**: Check image references
5. **Stage 5**: Create course via qBraid API
6. **Stage 6**: Poll for completion

### Step 4: Handle Results

Agents should:

- Check workflow run status
- Extract outputs from action steps
- Handle success/failure notifications
- Store `qbook_url` for future reference

## Error Handling

### Common Failure Scenarios

1. **API Key Invalid**: Action fails at Stage 0
   - Solution: Verify `QBRAID_API_KEY` secret is correct

2. **course.json Invalid**: Action fails at Stage 1
   - Solution: Validate JSON structure and required fields

3. **Notebook Missing**: Action fails at Stage 2
   - Solution: Ensure all `baseFilePath` values point to existing files

4. **Image Missing/Too Large**: Action fails at Stage 3
   - Solution: Verify image paths and ensure files are < 1MB

5. **API Error**: Action fails at Stage 5
   - Solution: Check API key permissions and qBraid API status

### Error Detection

Agents can detect errors by:

- Monitoring workflow run status
- Checking action step exit codes
- Parsing error messages from action logs
- Reviewing commit comments (action posts failure notifications)

## Programmatic Access

### GitHub API Integration

Agents can interact with this action via GitHub API:

```python
# Example: Trigger workflow dispatch
import requests

headers = {
    "Authorization": f"token {github_token}",
    "Accept": "application/vnd.github.v3+json"
}

response = requests.post(
    f"https://api.github.com/repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches",
    headers=headers,
    json={"ref": "main"}
)
```

### Reading Action Outputs

After workflow completion, agents can retrieve outputs:

```python
# Get workflow run
run = github.get_repo(f"{owner}/{repo}").get_workflow_run(run_id)

# Parse job logs to extract outputs
# Outputs are available via step outputs in subsequent steps
```

## Best Practices for Agents

1. **Validate Before Deploying**: Always validate `course.json` and file structure before triggering deployment
2. **Handle Secrets Securely**: Never expose API keys or tokens in code or logs
3. **Monitor Workflow Status**: Poll workflow run status to detect completion
4. **Error Recovery**: Implement retry logic for transient failures
5. **Idempotency**: Ensure deployments are idempotent (can be safely repeated)
6. **Logging**: Log all deployment attempts and results for debugging

## Testing

Agents can test the action using:

- **Local testing**: Use `act` tool with test workflows in `examples/` directory
- **Test workflows**: See `examples/test-workflow-*.yml` for reference
- **Dry-run validation**: Run validation scripts independently before full deployment

## Security Considerations

- API keys must be stored in GitHub secrets, never in code
- Repository tokens should have minimal required permissions
- Content is scanned for security vulnerabilities before deployment
- File size limits prevent resource exhaustion attacks

## Additional Resources

- **README.md**: User-facing documentation
- **WORKFLOW_GUIDE.md**: Detailed workflow usage guide
- **DEVELOPMENT.md**: Development and contribution guide
- **TESTING.md**: Testing procedures and guidelines

## Support

For issues or questions:
- Open an issue in this repository
- Review existing documentation files
- Check workflow logs for detailed error messages
