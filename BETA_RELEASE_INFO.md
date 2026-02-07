# Beta Release Information

## Beta Status: v0.1.0-beta

This is a **beta release** of the qBraid Course Deployment GitHub Action. Please review this information before use.

### 🚨 Important Beta Notices

- **Environment**: Uses qBraid staging API (`api-v2.qbraid.com`)
- **Stability**: May undergo breaking changes without notice
- **Production Use**: **NOT RECOMMENDED** until stable release
- **Data Persistence**: Staging environment data may be cleared periodically
- **Performance**: May differ from production environment

### ✅ What Works in Beta

- ✅ Complete course deployment pipeline
- ✅ API key validation and authentication
- ✅ Notebook security scanning and validation
- ✅ Image reference checking
- ✅ Progress monitoring and notifications
- ✅ GitHub Actions integration
- ✅ Comprehensive error handling

### ⚠️ Current Limitations

- **Staging API**: Uses non-production environment
- **Rate Limits**: May have stricter limits than production
- **Feature Completeness**: Some advanced features may be in development
- **Data Longevity**: Created courses may not persist long-term

### 🔧 How to Use Beta

In your `.github/workflows/deploy.yml`:

```yaml
name: Deploy Course to qBraid

on:
  push:
    branches: [ main ]
  workflow_dispatch:

permissions:
  contents: write

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v6

      - name: Deploy to qBraid (Beta)
        uses: qBraid/upload-course-api@v0.1.0-beta
        with:
          api-key: ${{ secrets.QBRAID_API_KEY }}
          repo-read-token: ${{ secrets.GITHUB_TOKEN }}
```

### 📋 Prerequisites

1. **qBraid API Key**: Get from qBraid staging environment
2. **Repository Setup**: Valid `course.json` file
3. **Permissions**: `Read and write permissions` in repository settings
4. **Content**: Jupyter notebooks and images under size limits

### 🐛 Reporting Issues

Please report beta-specific issues:

1. **GitHub Issues**: [Create Issue](https://github.com/qBraid/upload-course-api/issues)
2. **Label**: Include "BETA" in issue title
3. **Environment**: Specify you're using staging API
4. **Details**: Include course.json (sanitized) and workflow steps

### 📝 Feedback Collection

We particularly value feedback on:

- **Ease of Use**: How intuitive is the setup process?
- **Error Messages**: Are error messages clear and helpful?
- **Performance**: How long does deployment take?
- **Documentation**: What's unclear or missing?
- **Features**: What would make this action more useful?

### 🔄 Path to Stable Release

1. **Beta Phase** (Current): v0.1.0-beta with staging API
2. **Release Candidate**: v0.1.0-rc.1 with production API
3. **Stable Release**: v1.0.0 with production guarantees

### 🔄 Migration from Beta to Stable

When stable version is released, update your workflows:

```yaml
# Before (Beta)
uses: qBraid/upload-course-api@v0.1.0-beta

# After (Stable)
uses: qBraid/upload-course-api@v1.0.0
```

### 🛡️ Security Considerations

- ✅ API keys are validated and never logged
- ✅ Notebook content is scanned for security issues
- ✅ File size limits prevent resource abuse
- ✅ Repository access uses GitHub tokens with minimal permissions

### 📞 Support

- **Documentation**: [README.md](README.md)
- **Examples**: [examples/](examples/)
- **Testing Guide**: [TESTING.md](TESTING.md)
- **Agent Integration**: [AGENTS.md](AGENTS.md)

---

**Thank you for testing our beta release! Your feedback helps us build a better product.**