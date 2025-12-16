# GitHub Action Development Summary

## Overview
This repository contains a GitHub Action that uploads repository contents to Google Cloud Storage (GCS) buckets using qBraid API key authentication.

## Key Components

### 1. action.yml
- Defines the action metadata for GitHub Marketplace
- Specifies inputs (bucket-name, api-key, source-path, destination-path, exclude-patterns)
- Specifies outputs (upload-status, files-uploaded, upload-url)
- Uses Node.js 20 runtime
- Entry point: dist/index.js

### 2. src/index.js
Main action logic:
- Parses exclude patterns from user input
- Scans repository for files to upload (respecting exclusions)
- Authenticates with GCS using service account credentials
- Uploads files to specified GCS bucket
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

The action expects `QBRAID_API_KEY` to be a Google Cloud Service Account key in JSON format:
```json
{
  "type": "service_account",
  "project_id": "...",
  "private_key_id": "...",
  "private_key": "...",
  "client_email": "...",
  ...
}
```

Users must:
1. Create a GCS service account with appropriate permissions
2. Download the service account key as JSON
3. Add it to repository secrets as `QBRAID_API_KEY`

## How to Use

Users add this action to their workflow:

```yaml
- uses: courseBuilderNelson/UploadActionRepo@v1
  with:
    bucket-name: 'my-bucket'
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
