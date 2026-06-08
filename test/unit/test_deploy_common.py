from unittest import mock

import pytest
from common import ActionError, ValidationError
from deploy_common import (
    CourseDeployer,
    build_certificate_settings,
    validate_certificate_criteria_type,
    validate_certificate_criteria_value,
)


@pytest.mark.unit
class TestValidateCertificateCriteriaType:
    """Tests for validate_certificate_criteria_type function."""

    def test_valid_completion_type(self):
        """Test 'completion' is a valid criteria type."""
        assert validate_certificate_criteria_type("completion") == "completion"

    def test_valid_points_type(self):
        """Test 'points' is a valid criteria type."""
        assert validate_certificate_criteria_type("points") == "points"

    def test_type_with_whitespace(self):
        """Test criteria type with leading/trailing whitespace."""
        assert validate_certificate_criteria_type("  completion  ") == "completion"
        assert validate_certificate_criteria_type("\tpoints\n") == "points"

    def test_type_case_insensitive(self):
        """Test criteria type is case insensitive."""
        assert validate_certificate_criteria_type("COMPLETION") == "completion"
        assert validate_certificate_criteria_type("Points") == "points"
        assert validate_certificate_criteria_type("POINTS") == "points"

    def test_empty_returns_default(self):
        """Test empty string returns default 'completion'."""
        assert validate_certificate_criteria_type("") == "completion"
        assert validate_certificate_criteria_type("   ") == "completion"

    def test_none_returns_default(self):
        """Test None returns default 'completion'."""
        assert validate_certificate_criteria_type(None) == "completion"

    def test_invalid_type_raises_error(self):
        """Test invalid criteria type raises ValidationError."""
        with pytest.raises(ValidationError, match="must be 'completion' or 'points'"):
            validate_certificate_criteria_type("invalid")

        with pytest.raises(ValidationError, match="must be 'completion' or 'points'"):
            validate_certificate_criteria_type("percentage")


@pytest.mark.unit
class TestValidateCertificateCriteriaValue:
    """Tests for validate_certificate_criteria_value function."""

    def test_valid_integer_value(self):
        """Test valid integer values."""
        assert validate_certificate_criteria_value("100") == 100.0
        assert validate_certificate_criteria_value("50") == 50.0
        assert validate_certificate_criteria_value("0") == 0.0

    def test_valid_float_value(self):
        """Test valid float values."""
        assert validate_certificate_criteria_value("75.5") == 75.5
        assert validate_certificate_criteria_value("99.99") == 99.99

    def test_value_with_whitespace(self):
        """Test value with leading/trailing whitespace."""
        assert validate_certificate_criteria_value("  100  ") == 100.0

    def test_empty_returns_none(self):
        """Test empty string returns None."""
        assert validate_certificate_criteria_value("") is None
        assert validate_certificate_criteria_value("   ") is None

    def test_none_returns_none(self):
        """Test None returns None."""
        assert validate_certificate_criteria_value(None) is None

    def test_negative_value_raises_error(self):
        """Test negative value raises ValidationError."""
        with pytest.raises(ValidationError, match="must be non-negative"):
            validate_certificate_criteria_value("-1")

        with pytest.raises(ValidationError, match="must be non-negative"):
            validate_certificate_criteria_value("-50.5")

    def test_invalid_number_raises_error(self):
        """Test non-numeric value raises ValidationError."""
        with pytest.raises(ValidationError, match="must be a number"):
            validate_certificate_criteria_value("abc")

        with pytest.raises(ValidationError, match="must be a number"):
            validate_certificate_criteria_value("10%")


