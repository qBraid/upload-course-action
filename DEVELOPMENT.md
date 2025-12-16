# GitHub Action Development Summary

## Overview
This repository contains a GitHub Action that uploads repository contents to a Google Cloud Storage (GCS) bucket using qBraid API key authentication.

## Key Components

### 1. action.yml
- Defines the action metadata for GitHub Marketplace
- Specifies inputs (api-key, source-path, destination-path, exclude-patterns)
- Specifies outputs (upload-status, files-uploaded, upload-url)
- Uses Node.js 20 runtime
- Entry point: dist/index.js

### 2. src/index.js
Main action logic:
- Validates qBraid API key for authentication
- Parses exclude patterns from user input
- Scans repository for files to upload (respecting exclusions)
- Authenticates with GCS using built-in service account credentials
- Uploads files to preconfigured GCS bucket
- Reports status and metrics

### 3. package.json
Dependencies:
- @actions/core: GitHub Actions SDK for inputs/outputs/logging
- @google-cloud/storage: Official GCS client library
- glob: File pattern matching
- @vercel/ncc: Bundles code into single dist/index.js

### 4. dist/
Contains compiled action code (required for GitHub Actions):
- index.js: Bundled action code with all dependencies
- index.js.map: Source map for debugging
- licenses.txt: Third-party license information
- sourcemap-register.js: Source map support

## Authentication

The action uses a two-layer authentication approach:

1. **User Authentication**: Users provide a qBraid API key via the `QBRAID_API_KEY` secret
   - The action validates this key to authenticate the user
   - This is a simple string API key obtained from qBraid

2. **GCS Authentication**: The action has built-in GCS service account credentials
   - Configured via environment variable `GCS_SERVICE_ACCOUNT_KEY`
   - Should be set in the action's repository secrets/environment
   - Users do not need to provide GCS credentials

## Configuration

The action requires the following to be configured in the action repository (not by users):

1. **GCS_SERVICE_ACCOUNT_KEY**: Environment variable containing the GCS service account JSON
2. **GCS_BUCKET_NAME**: Environment variable for the bucket name (default: 'qbraid-upload-bucket')

Users only need to provide:
- `QBRAID_API_KEY`: Their qBraid API key for authentication

## How to Use

Users add this action to their workflow:

```yaml
- uses: courseBuilderNelson/UploadActionRepo@v1
  with:
    api-key: ${{ secrets.QBRAID_API_KEY }}
```

## Build Process

1. Source code in `src/index.js`
2. Run `npm run build` to compile with @vercel/ncc
3. Outputs bundled code to `dist/index.js`
4. Commit dist/ folder (required by GitHub Actions)

## Publishing to Marketplace

To publish:
1. Create a release on GitHub (e.g., v1.0.0)
2. Tag the release (e.g., v1)
3. Mark as "Publish this Action to the GitHub Marketplace"
4. GitHub will automatically list it for users to discover

## Security Considerations

✅ API keys handled securely via GitHub Actions secrets
✅ Input validation for all user inputs
✅ Safe path resolution (no directory traversal)
✅ Proper error handling (no sensitive data in logs)
✅ No command injection vulnerabilities
✅ Uses official, maintained libraries

## File Exclusions

Default exclusions (can be customized):
- .git/** (version control)
- node_modules/** (dependencies)
- .github/** (workflow files)

## Outputs

The action provides:
- `upload-status`: success/failed/skipped
- `files-uploaded`: number of files uploaded
- `upload-url`: base URL of uploaded content in GCS
