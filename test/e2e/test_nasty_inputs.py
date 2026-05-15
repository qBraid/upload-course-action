"""E2E tests for 'nasty' inputs that commonly break YAML/shell handling."""

import json
import os
from pathlib import Path
from unittest import mock

import pytest
import validate_course
import verify_notebooks
from common import Config


@pytest.mark.e2e
class TestNastyInputs:
    """Test edge cases and problematic inputs."""

    def setup_method(self):
        self.old_cwd = os.getcwd()
        self.test_dir = Path(__file__).parent / "temp_nasty"
        self.test_dir.mkdir(exist_ok=True)
        os.chdir(self.test_dir)

    def teardown_method(self):
        os.chdir(self.old_cwd)
        import shutil

        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    @mock.patch("validate_course.Path.exists")
    @mock.patch("validate_course.Path.stat")
    def test_path_with_spaces(self, mock_stat, mock_exists, sample_course_json):
        """Test handling of paths with spaces."""
        # Mock file existence for any notebook files referenced
        mock_exists.return_value = True
        mock_stat.return_value.st_size = 100

        course_file = self.test_dir / "course with spaces.json"
        with open(course_file, "w") as f:
            json.dump(sample_course_json, f)

        validator = validate_course.CourseValidator(str(course_file))
        # Should not crash on spaces
        try:
            validator.validate()
        except Exception as e:
            pytest.fail(f"Failed to handle path with spaces: {e}")

    @mock.patch("validate_course.Path.exists")
    @mock.patch("validate_course.Path.stat")
    def test_path_with_newlines(self, mock_stat, mock_exists, sample_course_json):
        """Test handling of paths with newlines (should fail gracefully)."""
        # Mock file existence for any notebook files referenced
        mock_exists.return_value = True
        mock_stat.return_value.st_size = 100

        # Create file with newline in name (unlikely but possible)
        course_file = self.test_dir / "course\nwith\nnewlines.json"
        with open(course_file, "w") as f:
            json.dump(sample_course_json, f)

        # This should either work or fail gracefully
        validator = validate_course.CourseValidator(str(course_file))
        try:
            validator.validate()
        except (ValueError, OSError, SystemExit):
            pass  # Expected to fail on newlines or validation
        except Exception as e:
            pytest.fail(f"Unexpected error handling newlines: {e}")

    def test_empty_course_json(self):
        """Test handling of empty course.json."""
        course_file = self.test_dir / "empty.json"
        course_file.write_text("{}")

        validator = validate_course.CourseValidator(str(course_file))
        with pytest.raises(SystemExit):
            validator.validate()

    def test_malformed_json(self):
        """Test handling of malformed JSON."""
        course_file = self.test_dir / "malformed.json"
        course_file.write_text("{ invalid json }")

        validator = validate_course.CourseValidator(str(course_file))
        with pytest.raises(SystemExit):
            validator.validate()

    @mock.patch("validate_course.Path.exists")
    @mock.patch("validate_course.Path.stat")
    def test_unicode_in_path(self, mock_stat, mock_exists, sample_course_json):
        """Test handling of unicode characters in paths."""
        # Mock file existence for any notebook files referenced
        mock_exists.return_value = True
        mock_stat.return_value.st_size = 100

        course_file = self.test_dir / "café_测试_тест.json"
        with open(course_file, "w", encoding="utf-8") as f:
            json.dump(sample_course_json, f, ensure_ascii=False)

        validator = validate_course.CourseValidator(str(course_file))
        try:
            validator.validate()
        except Exception as e:
            pytest.fail(f"Failed to handle unicode path: {e}")

    @mock.patch("validate_course.Path.exists")
    @mock.patch("validate_course.Path.stat")
    def test_very_long_path(self, mock_stat, mock_exists, sample_course_json):
        """Test handling of very long file paths."""
        # Mock file existence for any notebook files referenced
        mock_exists.return_value = True
        mock_stat.return_value.st_size = 100

        long_name = "a" * 200 + ".json"
        course_file = self.test_dir / long_name
        with open(course_file, "w") as f:
            json.dump(sample_course_json, f)

        validator = validate_course.CourseValidator(str(course_file))
        try:
            validator.validate()
        except (OSError, ValueError, SystemExit):
            pass  # May fail on some systems with path length limits or validation
        except Exception as e:
            pytest.fail(f"Unexpected error with long path: {e}")

    def test_missing_notebook_referenced_in_course(self, sample_course_json):
        """Test handling when course.json references non-existent notebook."""
        sample_course_json["content"] = [
            {
                "chapterName": "Missing Chapter",
                "chapterFileName": "missing.ipynb.json",
                "baseFilePath": "nonexistent.ipynb",
                "chapterNumber": 1,
                "kernelName": "qbraid_python",
                "kernelId": "qbraid_python",
                "sections": [],
            }
        ]

        course_file = self.test_dir / "course.json"
        with open(course_file, "w") as f:
            json.dump(sample_course_json, f)

        # Create course_data.json that verify_notebooks expects
        course_data_file = Path("course_data.json")
        with open(course_data_file, "w") as f:
            json.dump(sample_course_json, f)

        verifier = verify_notebooks.NotebookVerifier()
        with pytest.raises(SystemExit) as exc_info:
            verifier.run()
        assert exc_info.value.code == 1

    def test_course_json_with_special_chars_in_values(self):
        """Test handling of special characters in JSON values."""
        course_data = {
            "courseName": "Course\nwith\nnewlines\tand\ttabs",
            "courseDescription": "Description with 'quotes' and \"double quotes\"",
            "visibility": "public",
            "imageLink": {"darkLogo": "logo.png", "lightLogo": "logo.png"},
            "tags": ["tag with spaces", "tag-with-dashes"],
            "deployedTo": ["qbraid.com"],
            "content": [],
        }

        course_file = self.test_dir / "special_chars.json"
        with open(course_file, "w") as f:
            json.dump(course_data, f)

        validator = validate_course.CourseValidator(str(course_file))
        # Should handle special chars in values
        try:
            validator.validate()
        except Exception as e:
            pytest.fail(f"Failed to handle special chars in values: {e}")

    def test_relative_path_traversal_attempt(self, sample_course_json):
        """Test handling of path traversal attempts."""
        course_data = sample_course_json.copy()
        course_data["content"] = [
            {
                "chapterName": "Traversal",
                "chapterFileName": "traversal.ipynb.json",
                "baseFilePath": "../../../etc/passwd",
                "chapterNumber": 1,
                "kernelName": "qbraid_python",
                "kernelId": "qbraid_python",
                "sections": [],
            }
        ]

        course_file = self.test_dir / "course.json"
        with open(course_file, "w") as f:
            json.dump(course_data, f)

        # Create course_data.json
        course_data_file = Path("course_data.json")
        with open(course_data_file, "w") as f:
            json.dump(course_data, f)

        verifier = verify_notebooks.NotebookVerifier()
        # Should fail when trying to access traversal path
        with pytest.raises(SystemExit) as exc_info:
            verifier.run()
        assert exc_info.value.code == 1
