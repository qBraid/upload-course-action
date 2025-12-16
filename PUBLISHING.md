# Publishing to GitHub Marketplace

This guide explains how to publish this action to the GitHub Marketplace so that users can discover and use it.

## Prerequisites

✅ The action code is complete and tested
✅ All files are committed to the repository
✅ The dist/ folder is committed (contains compiled code)
✅ action.yml is properly configured with branding

## Steps to Publish

### 1. Create a Release

1. Go to your repository on GitHub
2. Click on "Releases" in the right sidebar
3. Click "Draft a new release"

### 2. Configure the Release

**Tag version:**
- Use semantic versioning: `v1.0.0`
- First release should be `v1.0.0`

**Release title:**
- Example: `v1.0.0 - Initial Release`

**Description:**
Include a description of what the action does:
```markdown
## Upload to GCS Action - Initial Release

A GitHub Action that uploads repository contents to Google Cloud Storage buckets using qBraid API key authentication.

### Features
- 🚀 Upload files and directories to GCS buckets
- 🔐 Secure authentication using qBraid API key
- 📁 Flexible source and destination path configuration
- 🎯 Pattern-based file exclusion
- 📊 Detailed upload status and metrics

### Usage
See the [README](https://github.com/courseBuilderNelson/UploadActionRepo/blob/main/README.md) for detailed usage instructions.

### Requirements
- A Google Cloud Storage bucket
- A qBraid API key (GCS service account) added as `QBRAID_API_KEY` secret
```

### 3. Publish to Marketplace

**Important:** Check the box that says:
☑️ **"Publish this Action to the GitHub Marketplace"**

GitHub will ask you to accept the terms. Review and accept them.

### 4. Create Version Tags

After publishing v1.0.0, create major version tags for easier user adoption:

```bash
git tag v1
git push origin v1
```

This allows users to reference the action as `@v1` instead of `@v1.0.0`, and they'll automatically get patch and minor updates.

## Updating the Action

When you make updates:

1. Make your code changes
2. Update version in package.json
3. Rebuild: `npm run build`
4. Commit changes
5. Create a new release (e.g., v1.0.1, v1.1.0, v2.0.0)
6. Update the major version tag if needed:
   ```bash
   git tag -fa v1 -m "Update v1 tag"
   git push origin v1 --force
   ```

## Version Tags Best Practices

- `v1.0.0`, `v1.0.1`, etc. - Specific versions (immutable)
- `v1` - Points to latest v1.x.x (movable)
- Users can choose: `@v1` (latest) or `@v1.0.0` (specific)

## After Publishing

Users will be able to use your action like this:

```yaml
- uses: courseBuilderNelson/UploadActionRepo@v1
  with:
    bucket-name: 'my-bucket'
    api-key: ${{ secrets.QBRAID_API_KEY }}
```

## Marketplace Categories

When publishing, you can select categories to help users discover your action:
- Deployment
- Publishing
- Utilities

## Action Badge

After publishing, GitHub provides a badge you can add to your README:

```markdown
![GitHub Marketplace](https://img.shields.io/badge/Marketplace-Upload%20to%20GCS-blue?logo=github)
```

## Troubleshooting

### "Action must have a unique name"
If someone already has an action with the same name, update the `name` field in action.yml.

### "dist folder is required"
Ensure the dist/ folder is committed to the repository. GitHub Actions need the compiled code.

### "action.yml validation failed"
Check that action.yml follows the correct syntax. Run a YAML validator if needed.

## Support

Add the following to your README to help users:
- Link to example workflows
- Link to issue tracker for bug reports
- Link to discussions for questions
