from unittest import mock

import pytest
from common import ActionError
from deploy_common import CourseDeployer


@pytest.mark.unit
class TestCourseDeployer:

    def setup_method(self):
        self.deployer = CourseDeployer(
            api_key="key",
            repo_read_token="token",
            repo_url="https://github.com/qBraid/upload-course-api",
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
        assert payload["repoUrl"] == "https://github.com/qBraid/upload-course-api"
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
