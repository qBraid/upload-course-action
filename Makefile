.PHONY: install install-test test test-unit test-e2e test-coverage coverage-report coverage-html clean sync lock version bump-version bump-patch bump-minor bump-major

install:
	uv pip install -e .

install-test:
	uv pip install -e ".[test]"

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