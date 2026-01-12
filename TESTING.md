# Testing Guide for Deploy Course Action

This guide covers multiple approaches to test the GitHub Action before deploying it to production.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Pytest Testing (Recommended)](#pytest-testing-recommended) ⭐ **Start here for development**
3. [CI/CD Automated Testing](#cicd-automated-testing)
4. [Testing Unpublished Actions](#testing-unpublished-actions)
5. [Local Script Testing](#local-script-testing)
6. [Testing with `act` (Local GitHub Actions)](#testing-with-act)
7. [Testing in a Test Repository](#testing-in-a-test-repository)
8. [Manual Workflow Dispatch](#manual-workflow-dispatch)
9. [Testing Individual Stages](#testing-individual-stages)

## Prerequisites

Before testing, ensure you have:

- Python 3.11+ installed
- A valid qBraid API key
- A GitHub token with repository read access
- A test `course.json` file (see `examples/course.json` for structure)

Install dependencies:
```bash
# Using UV (recommended)
make install

# Or manually with UV
uv pip install -e .

# For testing, install with test dependencies
make install-test
# Or: uv pip install -e ".[test]"
```

## Pytest Testing (Recommended)

The project uses **pytest** for comprehensive unit and integration testing. This is the primary testing method for development.

### Quick Start

```bash
# Run all tests
make test

# Run only unit tests
make test-unit
# Or: pytest -q test/unit

# Run only E2E tests
make test-e2e
# Or: pytest -q test/e2e

# Run tests with coverage
make test-coverage
# Or: pytest --cov=src/scripts --cov-report=html
```

### Test Markers

Tests are organized using pytest markers for easy filtering:

- `@pytest.mark.unit` - Unit tests for individual components
- `@pytest.mark.e2e` - End-to-end tests for full workflow

Run specific test types:

```bash
# Run only unit tests
pytest -m unit

# Run only E2E tests
pytest -m e2e

# Run tests matching multiple markers
pytest -m "unit or e2e"
```

### Test Coverage

Generate coverage reports to see which code is tested:

```bash
# Generate coverage report (terminal + HTML)
make coverage-report

# Generate and open HTML coverage report
make coverage-html

# View coverage in terminal
pytest --cov=src/scripts --cov-report=term-missing
```

Coverage reports are generated in:
- Terminal output (with missing lines)
- `htmlcov/index.html` (interactive HTML report)
- `coverage.xml` (for CI integration)

### Test Fixtures

The project includes shared fixtures in `test/conftest.py`:

- `mock_qbraid_session` - Mocked QbraidSessionV1 instance
- `temp_dir` - Temporary directory for test files
- `mock_api_response_success` - Successful API response mock
- `mock_api_response_created` - 201 Created response mock
- `mock_api_response_error` - Error response mock
- `sample_course_json` - Sample course.json data
- `sample_notebook_content` - Sample notebook content
- `github_output` - Simulates GitHub Actions $GITHUB_OUTPUT
- `github_env` - Simulates GitHub Actions environment variables
- `runner_filesystem` - Simulates GitHub Actions runner filesystem
- `nasty_inputs` - Edge case inputs (spaces, newlines, unicode, etc.)

### Example: Writing a New Test

```python
import pytest
from unittest import mock

from validate_api_key import AuthValidator

@pytest.mark.unit
class TestAuthValidator:
    @mock.patch("validate_api_key.QbraidSessionV1")
    def test_validate_success(self, mock_session_cls):
        """Test successful API key validation."""
        mock_instance = mock_session_cls.return_value
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"email": "test@example.com"}
        mock_instance.get.return_value = mock_response

        validator = AuthValidator("valid_key")
        validator.validate()
        mock_instance.get.assert_called_once()
```

### Testing Edge Cases

The project includes "nasty" E2E tests (`test/e2e/test_nasty_inputs.py`) that verify handling of:
- Paths with spaces, newlines, tabs
- Unicode characters in paths
- Very long paths
- Missing files
- Malformed JSON
- Path traversal attempts
- Special characters in values

Run these tests:

```bash
pytest test/e2e/test_nasty_inputs.py -v
```

### Configuration

Pytest configuration is in `pyproject.toml` under `[tool.pytest.ini_options]`:

- Test discovery patterns
- Markers definition
- Coverage settings
- Output formatting

## CI/CD Automated Testing

Tests run automatically on every push and pull request via `.github/workflows/test.yml`.

### CI Workflow Jobs

1. **Unit & Integration Tests**
   - Runs `pytest -q` on unit and E2E tests
   - Generates coverage reports
   - Uploads coverage artifacts

2. **Workflow & Action Checks**
   - Runs `actionlint` to validate action.yml
   - Runs `zizmor` to check security and best practices
   - Validates workflow syntax and permissions

3. **E2E Action Test**
   - Tests the actual composite action in a workflow
   - Verifies outputs and error handling
   - Tests edge cases (spaces, missing files, etc.)

### Viewing CI Results

1. Go to the **Actions** tab in GitHub
2. Click on a workflow run
3. View test results, coverage, and any failures
4. Download coverage artifacts if needed

### Local CI Simulation

You can simulate CI locally:

```bash
# Run the same tests CI runs
make test

# Check action.yml with actionlint (if installed)
actionlint .github/workflows/test.yml action.yml
```

## Testing Unpublished Actions

If the action hasn't been published to the GitHub Marketplace yet, you can still test it by referencing the source repository directly.

### Reference the Action from Source Repository

Instead of using `@latest` or `@v1` (which only work for published actions), use the repository path with a branch, tag, or commit SHA:

```yaml
# Reference by branch (recommended for testing)
uses: courseBuilderNelson/UploadActionRepo@main

# Reference by specific commit SHA (most stable for testing)
uses: courseBuilderNelson/UploadActionRepo@abc123def456

# Reference by tag (if you've created tags)
uses: courseBuilderNelson/UploadActionRepo@v0.1.0
```

### Complete Workflow Example for Testing

In your test repository, create `.github/workflows/deploy.yml`:

```yaml
name: Deploy Course

on:
  workflow_dispatch:  # Allows manual triggering
  push:
    branches: [ main, test ]

permissions:
  contents: write

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v6

      - name: Deploy to qBraid
        uses: courseBuilderNelson/UploadActionRepo@main
        with:
          api-key: ${{ secrets.QBRAID_API_KEY }}
          repo-read-token: ${{ secrets.GITHUB_TOKEN }}
          course-json-path: 'course.json'
          article-type: 'course'
```

### Quick Setup Steps

1. **In your test repository**, add secrets:
   - Go to **Settings** > **Secrets and variables** > **Actions**
   - Add `QBRAID_API_KEY` (your qBraid API key)
   - `GITHUB_TOKEN` is automatically available

2. **Create the workflow file** (`.github/workflows/deploy.yml`) with the example above

3. **Trigger the workflow**:
   - Go to **Actions** tab
   - Select your workflow
   - Click **Run workflow**
   - Or push to the `main` or `test` branch

### Using a Specific Branch for Development

If you're actively developing the action and want to test changes:

```yaml
# Test from a feature branch
uses: courseBuilderNelson/UploadActionRepo@feature-branch-name

# Test from a specific commit (most reliable)
uses: courseBuilderNelson/UploadActionRepo@abc123def456789
```

**Pro Tip:** Using a commit SHA ensures you're testing a specific version and won't be affected by future changes to the branch.

### Troubleshooting Unpublished Action References

**Error: "Action not found"**
- Verify the repository path is correct: `owner/repo-name`
- Check that the branch/tag/commit exists
- Ensure the repository is public or you have access

**Error: "Resource not accessible by integration"**
- The action repository might be private - ensure your GitHub token has access
- For private repos, you may need a Personal Access Token with `repo` scope

**Action runs but fails**
- Check that the branch you're referencing has the latest `action.yml`
- Verify all required files are in the repository
- Check the Actions tab in the source repository for any workflow errors

## Local Script Testing

You can test each Python script individually to verify functionality before running the full action.

### 1. Validate API Key

```bash
python src/scripts/validate_api_key.py "YOUR_API_KEY"
```

**Expected output:** ✅ API key is valid.

### 2. Validate course.json

```bash
python src/scripts/validate_course.py "course.json"
```

**Expected output:** Course validation details and course name.

### 3. Verify Notebooks

```bash
# Make sure you're in the repository root
python src/scripts/verify_notebooks.py
```

**Expected output:** Verification that all notebooks referenced in `course.json` exist.

### 4. Check Images

```bash
python src/scripts/check_images.py
```

**Expected output:** Verification that all image references in notebooks are valid.

### 5. Create Course (Full Upload)

```bash
python src/scripts/create_course.py \
  "YOUR_API_KEY" \
  "course" \
  "false" \
  "YOUR_GITHUB_TOKEN" \
  "https://github.com/your-org/your-repo" \
  "commit-sha"
```

**Note:** This will actually create a course in qBraid, so use a test API key or test environment.

### 6. Poll for Completion

```bash
python src/scripts/poll_files_progress.py "YOUR_API_KEY" "COURSE_CUSTOM_ID"
```

## Testing with `act` (Recommended for Local API Testing) ⭐

[`act`](https://github.com/nektos/act) allows you to run GitHub Actions locally on your machine. **This is the easiest way to test with a local API** since everything runs on your machine and can access `localhost` directly.

### Installation

```bash
# macOS
brew install act

# Linux
curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash

# Windows (via Chocolatey)
choco install act-cli
```

### Setup Secrets

Create a `.secrets` file in the repository root:

```bash
# .secrets
QBRAID_API_KEY=your_api_key_here
GITHUB_TOKEN=your_github_token_here
```

### Testing with Local API using `act`

This is the **recommended approach** for testing with a local API:

1. **Start your local API server** (e.g., on `localhost:3001`)

2. **Create a test workflow** (`.github/workflows/test-local.yml`):

```yaml
name: Test Action with Local API

on:
  workflow_dispatch:

permissions:
  contents: write

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      
      - name: Test Action with Local API
        env:
          QBRAID_API_BASE_URL: "http://localhost:3001"  # Your local API
        uses: ./
        with:
          api-key: ${{ secrets.QBRAID_API_KEY }}
          repo-read-token: ${{ secrets.GITHUB_TOKEN }}
          course-json-path: 'course.json'
```

3. **Run with act:**

```bash
# Run the workflow with secrets and local API
act workflow_dispatch -W .github/workflows/test-local.yml --secret-file .secrets

# Or if your workflow triggers on push
act push --secret-file .secrets
```

**Key Benefits:**
- ✅ No need for ngrok or exposing your API
- ✅ Direct access to `localhost`
- ✅ Fast iteration - no waiting for GitHub Actions
- ✅ Test unpublished actions with `uses: ./`

### Testing Unpublished Action with `act`

When using `act`, you can test the action from the source repository:

```yaml
name: Test Action Locally

on:
  workflow_dispatch:

permissions:
  contents: write

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      
      - name: Test Action
        env:
          QBRAID_API_BASE_URL: "http://localhost:3001"  # Local API
        uses: ./
        with:
          api-key: ${{ secrets.QBRAID_API_KEY }}
          repo-read-token: ${{ secrets.GITHUB_TOKEN }}
          course-json-path: 'examples/course.json'
```

**Note:** When using `act`, use `uses: ./` to reference the local action instead of the published version.

### Testing with Private Action Repository

If your GitHub Action repository is **private**, `act` needs authentication to clone it. Here are the options:

#### Option 1: Use GitHub Token in Environment Variable (Recommended)

Set `GITHUB_TOKEN` as an environment variable when running `act`:

```bash
# Create a Personal Access Token (PAT) with 'repo' scope
# GitHub Settings > Developer settings > Personal access tokens > Tokens (classic)

# Run act with the token
GITHUB_TOKEN=ghp_your_personal_access_token act workflow_dispatch --secret-file .secrets

# Or export it first
export GITHUB_TOKEN=ghp_your_personal_access_token
act workflow_dispatch --secret-file .secrets
```

#### Option 2: Add Token to `.secrets` File

Add your GitHub Personal Access Token to the `.secrets` file:

```bash
# .secrets
QBRAID_API_KEY=your_api_key_here
GITHUB_TOKEN=ghp_your_personal_access_token_here
```

Then `act` will use it automatically when you run:
```bash
act workflow_dispatch --secret-file .secrets
```

**Note:** The `GITHUB_TOKEN` in `.secrets` is used by the workflow steps. For `act` to clone private repos, you may still need to set it as an environment variable (Option 1).

#### Option 3: Configure Git Credentials

Configure git to use a token for GitHub:

```bash
# Configure git to use token for GitHub
git config --global url."https://ghp_your_token@github.com/".insteadOf "https://github.com/"

# Or for SSH (if you use SSH URLs)
# Set up SSH keys and use SSH URLs in your workflow
```

#### Option 4: Use SSH Instead of HTTPS

If you have SSH keys set up:

1. Use SSH URLs in your workflow:
   ```yaml
   - uses: actions/checkout@v6
     with:
       ssh-key: ${{ secrets.SSH_PRIVATE_KEY }}
   ```

2. Or configure git to use SSH:
   ```bash
   git config --global url."git@github.com:".insteadOf "https://github.com/"
   ```

### Creating a GitHub Personal Access Token

1. Go to **GitHub Settings** > **Developer settings** > **Personal access tokens** > **Tokens (classic)**
2. Click **Generate new token (classic)**
3. Give it a name (e.g., "act-local-testing")
4. Select scopes:
   - ✅ `repo` (Full control of private repositories)
   - ✅ `read:packages` (if you use GitHub Packages)
5. Click **Generate token**
6. **Copy the token immediately** (you won't see it again!)

### Testing Private Action with `act`

If your workflow references a private action repository:

```yaml
- name: Deploy to qBraid
  uses: your-org/private-action-repo@main  # Private repo
  with:
    api-key: ${{ secrets.QBRAID_API_KEY }}
```

Run `act` with authentication:

```bash
# Method 1: Environment variable
GITHUB_TOKEN=ghp_your_token act workflow_dispatch --secret-file .secrets

# Method 2: Export first
export GITHUB_TOKEN=ghp_your_token
act workflow_dispatch --secret-file .secrets -W .github/workflows/test.yml
```

### Advanced `act` Usage

```bash
# Run with specific event
act workflow_dispatch --secret-file .secrets

# Run with environment variables
act workflow_dispatch --secret-file .secrets -e QBRAID_API_BASE_URL=http://localhost:3001

# Run with GitHub token for private repos
GITHUB_TOKEN=ghp_your_token act workflow_dispatch --secret-file .secrets

# Run with verbose output for debugging
act workflow_dispatch --secret-file .secrets -v

# Use a specific workflow file
act -W .github/workflows/test-local.yml --secret-file .secrets

# Combine multiple options
GITHUB_TOKEN=ghp_your_token act workflow_dispatch \
  -W .github/workflows/test-local.yml \
  --secret-file .secrets \
  -e QBRAID_API_BASE_URL=http://localhost:3001 \
  -v
```

## Testing in a Test Repository

The safest way to test is in a separate test repository with sample course content.

### Step 1: Create Test Repository

1. Create a new GitHub repository (e.g., `test-course-deployment`)
2. Add a `course.json` file with test content
3. Add sample notebook files referenced in `course.json`
4. Add the workflow file (see below)

### Step 2: Add Secrets

In your test repository, go to **Settings** > **Secrets and variables** > **Actions** and add:
- `QBRAID_API_KEY`: Your qBraid API key
- The `GITHUB_TOKEN` is automatically available

### Step 3: Create Test Workflow

Create `.github/workflows/test-deploy.yml`:

```yaml
name: Test Course Deployment

on:
  workflow_dispatch:  # Allows manual triggering
  push:
    branches: [ test ]  # Only trigger on test branch

permissions:
  contents: write

jobs:
  test-deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v6

      - name: Deploy to qBraid
        uses: courseBuilderNelson/UploadActionRepo@main
        with:
          api-key: ${{ secrets.QBRAID_API_KEY }}
          repo-read-token: ${{ secrets.GITHUB_TOKEN }}
          course-json-path: 'course.json'
```

### Step 4: Test

1. Push to the `test` branch, or
2. Go to **Actions** tab > **Test Course Deployment** > **Run workflow**

## Manual Workflow Dispatch

You can test the action using `workflow_dispatch` in your test repository:

1. Go to the **Actions** tab in your repository
2. Select your workflow
3. Click **Run workflow**
4. Select the branch and click **Run workflow**

This allows you to trigger the action on-demand without making code changes.

## Testing Individual Stages

To test specific stages without running the full pipeline, you can create a custom workflow that runs only selected steps:

```yaml
name: Test Individual Stages

on:
  workflow_dispatch:

jobs:
  test-validation:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install UV
        uses: astral-sh/setup-uv@v4
        with:
          version: "latest"
      
      - name: Install dependencies
        run: uv pip install -e .
      
      - name: Test API Key Validation
        run: |
          python src/scripts/validate_api_key.py "${{ secrets.QBRAID_API_KEY }}"
      
      - name: Test Course Validation
        run: |
          python src/scripts/validate_course.py "course.json"
      
      - name: Test Notebook Verification
        run: |
          python src/scripts/verify_notebooks.py
      
      - name: Test Image Checking
        run: |
          python src/scripts/check_images.py
```

## Testing with Local API

You can test the action against a local API server instead of the production API. This is useful for development and debugging.

### Local Script Testing with Local API

Set the `QBRAID_API_BASE_URL` environment variable before running scripts:

```bash
# For local API (scripts append /api/v1, so use base URL only)
export QBRAID_API_BASE_URL="http://localhost:3001"

# Test API key validation
python src/scripts/validate_api_key.py "YOUR_API_KEY"

# Test course creation
python src/scripts/create_course.py "YOUR_API_KEY" "course" "false" "GITHUB_TOKEN" "REPO_URL" "COMMIT_SHA"
```

**Note:** The scripts automatically append `/api/v1` to the base URL, so set `QBRAID_API_BASE_URL` to just the base URL (e.g., `http://localhost:3001`), not the full path.

### Testing in Workflow with Local API

To test against a local API from a GitHub Actions workflow, you'll need to expose your local API to the internet. Here are two approaches:

#### Option 1: Using ngrok (Recommended for Quick Testing)

1. **Start your local API server:**
   ```bash
   # Your API should be running on localhost:3001
   ```

2. **Expose it with ngrok:**
   ```bash
   ngrok http 3001
   # Copy the forwarding URL (e.g., https://abc123.ngrok.io)
   ```

3. **Use the ngrok URL in your workflow:**
   ```yaml
   name: Test with Local API
   
   on:
     workflow_dispatch:
   
   permissions:
     contents: write
   
   jobs:
     test:
       runs-on: ubuntu-latest
       steps:
         - uses: actions/checkout@v6
         
         - name: Deploy to qBraid (Local API)
           env:
             QBRAID_API_BASE_URL: "https://abc123.ngrok.io"  # Your ngrok URL
           uses: courseBuilderNelson/UploadActionRepo@main
           with:
             api-key: ${{ secrets.QBRAID_API_KEY }}
             repo-read-token: ${{ secrets.GITHUB_TOKEN }}
             course-json-path: 'course.json'
   ```

#### Option 2: Using GitHub Codespaces or Self-Hosted Runner

If you're using a self-hosted runner or GitHub Codespaces, you can access localhost directly:

```yaml
name: Test with Local API

on:
  workflow_dispatch:

jobs:
  test:
    runs-on: self-hosted  # or ubuntu-latest for Codespaces
    steps:
      - uses: actions/checkout@v6
      
      - name: Deploy to qBraid (Local API)
        env:
          QBRAID_API_BASE_URL: "http://localhost:3001"
        uses: courseBuilderNelson/UploadActionRepo@main
        with:
          api-key: ${{ secrets.QBRAID_API_KEY }}
          repo-read-token: ${{ secrets.GITHUB_TOKEN }}
          course-json-path: 'course.json'
```

### Complete Local Testing Workflow Example

Create `.github/workflows/test-local-api.yml`:

```yaml
name: Test with Local API

on:
  workflow_dispatch:
    inputs:
      local_api_url:
        description: 'Local API URL (e.g., https://abc123.ngrok.io)'
        required: true
        default: 'https://abc123.ngrok.io'

permissions:
  contents: write

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v6

      - name: Deploy to qBraid (Local API)
        env:
          QBRAID_API_BASE_URL: ${{ inputs.local_api_url }}
        uses: courseBuilderNelson/UploadActionRepo@main
        with:
          api-key: ${{ secrets.QBRAID_API_KEY }}
          repo-read-token: ${{ secrets.GITHUB_TOKEN }}
          course-json-path: 'course.json'
```

### Testing Different Environments

You can override the API base URL for testing against different environments:

```bash
# Local development
export QBRAID_API_BASE_URL="http://localhost:3001"

# Staging environment
export QBRAID_API_BASE_URL="https://staging-api.qbraid.com"

# Production (default, no need to set)
# Uses the default from config.py
```

Or in a workflow:

```yaml
- name: Test with custom API URL
  env:
    QBRAID_API_BASE_URL: "https://staging-api.qbraid.com"
  run: |
    python src/scripts/validate_api_key.py "${{ secrets.QBRAID_API_KEY }}"
```

### Troubleshooting Local API Testing

**Connection refused errors:**
- Ensure your local API server is running
- Check the port number matches (default: 3001)
- Verify firewall settings allow connections

**ngrok URL not working:**
- ngrok URLs change on restart - update your workflow with the new URL
- Free ngrok has connection limits - consider upgrading for extended testing
- Check ngrok dashboard for connection status

**CORS errors:**
- Your local API may need CORS headers to accept requests from GitHub Actions
- Add appropriate CORS configuration to your API server

**URL path issues:**
- Remember: scripts append `/api/v1` automatically
- Set `QBRAID_API_BASE_URL` to base URL only (e.g., `http://localhost:3001`)
- Don't include `/api/v1` in the environment variable

## Troubleshooting Tests

### Script fails with "Module not found"
- Ensure you've installed dependencies: `make install` or `uv pip install -e .`
- Check that you're running from the correct directory

### API key validation fails
- Verify your API key is correct
- Check if you need to set `QBRAID_API_BASE_URL` for a test environment
- Ensure network connectivity to the API endpoint

### Notebook verification fails
- Ensure all file paths in `course.json` are correct
- Check that notebook files exist at the specified paths
- Verify paths are relative to the repository root

### Image checking fails
- Ensure image files exist at referenced paths
- Check that image paths in notebooks are correct (absolute or relative)
- Verify images are under 1MB (if that validation is enabled)

## Best Practices

1. **Start Small**: Test individual scripts before testing the full action
2. **Use Test Data**: Create a minimal `course.json` with just one chapter for initial testing
3. **Test Environment**: Use a test/staging API endpoint if available
4. **Clean Up**: Delete test courses created during testing
5. **Version Control**: Test in a separate branch before merging to main

## Next Steps

After successful testing:
1. Review the [PUBLISHING.md](./PUBLISHING.md) guide for publishing updates
2. Check [WORKFLOW_GUIDE.md](./WORKFLOW_GUIDE.md) for usage documentation
3. Update [README.md](./README.md) if you've made changes
