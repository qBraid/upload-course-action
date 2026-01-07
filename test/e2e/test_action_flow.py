import os
import sys
import json
import shutil
import tempfile
import pytest
from unittest import mock
from pathlib import Path

# Add src/scripts to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src/scripts')))

import validate_api_key
import validate_course
import create_course
import poll_files_progress
import check_images
import verify_notebooks
from common import Config

class TestActionFlowE2E:

    @pytest.fixture(autouse=True)
    def setup_teardown(self):
        # Create a temporary directory
        self.test_dir = tempfile.mkdtemp()
        self.old_cwd = os.getcwd()
        os.chdir(self.test_dir)
        
        yield
        
        # Cleanup
        os.chdir(self.old_cwd)
        shutil.rmtree(self.test_dir)

    def create_dummy_notebook(self, filename):
        nb_content = {
          "cells": [
            {
              "cell_type": "markdown",
              "metadata": {},
              "source": [
                "# Chapter 1"
              ]
            }
          ],
          "metadata": {
            "kernelspec": {
              "display_name": "Python 3",
              "language": "python",
              "name": "python3"
            },
            "language_info": {
              "codemirror_mode": {
                "name": "ipython",
                "version": 3
              },
              "file_extension": ".py",
              "mimetype": "text/x-python",
              "name": "python",
              "nbconvert_exporter": "python",
              "pygments_lexer": "ipython3",
              "version": "3.8.5"
            }
          },
          "nbformat": 4,
          "nbformat_minor": 4
        }
        with open(filename, 'w') as f:
            json.dump(nb_content, f)

    @mock.patch('validate_api_key.QbraidSession')
    @mock.patch('requests.get')
    @mock.patch('requests.post')
    def test_full_flow(self, mock_post, mock_get, mock_qbraid_session):
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
                    "baseFilePath": "chapter1.ipynb",
                    "chapterNumber": 1,
                    "kernelName": "python3",
                    "kernelId": "python3",
                    "sections": []
                }
            ]
        }
    
        with open("course.json", "w") as f:
            json.dump(course_json_content, f)
    
        self.create_dummy_notebook("chapter1.ipynb")
    
        # Setup Mock Responses for QbraidSession (API Key)
        mock_session_instance = mock_qbraid_session.return_value
        mock_verify_resp = mock.Mock()
        mock_verify_resp.status_code = 200
        mock_verify_resp.json.return_value = {"email": "test@test.com"}
        mock_session_instance.get.return_value = mock_verify_resp

        # Setup Mock Responses for requests (Poll & Create)
        mock_poll_resp = mock.Mock()
        mock_poll_resp.status_code = 200
        mock_poll_resp.json.return_value = {"status": "processed", "qbookUrl": "http://qbook.url"}
        
        mock_create_resp = mock.Mock()
        mock_create_resp.status_code = 201
        mock_create_resp.json.return_value = {"article": {"customId": "course-123"}}
        
        mock_get.return_value = mock_poll_resp
        mock_post.return_value = mock_create_resp
    
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
            verify_notebooks.verify_notebooks()
        except SystemExit as e:
            if e.code != 0:
                pytest.fail(f"Notebook verification failed with code {e.code}")

        # --- Step 4: Check Images ---
        print("\n--- Step 4: Check Images ---")
        try:
            check_images.verify_images()
        except SystemExit as e:
            if e.code != 0:
                pytest.fail(f"Image check failed with code {e.code}")

        # --- Step 5: Create Course ---
        print("\n--- Step 5: Create Course ---")
        try:
            create_course.create_course("fake-api-key", repo_read_token="token", repo_url="url", commit_sha="sha")
        except SystemExit as e:
             if e.code != 0:
                pytest.fail(f"Create course failed with code {e.code}")

        # --- Step 6: Poll Progress ---
        print("\n--- Step 6: Poll Progress ---")
        # To test polling success, we mock check_status to return processed immediately or simulated
        # But we mocked requests.get above to return 'processed'
        try:
            poll_files_progress.poll_worker("fake-api-key", "course-123")
        except SystemExit as e:
             if e.code != 0:
                pytest.fail(f"Polling failed with code {e.code}")


