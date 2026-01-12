.PHONY: install install-test install-dev test test-unit test-e2e test-coverage coverage-report coverage-html format format-check lint lint-check check-headers clean sync lock version bump-version bump-patch bump-minor bump-major

install:
	uv sync

install-test:
	uv sync --extra test

install-dev:
	uv sync --extra dev --extra test

format:
	@echo "Formatting code with black and isort..."
	black src/scripts test
	isort src/scripts test
	@echo "✅ Formatting complete"

format-check:
	@echo "=== Checking code formatting ==="
	@echo "Checking black..."
	@black --check src/scripts test || (echo "❌ Code is not formatted. Run 'make format' to fix." && exit 1)
	@echo "Checking isort..."
	@isort --check-only src/scripts test || (echo "❌ Imports are not sorted. Run 'make format' to fix." && exit 1)
	@echo "Checking pylint..."
	@pylint src/scripts --rcfile=.pylintrc --fail-under=7.0 || (echo "❌ Pylint score is below 7.0. Fix issues before committing." && exit 1)
	@echo "Checking headers..."
	@HEADER_PATTERN="# Copyright (C)"; \
	MISSING_HEADERS=0; \
	for file in $$(find src/scripts -name "*.py" -type f ! -name "__init__.py"); do \
		if ! head -1 "$$file" | grep -q "$$HEADER_PATTERN"; then \
			echo "❌ Missing header in: $$file"; \
			MISSING_HEADERS=1; \
		fi; \
	done; \
	if [ $$MISSING_HEADERS -eq 1 ]; then \
		echo "❌ Some files are missing copyright headers."; \
		echo "Expected header format:"; \
		echo "# Copyright (C) 2024 qBraid"; \
		exit 1; \
	fi
	@echo "✅ All checks passed (black, isort, pylint, headers)"

lint:
	@echo "Running linters..."
	@if command -v ruff > /dev/null; then \
		ruff check src/scripts test; \
	else \
		echo "⚠️  ruff not installed. Install with: uv pip install ruff"; \
	fi

lint-check:
	@echo "Running pylint..."
	@pylint src/scripts --disable=C0111,C0103,R0913,R0912 || (echo "❌ Pylint found issues. Fix them before committing." && exit 1)
	@echo "✅ Pylint checks passed"

check-headers:
	@echo "Checking file headers..."
	@HEADER_PATTERN="# Copyright (C)"; \
	MISSING_HEADERS=0; \
	for file in $$(find src/scripts -name "*.py" -type f ! -name "__init__.py"); do \
		if ! head -1 "$$file" | grep -q "$$HEADER_PATTERN"; then \
			echo "❌ Missing header in: $$file"; \
			MISSING_HEADERS=1; \
		fi; \
	done; \
	if [ $$MISSING_HEADERS -eq 1 ]; then \
		echo "❌ Some files are missing copyright headers."; \
		echo "Expected header format:"; \
		echo "# Copyright (C) 2024 qBraid"; \
		exit 1; \
	else \
		echo "✅ All files have proper headers"; \
	fi

sync:
	uv sync --all-groups

lock:
	uv lock

test: test-unit test-e2e

test-unit:
	pytest -q test/unit --no-cov

test-e2e:
	pytest -q test/e2e --no-cov

test-coverage:
	pytest --cov=src/scripts --cov-report=term-missing --cov-report=html --cov-report=xml

coverage-report:
	pytest --cov=src/scripts --cov-report=term-missing --cov-report=html --cov-report=xml
	@echo "Coverage report generated in htmlcov/index.html"

coverage-html:
	pytest --cov=src/scripts --cov-report=html
	@echo "Opening coverage report..."
	@python -m webbrowser htmlcov/index.html || open htmlcov/index.html || xdg-open htmlcov/index.html

version:
	@echo "Current version: $$(cat VERSION)"
	@echo "Version in pyproject.toml: $$(grep '^version =' pyproject.toml | cut -d'"' -f2)"

bump-version:
	@if [ -z "$(V)" ]; then \
		echo "Usage: make bump-version V=x.y.z"; \
		exit 1; \
	fi
	@echo "$(V)" > VERSION
	@sed -i.bak 's/^version = ".*"/version = "$(V)"/' pyproject.toml && rm pyproject.toml.bak
	@echo "Version bumped to $(V)"
	@echo "Don't forget to:"
	@echo "  1. Update CHANGELOG.md with the new version"
	@echo "  2. Commit changes: git add VERSION pyproject.toml CHANGELOG.md"
	@echo "  3. Create tag: git tag -a v$(V) -m 'Release v$(V)'"
	@echo "  4. Push: git push && git push --tags"

bump-patch:
	@VERSION=$$(cat VERSION); \
	MAJOR=$$(echo $$VERSION | cut -d. -f1); \
	MINOR=$$(echo $$VERSION | cut -d. -f2); \
	PATCH=$$(echo $$VERSION | cut -d. -f3); \
	NEW_VERSION="$$MAJOR.$$MINOR.$$((PATCH + 1))"; \
	$(MAKE) bump-version V=$$NEW_VERSION

bump-minor:
	@VERSION=$$(cat VERSION); \
	MAJOR=$$(echo $$VERSION | cut -d. -f1); \
	MINOR=$$(echo $$VERSION | cut -d. -f2); \
	NEW_VERSION="$$MAJOR.$$((MINOR + 1)).0"; \
	$(MAKE) bump-version V=$$NEW_VERSION

bump-major:
	@VERSION=$$(cat VERSION); \
	MAJOR=$$(echo $$VERSION | cut -d. -f1); \
	NEW_VERSION="$$((MAJOR + 1)).0.0"; \
	$(MAKE) bump-version V=$$NEW_VERSION

clean:
	find . -type d -name '__pycache__' -exec rm -rf {} +
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov
	rm -rf coverage.xml
	rm -f course_data.json
	rm -rf .venv
	rm -rf test/e2e/temp_nasty