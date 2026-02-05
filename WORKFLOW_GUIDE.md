# Deploy Course to qBraid - Workflow Guide

This guide explains how to use the "Deploy Course to qBraid" action to automate your course deployment.

## Overview

The action performs the following stages:

1.  **Validate API Key**: Checks if your `QBRAID_API_KEY` is valid.
2.  **Validate course.json**: Ensures the course configuration file has the correct structure.
3.  **Verify notebooks**: Confirms all referenced notebook files exist and validates security.
4.  **Check image references**: Validates all images referenced in notebooks exist and are under 1MB.
5.  **Create course**: Registers the course with qBraid API using repository metadata.
6.  **Poll for completion**: Waits for course processing to complete.
7.  **Notify**: Sends notification with the deployed course URL.

## course.json Structure

Your repository must contain a `course.json` file in the root with the following structure:

```json
{
  "courseName": "Introduction to Quantum Computing",
  "courseDescription": "A beginner-friendly course on quantum computing fundamentals",
  "visibility": "public",
  "imageLink": {
    "darkLogo": "https://example.com/dark-logo.jpg",
    "lightLogo": "https://example.com/light-logo.jpg"
  },
  "tags": ["quantum computing", "beginner"],
  "deployedTo": ["qbraid.com"],
  "content": [
    {
      "chapterName": "Introduction to Python",
      "chapterNumber": 1,
      "baseFilePath": "./chapter1/intro.ipynb",
      "kernelName": "python3",
      "kernelId": "Python 3",
      "sections": [
        {
          "sectionNumber": 1.1,
          "sectionName": "Getting Started",
          "baseFilePath": "./chapter1/section1/getting_started.ipynb",
          "kernelName": "python3",
          "kernelId": "Python 3"
        }
      ]
    }
  ]
}
```

### Required Root Fields

-   **courseName** (string): Name of the course
-   **courseDescription** (string): Brief description of the course
-   **visibility** (string): Visibility setting (e.g., "public", "private")
-   **imageLink** (object): Logo URLs for dark and light themes
    -   **darkLogo** (string): URL for dark theme logo
    -   **lightLogo** (string): URL for light theme logo
-   **tags** (array of strings): List of tags for the course
-   **deployedTo** (array of strings): Deployment targets (allowed: "qbraid.com", "quera.com")
-   **content** (array): List of chapters

### Chapter Fields

-   **chapterName** (string): Display name for the chapter
-   **chapterNumber** (number): Chapter number/order
-   **baseFilePath** (string): Path to the chapter notebook from repo root (max 5MB)
-   **kernelName** (string): Jupyter kernel to use (e.g., "python3", "qbraid_python")
-   **kernelId** (string): Display name for the kernel
-   **sections** (array, optional): List of sections within the chapter

### Section Fields

-   **sectionNumber** (number): Section number/identifier
-   **sectionName** (string): Display name for the section
-   **baseFilePath** (string): Path to the section notebook from repo root (max 5MB)
-   **kernelName** (string): Jupyter kernel to use
-   **kernelId** (string): Display name for the kernel

## Usage

### In Your Repository

Create a workflow file (e.g., `.github/workflows/deploy.yml`) in your course repository:

```yaml
name: Deploy Course

on:
  push:
    branches: [ main ]
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: courseBuilderNelson/UploadActionRepo@main
        with:
          api-key: ${{ secrets.QBRAID_API_KEY }}
```

### With Custom course.json Path

```yaml
name: Deploy Course

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: courseBuilderNelson/UploadActionRepo@main
        with:
          api-key: ${{ secrets.QBRAID_API_KEY }}
          course-json-path: 'config/course.json'
```

## Image References in Notebooks

The workflow validates image references in markdown cells. Images can be referenced using:

### Absolute Paths (from repo root)

```markdown
![Diagram](/assets/images/diagram.png)
```

### Relative Paths (from notebook location)

```markdown
![Chart](../images/chart.png)
```

### HTML Image Tags

```html
<img src="./images/photo.jpg" alt="Photo">
```

**Note:** HTTP/HTTPS URLs are allowed and won't be validated.

## Troubleshooting

### API Key Validation Fails
- Ensure `QBRAID_API_KEY` is set in your repository secrets.
- Verify the key is active and correct.

### Course validation fails
- Ensure `course.json` matches the required structure exactly.
- Check for missing commas or incorrect field names.

### Notebook not found
- Verify that file paths in `course.json` are correct and relative to repository root.

### Image references missing
- Check that image files exist at specified paths.

### Upload fails
- Ensure your API key has permissions to upload files.
- Check if the file paths contain special characters that might cause issues.
- If the API is slow, increase `QBRAID_REQUEST_TIMEOUT_SECONDS` in your workflow `env` (default: `30`).

Example:

```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest
    env:
      QBRAID_REQUEST_TIMEOUT_SECONDS: "60"
    steps:
      - uses: actions/checkout@v6
      - uses: qBraid/upload-course-api@v0.1.0-beta
        with:
          api-key: ${{ secrets.QBRAID_API_KEY }}
          repo-read-token: ${{ secrets.GITHUB_TOKEN }}
```

## Support

For issues related to:
-   **Workflow**: Open an issue in this repository
-   **qBraid API**: Contact qBraid support
-   **Course content**: Check your course.json and notebook files
