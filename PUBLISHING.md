# Publishing to GitHub Marketplace

This guide explains how to publish this action to the GitHub Marketplace.

## Prerequisites

✅ The action code is complete and tested.
✅ All files (including `src/scripts/` and `requirements.txt`) are committed.
✅ `action.yml` is properly configured.

## Steps to Publish

### 1. Create a Release

1.  Go to your repository on GitHub.
2.  Click on "Releases" in the right sidebar.
3.  Click "Draft a new release".

### 2. Configure the Release

**Tag version:**
-   Use semantic versioning: `v1.0.0` (or increment for updates).

**Release title:**
-   Example: `v1.0.0 - Initial Release`

**Publish this Action to the GitHub Marketplace:**
-   Check this box.
-   Select the category (e.g., "Deployment").

**Description:**
Describe the changes. For example:
```markdown
## Deploy Course to qBraid - v1.0.0

A Composite GitHub Action for deploying educational courses to qBraid.

### Features
- 🚀 Secure uploads using Signed URLs (No GCS keys needed!)
- 🔐 API Key validation
- ✅ Automated course structure validation
- 🎓 Course creation and deployment
```

### 3. Publish

Click "Publish release".

## Versioning Strategy

-   **Major (v1.0.0)**: Breaking changes (e.g., changing input names).
-   **Minor (v1.1.0)**: New features (e.g., new validation checks).
-   **Patch (v1.0.1)**: Bug fixes.

Users can pin to a specific version tag (e.g., `@v1.0.0`) or the major version (e.g., `@v1`) to get updates automatically.