@pytest.mark.unit
class TestBuildCertificateSettings:
    """Tests for build_certificate_settings function."""

    def test_disabled_certificate(self):
        """Test building settings when certificates are disabled includes default criteria."""
        settings = build_certificate_settings(False, "completion", None)
        # When disabled, default criteria is always included for consistent payload format
        assert settings == {
            "enabled": False,
            "criteria": {"type": "completion", "value": 100.0},
        }

    def test_disabled_certificate_ignores_provided_criteria(self):
        """Test that when disabled, default criteria is used regardless of provided values."""
        settings = build_certificate_settings(False, "points", 500.0)
        # Even with different criteria provided, disabled uses default
        assert settings == {
            "enabled": False,
            "criteria": {"type": "completion", "value": 100.0},
        }

    def test_enabled_completion_without_value(self):
        """Test enabled completion type without specific value."""
        settings = build_certificate_settings(True, "completion", None)
        assert settings == {"enabled": True, "criteria": {"type": "completion"}}

    def test_enabled_completion_with_value(self):
        """Test enabled completion type with specific value."""
        settings = build_certificate_settings(True, "completion", 80.0)
        assert settings == {
            "enabled": True,
            "criteria": {"type": "completion", "value": 80.0},
        }

    def test_enabled_points_without_value(self):
        """Test enabled points type without specific value."""
        settings = build_certificate_settings(True, "points", None)
        assert settings == {"enabled": True, "criteria": {"type": "points"}}

    def test_enabled_points_with_value(self):
        """Test enabled points type with specific value."""
        settings = build_certificate_settings(True, "points", 500.0)
        assert settings == {
            "enabled": True,
            "criteria": {"type": "points", "value": 500.0},
        }

    def test_completion_value_exceeds_100_raises_error(self):
        """Test that completion value over 100 raises ValidationError."""
        with pytest.raises(ValidationError, match="cannot exceed 100"):
            build_certificate_settings(True, "completion", 101.0)

        with pytest.raises(ValidationError, match="cannot exceed 100"):
            build_certificate_settings(True, "completion", 150.0)

    def test_completion_value_at_boundary(self):
        """Test completion value at boundary (100) is valid."""
        settings = build_certificate_settings(True, "completion", 100.0)
        assert settings["criteria"]["value"] == 100.0

    def test_points_value_over_100_is_valid(self):
        """Test points value over 100 is valid (unlike completion)."""
        settings = build_certificate_settings(True, "points", 500.0)
        assert settings["criteria"]["value"] == 500.0


