"""Shared pytest fixtures and configuration for all tests."""

import os
import sys
import tempfile
from pathlib import Path
from unittest import mock

import pytest

# Add src/scripts to path for all tests
TEST_ROOT = Path(__file__).parent
PROJECT_ROOT = TEST_ROOT.parent
SCRIPTS_PATH = PROJECT_ROOT / "src" / "scripts"

if str(SCRIPTS_PATH) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_PATH))

# Mock QbraidSessionV1 globally for consistent test behavior
try:
    import qbraid_core

    if not hasattr(qbraid_core, "QbraidSessionV1"):
        qbraid_core.QbraidSessionV1 = mock.Mock()
except ImportError:
    qbraid_core = mock.Mock()
    sys.modules["qbraid_core"] = qbraid_core
    if not hasattr(qbraid_core, "QbraidSessionV1"):
        qbraid_core.QbraidSessionV1 = mock.Mock()


@pytest.fixture
def mock_qbraid_session():
    """Fixture providing a mocked QbraidSessionV1 instance."""
    with mock.patch("qbraid_core.QbraidSessionV1") as mock_session_cls:
        mock_instance = mock_session_cls.return_value
        yield mock_instance


@pytest.fixture
def temp_dir():
    """Fixture providing a temporary directory for test files."""
    old_cwd = os.getcwd()
    test_dir = tempfile.mkdtemp()
    os.chdir(test_dir)
    yield test_dir
    os.chdir(old_cwd)
    import shutil

    shutil.rmtree(test_dir)


@pytest.fixture
def mock_api_response_success():
    """Fixture providing a successful API response mock."""
    mock_resp = mock.Mock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"email": "test@example.com"}
    return mock_resp


@pytest.fixture
def mock_api_response_created():
    """Fixture providing a 201 Created API response mock."""
    mock_resp = mock.Mock()
    mock_resp.status_code = 201
    mock_resp.json.return_value = {"article": {"customId": "course-123"}}
    return mock_resp


@pytest.fixture
def mock_api_response_error():
    """Fixture providing an error API response mock."""
    mock_resp = mock.Mock()
    mock_resp.status_code = 401
    mock_resp.json.return_value = {"error": "Unauthorized"}
    return mock_resp


@pytest.fixture
def sample_course_json():
    """Fixture providing sample course.json data."""
    return {
        "courseName": "Test Course",
        "courseDescription": "Test Description",
        "visibility": "public",
        "imageLink": {"darkLogo": "logo.png", "lightLogo": "logo.png"},
        "tags": ["test"],
        "deployedTo": ["qbraid.com"],
        "content": [
            {
                "chapterName": "Chapter 1",
                "chapterFileName": "chapter1.ipynb.json",
                "baseFilePath": "chapter1.ipynb",
                "chapterNumber": 1,
                "kernelName": "qbraid_python",
                "kernelId": "qbraid_python",
                "sections": [],
            }
        ],
    }


@pytest.fixture
def sample_notebook_content():
    """Fixture providing sample notebook content."""
    return {
        "cells": [{"cell_type": "markdown", "metadata": {}, "source": ["# Chapter 1"]}],
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3.8.5"},
        },
        "nbformat": 4,
        "nbformat_minor": 4,
    }


@pytest.fixture
def github_output(tmp_path, monkeypatch):
    """Fixture simulating GitHub Actions $GITHUB_OUTPUT file."""
    output_file = tmp_path / "github_output.txt"
    monkeypatch.setenv("GITHUB_OUTPUT", str(output_file))
    yield output_file
    if output_file.exists():
        output_file.unlink()


@pytest.fixture
def github_env(tmp_path, monkeypatch):
    """Fixture simulating GitHub Actions environment variables."""
    env_vars = {
        "GITHUB_WORKSPACE": str(tmp_path),
        "GITHUB_ACTION_PATH": str(tmp_path),
        "GITHUB_SHA": "abc123def456",
        "GITHUB_REPOSITORY": "test-org/test-repo",
        "GITHUB_SERVER_URL": "https://github.com",
    }
    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)
    return env_vars


@pytest.fixture
def runner_filesystem(tmp_path, github_env):
    """Fixture simulating GitHub Actions runner filesystem structure."""
    workspace = Path(github_env["GITHUB_WORKSPACE"])
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace


@pytest.fixture
def nasty_inputs():
    """Fixture providing 'nasty' input values that commonly break YAML/shell."""
    return {
        "path_with_spaces": "path with spaces/file.json",
        "path_with_newlines": "path\nwith\nnewlines.json",
        "path_with_tabs": "path\twith\ttabs.json",
        "weird_branch_name": "feature/branch-with-123_and-special-chars",
        "unicode_path": "café/测试/тест.json",
        "empty_string": "",
        "only_spaces": "   ",
        "path_with_quotes": 'path"with"quotes.json',
        "path_with_dollar": "path$with$vars.json",
        "very_long_path": "a" * 200 + ".json",
    }
