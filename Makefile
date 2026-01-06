.PHONY: install test test-unit test-e2e clean

install:
	pip install -r requirements.txt

test: test-unit test-e2e

test-unit:
	pytest test/unit

test-e2e:
	pytest test/e2e

clean:
	rm -rf __pycache__
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf htmlcov
	rm -f course_data.json
