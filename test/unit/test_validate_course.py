import json
from unittest import mock

import pytest
from validate_course import (
    Course,
    CourseValidator,
    _fetch_available_kernels,
    _format_missing_kernel_error,
)


@pytest.mark.unit
class TestCourseValidator:
    @mock.patch("validate_course.Path.exists")
    @mock.patch("validate_course.Path.stat")
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
                    "chapterFileName": "ch1_file.json",
                    "baseFilePath": "ch1.ipynb",
                    "chapterNumber": 1,
                    "kernelName": "qbraid_python",
                    "kernelId": "qbraid_python",
                    "sections": [],
                }
            ],
            "deployedTo": ["qbraid.com"],
        }

        course = Course(**valid_data)
        assert course.courseName == "Test Course"

    @mock.patch("builtins.open", new_callable=mock.mock_open)
    @mock.patch("json.load")
    @mock.patch("validate_course.Path.exists")
    @mock.patch("validate_course.Path.stat")
    def test_validate_valid(self, mock_stat, mock_exists, mock_json_load, mock_file):
        """Test validation with valid structure."""
        valid_data = {
            "courseName": "Test Course",
            "courseDescription": "Desc",
            "visibility": "public",
            "imageLink": {"darkLogo": "d.png", "lightLogo": "l.png"},
            "tags": ["tag"],
            "content": [],
            "deployedTo": ["qbraid.com"],
        }
        mock_json_load.return_value = valid_data
        mock_exists.return_value = True
        mock_stat.return_value.st_size = 100

        validator = CourseValidator("course.json")
        validator.validate()

    @mock.patch("builtins.open", new_callable=mock.mock_open)
    @mock.patch("json.load")
    @mock.patch("validate_course.Path.exists")
    def test_validate_missing_field(self, mock_exists, mock_json_load, mock_file):
        """Test validation with missing required field."""
        mock_exists.return_value = True
        mock_json_load.return_value = {}

        validator = CourseValidator("course.json")
        with pytest.raises(SystemExit) as e:
            validator.validate()
        assert e.value.code == 1

    @mock.patch.dict("os.environ", {}, clear=False)
    @mock.patch("validate_course.Path.exists")
    @mock.patch("validate_course.Path.stat")
    def test_course_model_skips_catalog_lookup_without_explicit_url(
        self, mock_stat, mock_exists
    ):
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
                    "chapterFileName": "ch1_file.json",
                    "baseFilePath": "ch1.ipynb",
                    "chapterNumber": 1,
                    "kernelName": "missing_kernel",
                    "kernelId": "missing_kernel",
                    "sections": [],
                }
            ],
            "deployedTo": ["qbraid.com"],
        }

        course = Course(**valid_data)
        assert course.content[0].kernelName == "missing_kernel"

    @mock.patch.dict(
        "os.environ",
        {"KERNEL_CATALOG_URL": "https://example.test/api/kernelspecs"},
        clear=False,
    )
    @mock.patch("validate_course.urllib.request.urlopen")
    @mock.patch("validate_course.Path.exists")
    @mock.patch("validate_course.Path.stat")
    def test_course_model_validates_kernel_name_when_catalog_url_is_set(
        self, mock_stat, mock_exists, mock_urlopen
    ):
        mock_exists.return_value = True
        mock_stat.return_value.st_size = 100
        mock_response = mock.Mock()
        mock_response.read.return_value = json.dumps(
            {"kernels": {"qbraid_python": {}, "qiskit142_python": {}}}
        ).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response

        valid_data = {
            "courseName": "Test Course",
            "courseDescription": "Desc",
            "visibility": "public",
            "imageLink": {"darkLogo": "d.png", "lightLogo": "l.png"},
            "tags": ["tag"],
            "content": [
                {
                    "chapterName": "Ch1",
                    "chapterFileName": "ch1_file.json",
                    "baseFilePath": "ch1.ipynb",
                    "chapterNumber": 1,
                    "kernelName": "missing_kernel",
                    "kernelId": "missing_kernel",
                    "sections": [],
                }
            ],
            "deployedTo": ["qbraid.com"],
        }

        with pytest.raises(Exception) as exc_info:
            Course(**valid_data)

        assert "Catalog contains 2 kernels" in str(exc_info.value)
        assert "qbraid_python" in str(exc_info.value)
        assert "qiskit142_python" in str(exc_info.value)

    @mock.patch("validate_course.urllib.request.urlopen")
    def test_fetch_available_kernels_returns_none_on_network_errors(self, mock_urlopen):
        mock_urlopen.side_effect = OSError("network down")

        assert _fetch_available_kernels("https://example.test/api/kernelspecs") is None

    def test_format_missing_kernel_error_limits_kernel_sample(self):
        available = {f"kernel_{index}" for index in range(20)}

        message = _format_missing_kernel_error(
            "missing_kernel", "https://example.test/api/kernelspecs", available
        )

        assert "Catalog contains 20 kernels" in message
        assert message.count("kernel_") <= 10
        assert "..." in message

    @mock.patch("builtins.open", new_callable=mock.mock_open)
    @mock.patch("json.load")
    @mock.patch("validate_course.Path.exists")
    def test_validate_invalid_json(self, mock_exists, mock_json_load, mock_file):
        """Test validation with invalid JSON."""
        mock_exists.return_value = True
        mock_json_load.side_effect = json.JSONDecodeError("Invalid", "doc", 0)

        validator = CourseValidator("course.json")
        with pytest.raises(SystemExit) as e:
            validator.validate()
        assert e.value.code == 1
