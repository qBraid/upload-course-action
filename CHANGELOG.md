# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Comprehensive pytest testing infrastructure with unit and E2E tests
- Test markers for easy filtering (`@pytest.mark.unit`, `@pytest.mark.e2e`)
- Shared test fixtures in `test/conftest.py` for mocking and GitHub Actions simulation
- CI/CD workflow with automated testing on push/PR
- Coverage reporting with pytest-cov
- Edge case E2E tests for "nasty" inputs (spaces, newlines, unicode, etc.)
- Workflow checks with actionlint and zizmor
- GitHub Actions runner simulation fixtures (`github_output`, `github_env`, `runner_filesystem`)

### Changed
- Updated test infrastructure to use pytest exclusively
- Improved test organization with markers and shared fixtures
- Enhanced Makefile with coverage commands

## [0.1.0] - 2026-01-XX

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

[Unreleased]: https://github.com/qBraid/upload-course-api/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/qBraid/upload-course-api/releases/tag/v0.1.0
