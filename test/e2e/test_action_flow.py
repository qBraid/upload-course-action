import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from unittest import mock

import pytest

# Mock QbraidSessionV1 for import
try:
    import qbraid_core

    if not hasattr(qbraid_core, "QbraidSessionV1"):
        qbraid_core.QbraidSessionV1 = mock.Mock()
except ImportError:
    qbraid_core = mock.Mock()
    sys.modules["qbraid_core"] = qbraid_core
    if not hasattr(qbraid_core, "QbraidSessionV1"):
        qbraid_core.QbraidSessionV1 = mock.Mock()

import check_images
import create_course
import poll_files_progress
import validate_api_key
import validate_course
import verify_notebooks
from common import Config


@pytest.mark.e2e
class TestActionFlowE2E:

    def setup_method(self):
        self.old_cwd = os.getcwd()
        self.test_dir = tempfile.mkdtemp()
        os.chdir(self.test_dir)

        # Create dummy image
        with open("logo.png", "wb") as f:
            f.write(b"fake_image_data")

    def teardown_method(self):
        os.chdir(self.old_cwd)
        shutil.rmtree(self.test_dir)

    def create_dummy_notebook(self, filename):
        nb_content = {
            "cells": [
                {"cell_type": "markdown", "metadata": {}, "source": ["# Chapter 1"]}
            ],
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
        with open(filename, "w") as f:
            json.dump(nb_content, f)

    def test_full_flow(self):
        # 0. Setup Files
        course_json_content = {
            "courseName": "E2E Test Course",
            "courseDescription": "Description",
            "visibility": "public",
            "imageLink": {"darkLogo": "logo.png", "lightLogo": "logo.png"},
            "tags": ["e2e"],
            "deployedTo": ["qbraid.com"],
            "content": [
                {
                    "chapterName": "Chapter 1",
                    "chapterFileName": "chapter1.ipynb.json",
                    "baseFilePath": "chapter1.ipynb",
                    "chapterNumber": 1,
                    "kernelName": "python3",
                    "kernelId": "python3",
                    "sections": [],
                }
            ],
        }

        with open("course.json", "w") as f:
            json.dump(course_json_content, f)

        self.create_dummy_notebook("chapter1.ipynb")

        # Setup Mock Responses for QbraidSessionV1
        # Patch at the point where it's imported in the modules
        with (
            mock.patch("validate_api_key.QbraidSessionV1") as mock_session_cls_validate,
            mock.patch("create_course.QbraidSessionV1") as mock_session_cls_create,
            mock.patch("poll_files_progress.QbraidSessionV1") as mock_session_cls_poll,
        ):

            # Configure mock instances
            mock_session_instance_validate = mock_session_cls_validate.return_value
            mock_session_instance_create = mock_session_cls_create.return_value
            mock_session_instance_poll = mock_session_cls_poll.return_value

            # Configure GET response for validate_api_key
            mock_verify_resp = mock.Mock()
            mock_verify_resp.status_code = 200
            mock_verify_resp.json.return_value = {"email": "test@test.com"}
            mock_session_instance_validate.get.return_value = mock_verify_resp

            # Configure GET response for poll_files_progress
            mock_poll_resp = mock.Mock()
            mock_poll_resp.status_code = 200
            mock_poll_resp.json.return_value = {
                "status": "processed",
                "qbookUrl": "http://qbook.url",
            }
            mock_session_instance_poll.get.return_value = mock_poll_resp

            # Configure POST response for create_course
            mock_create_resp = mock.Mock()
            mock_create_resp.status_code = 201
            mock_create_resp.json.return_value = {"article": {"customId": "course-123"}}
            mock_session_instance_create.post.return_value = mock_create_resp

            # --- Step 1: Validate API Key ---
            print("\n--- Step 1: Validate API Key ---")
            try:
                validate_api_key.validate_api_key("fake-api-key")
            except SystemExit as e:
                if e.code != 0:
                    pytest.fail(f"API Key validation failed with code {e.code}")

            # --- Step 2: Validate Course ---
            print("\n--- Step 2: Validate Course ---")
            try:
                validate_course.validate_course_json("course.json")
            except SystemExit as e:
                if e.code != 0:
                    pytest.fail(f"Course validation failed with code {e.code}")

            assert os.path.exists("course_data.json")

            # --- Step 3: Verify Notebooks ---
            print("\n--- Step 3: Verify Notebooks ---")
            try:
                verifier = verify_notebooks.NotebookVerifier()
                verifier.run()
            except SystemExit as e:
                if e.code != 0:
                    pytest.fail(f"Notebook verification failed with code {e.code}")

            # --- Step 4: Check Images ---
            print("\n--- Step 4: Check Images ---")
            try:
                validator = check_images.ImageValidator()
                validator.run()
            except SystemExit as e:
                if e.code != 0:
                    pytest.fail(f"Image check failed with code {e.code}")

            # --- Step 5: Create Course ---
            print("\n--- Step 5: Create Course ---")
            try:
                create_course.create_course(
                    "fake-api-key",
                    repo_read_token="token",
                    repo_url="url",
                    commit_sha="sha",
                )
            except SystemExit as e:
                if e.code != 0:
                    pytest.fail(f"Create course failed with code {e.code}")

            # --- Step 6: Poll Progress ---
            print("\n--- Step 6: Poll Progress ---")

            with mock.patch(
                "poll_files_progress.ProgressPoller.fetch_status"
            ) as mock_fetch:
                mock_fetch.return_value = {
                    "status": "processed",
                    "qbookUrl": "http://qbook.url",
                }
                try:
                    poll_files_progress.poll_worker("fake-api-key", "course-123")
                except SystemExit as e:
                    if e.code != 0:
                        pytest.fail(f"Polling failed with code {e.code}")
