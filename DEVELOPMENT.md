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

### 3. pyproject.toml
Python dependencies are managed via `pyproject.toml` using UV. Main dependencies:
- `requests`
- `nbformat`
- `qbraid-core`
- `pydantic`
- `tenacity`

Test dependencies are in the `[project.optional-dependencies]` section.

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
    
    # Or run the test suite
    make test
    ```
3.  **Format Code**: Before committing, format your code:
    ```bash
    make format  # Auto-formats code and adds headers
    ```
4.  **Update Action**: If you change inputs/outputs, update `action.yml`.
5.  **Update Changelog**: Add your changes to `CHANGELOG.md` under `[Unreleased]`.
6.  **Commit**: Commit changes to `main`. Since this is a composite action, no build step is required.

### Git Hooks

A **pre-push hook** automatically formats code before pushing to remote. If code is reformatted, the push will be aborted and you'll need to commit the formatting changes first.

**Install the hook:**
```bash
make install-hooks
```

**Manual formatting:**
```bash
make format        # Auto-format code
make format-check  # Check if code is formatted (doesn't modify files)
```

**Note:** The hook uses `uv run make format` if `uv` is available, otherwise falls back to `make format` directly.

## Versioning

This project follows [Semantic Versioning](https://semver.org/):
- **MAJOR** version for incompatible API changes
- **MINOR** version for new functionality in a backward compatible manner
- **PATCH** version for backward compatible bug fixes

### Version Management

The version is stored in two places:
- `VERSION` file (single source of truth)
- `pyproject.toml` (for Python package metadata)

### Bumping Versions

```bash
# View current version
make version

# Bump patch version (0.1.0 -> 0.1.1)
make bump-patch

# Bump minor version (0.1.0 -> 0.2.0)
make bump-minor

# Bump major version (0.1.0 -> 1.0.0)
make bump-major

# Set specific version
make bump-version V=0.2.0
```

### Release Process

1. **Update CHANGELOG.md**: Move items from `[Unreleased]` to a new version section
2. **Bump version**: Use `make bump-patch`, `make bump-minor`, or `make bump-major`
3. **Commit changes**: 
   ```bash
   git add VERSION pyproject.toml CHANGELOG.md
   git commit -m "Bump version to vX.Y.Z"
   ```
4. **Create and push tag**:
   ```bash
   git tag -a vX.Y.Z -m "Release vX.Y.Z"
   git push && git push --tags
   ```
5. **GitHub Release**: The `.github/workflows/release.yml` workflow will automatically create a GitHub release when a tag is pushed

## Security Considerations

✅ **No Secrets in Action**: The action does not store GCS credentials or other sensitive data.
✅ **API Key Validation**: The API key is validated before any operations.
✅ **Secure Repository Access**: Uses GitHub tokens with read-only scope.
✅ **Input Validation**: All user inputs and file content are validated by the scripts.
✅ **Content Security**: Notebooks are scanned for XSS vulnerabilities, malicious scripts, and embedded credentials.
✅ **Size Limits**: Enforces file size limits (5MB for notebooks, 1MB for images).
✅ **Environment Override**: API base URL can be overridden via `QBRAID_API_BASE_URL` environment variable for testing.
