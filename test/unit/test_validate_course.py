import os
import sys
import json
import pytest
from unittest import mock
from pathlib import Path

# Add src/scripts to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src/scripts')))

from validate_course import CourseValidator, Course
from common import Config

class TestCourseValidator:
    
    @mock.patch('validate_course.Path.exists')
    @mock.patch('validate_course.Path.stat')
    def test_model_validation_valid(self, mock_stat, mock_exists):
        """Test valid course model creation via Pydantic model directly."""
        mock_exists.return_value = True
        mock_stat.return_value.st_size = 100
        
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
        
        course = Course(**valid_data)
        assert course.courseName == "Test Course"

    @mock.patch('builtins.open', new_callable=mock.mock_open)
    @mock.patch('json.load')
    @mock.patch('validate_course.Path.exists')
    @mock.patch('validate_course.Path.stat')
    def test_validate_valid(self, mock_stat, mock_exists, mock_json_load, mock_file):
        """Test validation with valid structure."""
        valid_data = {
            "courseName": "Test Course",
            "courseDescription": "Desc",
            "visibility": "public",
            "imageLink": {"darkLogo": "d.png", "lightLogo": "l.png"},
            "tags": ["tag"],
            "content": [],
            "deployedTo": ["qbraid.com"]
        }
        mock_json_load.return_value = valid_data
        mock_exists.return_value = True
        mock_stat.return_value.st_size = 100
        
        validator = CourseValidator("course.json")
        validator.validate()

    @mock.patch('builtins.open', new_callable=mock.mock_open)
    @mock.patch('json.load')
    @mock.patch('validate_course.Path.exists')
    def test_validate_missing_field(self, mock_exists, mock_json_load, mock_file):
        """Test validation with missing required field."""
        mock_exists.return_value = True
        mock_json_load.return_value = {} 

        validator = CourseValidator("course.json")
        with pytest.raises(SystemExit) as e:
            validator.validate()
        assert e.value.code == 1

    @mock.patch('builtins.open', new_callable=mock.mock_open)
    @mock.patch('json.load')
    @mock.patch('validate_course.Path.exists')
    def test_validate_invalid_json(self, mock_exists, mock_json_load, mock_file):
        """Test validation with invalid JSON."""
        mock_exists.return_value = True
        mock_json_load.side_effect = json.JSONDecodeError("Invalid", "doc", 0)

        validator = CourseValidator("course.json")
        with pytest.raises(SystemExit) as e:
            validator.validate()
        assert e.value.code == 1

