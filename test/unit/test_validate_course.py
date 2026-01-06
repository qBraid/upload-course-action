import os
import sys
import json
import pytest
from unittest import mock

# Add src/scripts to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src/scripts')))

import validate_course

class TestValidateCourse:

    def test_check_file_size_valid(self):
        """Test file size check with valid size."""
        with mock.patch('os.path.exists', return_value=True), \
             mock.patch('os.path.getsize', return_value=1024):
            # Should not raise exception
            validate_course.check_file_size("dummy.file", "Context")

    def test_check_file_size_exceeds(self):
        """Test file size check with invalid size."""
        limit_mb = 5
        limit_bytes = limit_mb * 1024 * 1024 + 1
        with mock.patch('os.path.exists', return_value=True), \
             mock.patch('os.path.getsize', return_value=limit_bytes):
            with pytest.raises(SystemExit) as e:
                validate_course.check_file_size("dummy.file", "Context")
            assert e.value.code == 1


    @mock.patch('builtins.print')
    def test_validate_course_json_file_not_found(self, mock_print):
        """Test validate_course_json when file not found."""
        with mock.patch('os.path.exists', return_value=False):
            with pytest.raises(SystemExit) as e:
                validate_course.validate_course_json("course.json")
            assert e.value.code == 1

    @mock.patch('builtins.open', new_callable=mock.mock_open)
    @mock.patch('json.load')
    @mock.patch('os.path.exists', return_value=True)
    def test_validate_course_json_missing_field(self, mock_exists, mock_json_load, mock_file, capsys):
        """Test validate_course_json with missing required field."""
        mock_json_load.return_value = {} # Empty dict
        
        with pytest.raises(SystemExit) as e:
            validate_course.validate_course_json("course.json")
        assert e.value.code == 1
        captured = capsys.readouterr()
        assert "Missing required field" in captured.out

    @mock.patch('builtins.open', new_callable=mock.mock_open)
    @mock.patch('json.load')
    @mock.patch('os.path.exists', return_value=True)
    def test_validate_course_json_valid(self, mock_exists, mock_json_load, mock_file):
        """Test validate_course_json with valid structure."""
        valid_data = {
            "courseName": "Test Course",
            "courseDescription": "Desc",
            "visibility": "public",
            "imageLink": {"darkLogo": "d.png", "lightLogo": "l.png"},
            "tags": ["tag"],
            "content": [
                {
                    "chapterName": "Ch1",
                    "baseFilePath": "ch1.ipynb",
                    "chapterNumber": 1,
                    "kernelName": "python3",
                    "kernelId": "python-3",
                    "sections": []
                }
            ],
            "deployedTo": ["qbraid.com"]
        }
        mock_json_load.return_value = valid_data
        
        # Mock check_file_size to pass
        with mock.patch('validate_course.check_file_size') as mock_check_size:
             validate_course.validate_course_json("course.json")
             
             # Verify that course_data.json is written
             assert mock_file.call_count >= 2  # Read course.json and write course_data.json
             
             # Verify that course_data.json is opened in write mode for output
             mock_file.assert_any_call("course_data.json", "w")
    @mock.patch('builtins.open', new_callable=mock.mock_open)
    @mock.patch('json.load')
    @mock.patch('os.path.exists', return_value=True)
    def test_validate_course_json_invalid_domain(self, mock_exists, mock_json_load, mock_file, capsys):
        """Test validate_course_json with invalid domain."""
        invalid_data = {
            "courseName": "Test Course",
            "courseDescription": "Desc",
            "visibility": "public",
            "imageLink": {"darkLogo": "d.png", "lightLogo": "l.png"},
            "tags": [],
            "content": [],
            "deployedTo": ["invalid.com"]
        }
        mock_json_load.return_value = invalid_data
        
        with pytest.raises(SystemExit) as e:
            validate_course.validate_course_json("course.json")
        assert e.value.code == 1
        captured = capsys.readouterr()
        assert "Invalid domain" in captured.out

    @mock.patch('builtins.open', new_callable=mock.mock_open)
    @mock.patch('json.load')
    @mock.patch('os.path.exists', return_value=True)
    def test_validate_course_json_github_output(self, mock_exists, mock_json_load, mock_file):
        """Test valid course json writes to Github Output."""
        valid_data = {
           "courseName": "Test Course",
           "courseDescription": "Desc",
           "visibility": "public",
           "imageLink": {"darkLogo": "d.png", "lightLogo": "l.png"},
           "tags": [],
           "content": [],
           "deployedTo": ["qbraid.com"]
        }
        mock_json_load.return_value = valid_data
        
        with mock.patch.dict(os.environ, {'GITHUB_OUTPUT': 'output.txt'}):
             validate_course.validate_course_json("course.json")
             # Verify writing to output.txt
             mock_file.assert_any_call('output.txt', 'a')
             handle = mock_file()
             handle.write.assert_any_call("course_name=Test Course\n")

