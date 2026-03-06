# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [v0.1.0-beta] - 2026-01-30

### Beta Release
- Initial beta release for GitHub Marketplace testing
- Uses qBraid staging API environment
- Ready for early adopters and testing
- Full deployment pipeline implemented
- Security scanning and validation included

### Environment
- **API Endpoint**: `api-v2.qbraid.com`
- **Status**: Beta - Not for production use
- **Support**: Community feedback encouraged

### Usage
```yaml
uses: qBraid/upload-course-action@v0.1.0-beta
```

## [Unreleased]

### Fixed
- Fixed JSend response parsing in deploy and polling scripts to support `{status, data}` envelope format
- Added guard in `action.yml` to fail early with a clear error when `course_custom_id` is empty after create/update step
- Replaced silent `pass` with warning logs when API response parsing fails

### Added
- Unit tests for JSend response handling in course creation and polling
- Unit tests for shared deploy payload/response handling in `deploy_common.py`
- Action inputs to configure polling limits (`max-poll-attempts`, `poll-interval-seconds`, `max-consecutive-errors`)
- Comprehensive pytest testing infrastructure with unit and E2E tests
- Test markers for easy filtering (`@pytest.mark.unit`, `@pytest.mark.e2e`)
- Shared test fixtures in `test/conftest.py` for mocking and GitHub Actions simulation
- CI/CD workflow with automated testing on push/PR
- Coverage reporting with pytest-cov
- Edge case E2E tests for "nasty" inputs (spaces, newlines, unicode, etc.)
- Workflow checks with actionlint and zizmor
- GitHub Actions runner simulation fixtures (`github_output`, `github_env`, `runner_filesystem`)
- Automated CI workflow for formatting (Black, isort), linting (Pylint), spell checking, action metadata linting, and pytest matrix testing
- PR changelog guard workflow that requires `CHANGELOG.md` updates when code-related files change
- Typos configuration file to ignore generated artifacts and allow project-specific terms (`qbraid`, `qbook`)

### Added
- Certificate settings support for course creation and updates via `certificate-enabled`, `certificate-criteria-type`, and `certificate-criteria-value` action inputs
- Certificate criteria validation (type must be `completion` or `points`; value must be in range 0–100 for completion)
- Certificate settings payload construction in `deploy_common.py` shared by create and update flows
- Comprehensive unit tests for certificate settings handling in `CourseDeployer` and `CourseUpdater`

### Changed
- Increased default polling attempts to 20 (from 10)
- Updated CI coverage upload to Codecov to support token upload with OIDC fallback when `CODECOV_TOKEN` is unavailable
- Updated test infrastructure to use pytest exclusively
- Improved test organization with markers and shared fixtures
- Enhanced Makefile with coverage commands
- Added configurable polling controls via environment variables:
  `QBRAID_MAX_POLL_ATTEMPTS`, `QBRAID_POLL_INTERVAL_SECONDS`,
  and `QBRAID_MAX_CONSECUTIVE_ERRORS`
- Updated default `QBRAID_MAX_POLL_ATTEMPTS` to `15`
- Documented polling environment configuration in `README.md` and `WORKFLOW_GUIDE.md`
- Increased default qBraid API request timeout from 5s to 30s for course deployment steps
- Added configurable request timeout via `QBRAID_REQUEST_TIMEOUT_SECONDS` (positive integer)
- Documented timeout/environment configuration in `README.md` and `WORKFLOW_GUIDE.md`

## [Unreleased]
### Planned for v1.0.0 (Stable)
- Production API integration
- Performance optimizations
- Additional user feedback improvements
- Full documentation updates

## [0.1.0-beta] - 2026-01-30

### Added
- Initial release of Deploy Course Action
- API key validation
- Course JSON structure validation
- Notebook file verification and security scanning
- Image reference validation
- Course creation via qBraid API
- Progress polling for course processing
- Deployment notifications via commit comments
- Support for course and blog article types
- Optional force duplicate questions flag
- Environment variable override for API base URL (`QBRAID_API_BASE_URL`)

### Security
- API key validation before operations
- Notebook content security scanning (XSS, script injection, credential detection)
- File size limits (5MB for notebooks, 15MB for images)
- Secure repository access via GitHub tokens
- No credentials stored in action code

[v1.0.0]: https://github.com/qBraid/upload-course-action/releases/tag/v1.0.0 (planned)

[Unreleased]: https://github.com/qBraid/upload-course-action/compare/v0.1.0-beta...HEAD
[v0.1.0-beta]: https://github.com/qBraid/upload-course-action/releases/tag/v0.1.0-beta
