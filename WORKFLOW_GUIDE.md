# Deploy Course to qBraid - Reusable Workflow

This reusable workflow provides a complete end-to-end solution for deploying educational courses to qBraid's learning platform.

## Overview

The workflow performs the following stages:

1. **Validate course.json** - Ensures the course configuration file has the correct structure
2. **Verify notebooks** - Confirms all referenced notebook files exist
3. **Check image references** - Validates all images referenced in notebooks exist
4. **Upload to GCS** - Uploads all course files to Google Cloud Storage
5. **Create course** - Registers the course with qBraid API
6. **Poll for completion** - Waits for course processing to complete
7. **Notify** - Sends notification with the deployed course URL

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

- **owner_email** (string): Email address of the course owner
- **course_name** (string): Name of the course
- **content** (array): List of chapters

### Chapter Fields

- **kernel_name** (string): Jupyter kernel to use (e.g., "python3", "qsharp")
- **chapter_name** (string): Display name for the chapter
- **file_path** (string): Path to the chapter notebook from repo root
- **sections** (array, optional): List of sections within the chapter

### Section Fields

- **section_obj** (number): Section number/identifier
- **section_name** (string): Display name for the section
- **file_path** (string): Path to the section notebook from repo root

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
    uses: courseBuilderNelson/UploadActionRepo/.github/workflows/deploy-course.yml@v1
    secrets:
      QBRAID_API_KEY: ${{ secrets.QBRAID_API_KEY }}
```

### With Custom course.json Path

```yaml
name: Deploy Course

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    uses: courseBuilderNelson/UploadActionRepo/.github/workflows/deploy-course.yml@v1
    with:
      course-json-path: 'config/course.json'
    secrets:
      QBRAID_API_KEY: ${{ secrets.QBRAID_API_KEY }}
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

## Course Name Formatting

The course name from `course.json` is automatically formatted for GCS storage:

- Spaces replaced with underscores: `My Course` → `My_Course`
- Slashes replaced with hyphens: `Part 1/2` → `Part_1-2`
- Special characters removed: `Course: Advanced!` → `Course_Advanced`

## Workflow Stages

### Stage 1: Validate course.json

Checks that:
- File exists in repository
- Required fields are present
- Content structure is valid
- All chapters have required fields
- All sections (if present) have required fields

### Stage 2: Verify Notebooks

Verifies that:
- All chapter notebook files exist at specified paths
- All section notebook files exist at specified paths

### Stage 3: Check Images

For each notebook, checks:
- All markdown image references exist
- Both absolute (from repo root) and relative paths
- Both Markdown and HTML syntax

### Stage 4: Upload to GCS

Uploads all files to Google Cloud Storage with:
- Formatted course name as destination path
- Proper path structure maintained
- Built-in GCS credentials (users don't provide)

### Stage 5: Create Course

Calls qBraid API:
- Endpoint: `http://api.qbraid.com/learn/create`
- Method: POST
- Payload: `{data: {...course.json}}`
- Expected response: HTTP 201

### Stage 6: Poll Worker

Monitors course processing:
- Polls: `http://api-worker.qbraid.com/status/{course_name}`
- Interval: Every 30 seconds
- Timeout: 30 minutes
- Success: Receives `{qbookUrl: "..."}`

### Stage 7: Notify

On successful deployment:
- Adds comment to PR/issue with course URL
- Creates GitHub Actions summary
- Displays qBook URL for accessing the course

## Secrets Required

### QBRAID_API_KEY

Your qBraid API key for authentication.

**Setup:**
1. Obtain your API key from qBraid
2. Go to your repository Settings → Secrets and variables → Actions
3. Click "New repository secret"
4. Name: `QBRAID_API_KEY`
5. Value: Your API key
6. Click "Add secret"

## Error Handling

The workflow will fail and provide clear error messages if:

- `course.json` is missing or malformed
- Required fields are missing
- Notebook files don't exist at specified paths
- Images referenced in notebooks are missing
- API calls fail
- Worker service times out

## Example Repository Structure

```
my-course/
├── course.json
├── chapter1/
│   ├── intro.ipynb
│   └── section1/
│       └── basics.ipynb
├── chapter2/
│   ├── advanced.ipynb
│   └── images/
│       └── diagram.png
└── assets/
    └── logo.png
```

## Troubleshooting

### Course validation fails

Ensure `course.json` matches the required structure exactly. Check for:
- Missing commas
- Incorrect field names (case-sensitive)
- Missing required fields

### Notebook not found

Verify that:
- File paths in `course.json` are correct
- Paths are relative to repository root
- File extensions are correct (`.ipynb`)

### Image references missing

Check that:
- Image files exist at specified paths
- Relative paths are correct from notebook location
- Absolute paths start with `/` and are from repo root

### API call fails

Verify that:
- `QBRAID_API_KEY` secret is set correctly
- API key is valid and active
- You have permissions to create courses

### Worker timeout

The worker service may take time to process large courses. If timeout occurs:
- Check worker service status
- Contact qBraid support if needed

## Outputs

The workflow provides:

- **formatted_course_name**: Sanitized course name used for GCS storage
- **qbook_url**: URL where the deployed course can be accessed

## Support

For issues related to:
- **Workflow**: Open an issue in this repository
- **qBraid API**: Contact qBraid support
- **Course content**: Check your course.json and notebook files

## License

MIT