@pytest.mark.unit
class TestCourseDeployer:

    def setup_method(self):
        self.deployer = CourseDeployer(
            api_key="key",
            repo_read_token="token",
            repo_url="https://github.com/qBraid/upload-course-action",
            commit_sha="abc1234",
            force_duplicate_questions=False,
        )

    def test_get_common_payload_includes_integer_run_attempt(self, monkeypatch):
        self.deployer.load_course_data = mock.Mock(return_value={"courseName": "Demo"})
        monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "3")

        payload = self.deployer.get_common_payload()

        assert payload["data"] == {"courseName": "Demo"}
        assert payload["forceDuplicateQuestions"] is False
        assert payload["repoReadToken"] == "token"
        assert payload["repoUrl"] == "https://github.com/qBraid/upload-course-action"
        assert payload["commitSha"] == "abc1234"
        assert payload["runAttempt"] == 3

    def test_get_common_payload_skips_invalid_run_attempt(self, monkeypatch):
        self.deployer.load_course_data = mock.Mock(return_value={"courseName": "Demo"})
        monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "invalid")

        payload = self.deployer.get_common_payload()

        assert "runAttempt" not in payload

    @mock.patch("deploy_common.write_github_output")
    def test_handle_response_supports_legacy_payload(self, mock_output):
        response = mock.Mock()
        response.status_code = 201
        response.json.return_value = {"article": {"customId": "course-123"}}

        self.deployer.handle_response(response, "ok")

        mock_output.assert_any_call("course_name", "course-123")
        mock_output.assert_any_call("course_custom_id", "course-123")

    @mock.patch("deploy_common.write_github_output")
    def test_handle_response_supports_jsend_payload(self, mock_output):
        response = mock.Mock()
        response.status_code = 200
        response.json.return_value = {
            "status": "success",
            "data": {"article": {"customId": "course-456"}},
        }

        self.deployer.handle_response(response, "ok")

        mock_output.assert_any_call("course_name", "course-456")
        mock_output.assert_any_call("course_custom_id", "course-456")

    def test_handle_response_raises_on_failure_status(self):
        response = mock.Mock()
        response.status_code = 400
        response.text = "bad request"

        with pytest.raises(ActionError, match="Operation failed"):
            self.deployer.handle_response(response, "ok")

    def test_deployer_init_with_certificate_settings(self):
        """Test CourseDeployer initialization with certificate settings."""
        cert_settings = {
            "enabled": True,
            "criteria": {"type": "completion", "value": 80},
        }
        deployer = CourseDeployer(
            api_key="key",
            repo_read_token="token",
            repo_url="https://github.com/qBraid/upload-course-action",
            commit_sha="abc1234",
            article_type="course",
            force_duplicate_questions=True,
            certificate_settings=cert_settings,
        )
        assert deployer.certificate_settings == cert_settings
        assert deployer.article_type == "course"

    def test_get_common_payload_includes_certificate_settings_for_course(self):
        """Test get_common_payload includes certificate settings for course type."""
        cert_settings = {
            "enabled": True,
            "criteria": {"type": "completion", "value": 80},
        }
        deployer = CourseDeployer(
            api_key="key",
            repo_read_token="token",
            repo_url="https://github.com/qBraid/upload-course-action",
            commit_sha="abc1234",
            article_type="course",
            certificate_settings=cert_settings,
        )
        deployer.load_course_data = mock.Mock(return_value={"courseName": "Demo"})

        payload = deployer.get_common_payload()

        assert payload["data"]["certificateSettings"] == cert_settings

    def test_get_common_payload_excludes_certificate_settings_for_blog(self):
        """Test get_common_payload excludes certificate settings for blog type."""
        cert_settings = {
            "enabled": True,
            "criteria": {"type": "completion", "value": 80},
        }
        deployer = CourseDeployer(
            api_key="key",
            repo_read_token="token",
            repo_url="https://github.com/qBraid/upload-course-action",
            commit_sha="abc1234",
            article_type="blog",
            certificate_settings=cert_settings,
        )
        deployer.load_course_data = mock.Mock(return_value={"courseName": "Demo"})

        with mock.patch("deploy_common.logger") as mock_logger:
            payload = deployer.get_common_payload()

            assert "certificateSettings" not in payload["data"]
            mock_logger.warning.assert_called_once()
            assert "Certificate settings ignored" in mock_logger.warning.call_args[0][0]

    def test_get_common_payload_silently_ignores_disabled_certificate_settings_for_blog(
        self,
    ):
        """Test disabled certificate settings do not warn for blog type."""
        cert_settings = {
            "enabled": False,
            "criteria": {"type": "completion", "value": 100.0},
        }
        deployer = CourseDeployer(
            api_key="key",
            repo_read_token="token",
            repo_url="https://github.com/qBraid/upload-course-action",
            commit_sha="abc1234",
            article_type="blog",
            certificate_settings=cert_settings,
        )
        deployer.load_course_data = mock.Mock(return_value={"courseName": "Demo"})

        with mock.patch("deploy_common.logger") as mock_logger:
            payload = deployer.get_common_payload()

            assert "certificateSettings" not in payload["data"]
            mock_logger.warning.assert_not_called()

    def test_get_common_payload_no_certificate_settings(self):
        """Test get_common_payload without certificate settings."""
        deployer = CourseDeployer(
            api_key="key",
            repo_read_token="token",
            repo_url="https://github.com/qBraid/upload-course-action",
            commit_sha="abc1234",
            article_type="course",
            certificate_settings=None,
        )
        deployer.load_course_data = mock.Mock(return_value={"courseName": "Demo"})

        payload = deployer.get_common_payload()

        assert "certificateSettings" not in payload["data"]
