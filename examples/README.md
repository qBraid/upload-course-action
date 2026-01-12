# Examples

This directory contains example files to help you get started with the Deploy Course Action.

## Files

### `course.json`
Example course configuration file showing the required structure and fields. Use this as a reference when creating your own `course.json`.

**Location:** Place `course.json` in your repository root (or specify a custom path via `course-json-path` input).

### `workflow.yml` (formerly `example.yaml`)
Production-ready workflow example for deploying courses. This is the main example you should reference.

**Usage:** Copy this to `.github/workflows/deploy.yml` in your repository.

**Features:**
- Deploys on push to main branch
- Supports manual triggering via `workflow_dispatch`
- Shows deployment results

### `test-workflow-unpublished.yml`
Workflow for testing the action before it's published to the marketplace. Useful when:
- Testing changes from a feature branch
- Using a specific commit SHA
- Testing before a release

**Usage:** Copy to your test repository's `.github/workflows/` directory.

### `test-workflow-act-local.yml`
Workflow for local testing using [`act`](https://github.com/nektos/act). This allows you to test the action locally without pushing to GitHub.

**Usage:**
1. Install `act`: `brew install act` (macOS) or see [act installation](https://github.com/nektos/act#installation)
2. Create `.secrets` file with your API key
3. Run: `act workflow_dispatch -W .github/workflows/test-act.yml --secret-file .secrets`

**Note:** This workflow uses `uses: ./` to reference the local action, which only works with `act`.

## Quick Start

1. **Copy the workflow:**
   ```bash
   cp examples/workflow.yml .github/workflows/deploy.yml
   ```

2. **Create your course.json:**
   ```bash
   cp examples/course.json course.json
   # Edit course.json with your course details
   ```

3. **Add secrets:**
   - Go to your repository Settings > Secrets and variables > Actions
   - Add `QBRAID_API_KEY` with your qBraid API key

4. **Enable permissions:**
   - Go to Settings > Actions > General > Workflow permissions
   - Select "Read and write permissions"

5. **Push and deploy:**
   ```bash
   git add .github/workflows/deploy.yml course.json
   git commit -m "Add course deployment workflow"
   git push
   ```

## Testing Locally

For local testing with a local API or before publishing:

- **With act:** Use `test-workflow-act-local.yml` (see above)
- **With local API:** Set `QBRAID_API_BASE_URL` environment variable (see [TESTING.md](../TESTING.md))
- **Unpublished action:** Use `test-workflow-unpublished.yml` in a test repository

For more details, see [TESTING.md](../TESTING.md).
