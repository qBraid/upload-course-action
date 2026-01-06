import os
import sys
import json
import shutil
import tempfile
import pytest
from unittest import mock
import nbformat

# Add src/scripts to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src/scripts')))

import validate_api_key
import validate_course
import verify_notebooks
import check_images
import create_course
import poll_files_progress

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
        nb = nbformat.v4.new_notebook()
        nb.cells.append(nbformat.v4.new_markdown_cell("Test notebook content"))
        with open(filename, 'w', encoding='utf-8') as f:
            nbformat.write(nb, f)

    @mock.patch('requests.get')
    @mock.patch('requests.post')
    def test_full_flow(self, mock_post, mock_get):
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
        
        # Setup Mock Responses
        
        # Validate API Key Mock
        mock_response_verify = mock.Mock()
        mock_response_verify.status_code = 200
        mock_response_verify.json.return_value = {"email": "test@test.com"}
        
        # Poll Status Mock
        mock_response_poll = mock.Mock()
        mock_response_poll.status_code = 200
        mock_response_poll.json.return_value = {"status": "processed", "qbookUrl": "http://qbook.url"}

        # Create Course Mock
        mock_response_create = mock.Mock()
        mock_response_create.status_code = 201
        mock_response_create.json.return_value = {"article": {"customId": "course-123"}}

        # Configure mocks
        def get_side_effect(url, **kwargs):
            if "verify" in url:
                return mock_response_verify
            if "files/status" in url:
                return mock_response_poll
            return mock.Mock(status_code=404)
            
        mock_get.side_effect = get_side_effect
        mock_post.return_value = mock_response_create


        # --- Step 1: Validate API Key ---
        print("\n--- Step 1: Validate API Key ---")
        try:
            with pytest.raises(SystemExit) as e:
                validate_api_key.validate_api_key("fake-api-key")
            assert e.value.code == 0
        except pytest.fail.Exception:
             # validate_api_key calls sys.exit(0) on success
             pass

        # --- Step 2: Validate Course  ---
        print("\n--- Step 2: Validate Course ---")
        # validate_course prints check_file_size output etc.
        # It creates course_data.json
        validate_course.validate_course_json("course.json")
        assert os.path.exists("course_data.json")

        # --- Step 3: Verify Notebooks ---
        print("\n--- Step 3: Verify Notebooks ---")
        # verify_notebooks reads course_data.json
        # Calls sys.exit(1) on failure, otherwise prints success
        verify_notebooks.verify_notebooks()

        # --- Step 4: Check Images ---
        print("\n--- Step 4: Check Images ---")
        # check_images reads course_data.json
        check_images.verify_images()

        # --- Step 5: Create Course ---
        print("\n--- Step 5: Create Course ---")
        # create_course(api_key, article_type, force_duplicate, repo_token, repo_url, commit_sha)
        create_course.create_course(
            "fake-api-key", 
            "course", 
            True, 
            "gh-token", 
            "http://github.com/repo", 
            "sha123"
        )
        
        # --- Step 6: Poll Status ---
        print("\n--- Step 6: Poll Status ---")
        with pytest.raises(SystemExit) as e:
            poll_files_progress.poll_worker("fake-api-key", "course-123")
        assert e.value.code == 0

