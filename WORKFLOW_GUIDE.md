# Deploy Course to qBraid - Workflow Guide

This guide explains how to use the "Deploy Course to qBraid" action to automate your course deployment.

## Overview

The action performs the following stages:

1.  **Validate API Key**: Checks if your `QBRAID_API_KEY` is valid.
2.  **Validate course.json**: Ensures the course configuration file has the correct structure.
3.  **Verify notebooks**: Confirms all referenced notebook files exist.
4.  **Check image references**: Validates all images referenced in notebooks exist.
5.  **Upload to GCS**: Uploads all course files to Google Cloud Storage using secure Signed URLs.
6.  **Create course**: Registers the course with qBraid API.
7.  **Poll for completion**: Waits for course processing to complete.
8.  **Notify**: Sends notification with the deployed course URL.

## course.json Structure

Your repository must contain a `course.json` file in the root with the following structure:

```json
{
  "owner_email": "owner@example.com",
  "course_name": "Your Course Name",
  "content": [
    {
      "kernel_name": "python3",
      "chapter_name": "Introduction to Python",
      "file_path": "./chapter1/intro.ipynb",
      "sections": [
        {
          "section_obj": 1,
          "section_name": "Getting Started",
          "file_path": "./chapter1/section1/getting_started.ipynb"
        }
      ]
    }
  ]
}
```

### Required Fields

-   **owner_email** (string): Email address of the course owner
-   **course_name** (string): Name of the course
-   **content** (array): List of chapters

### Chapter Fields

-   **kernel_name** (string): Jupyter kernel to use (e.g., "python3", "qsharp")
-   **chapter_name** (string): Display name for the chapter
-   **file_path** (string): Path to the chapter notebook from repo root
-   **sections** (array, optional): List of sections within the chapter

### Section Fields

-   **section_obj** (number): Section number/identifier
-   **section_name** (string): Display name for the section
-   **file_path** (string): Path to the section notebook from repo root

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
      - uses: actions/checkout@v4
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
      - uses: actions/checkout@v4
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

## Support

For issues related to:
-   **Workflow**: Open an issue in this repository
-   **qBraid API**: Contact qBraid support
-   **Course content**: Check your course.json and notebook files
