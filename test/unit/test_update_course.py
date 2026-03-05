import json
from unittest import mock

import pytest
import requests
from common import ActionError, ArticleType
from update_course import CourseUpdater


@pytest.mark.unit
class TestCourseUpdater:

    def setup_method(self):
        self.api_key = "test_key"
        self.course_custom_id = "course-123"
        self.token = "test_token"
        self.url = "test_url"
        self.sha = "test_sha"
        self.updater = CourseUpdater(
            api_key=self.api_key,
            course_custom_id=self.course_custom_id,
            article_type="course",
            force_duplicate_questions=True,
            repo_read_token=self.token,
            repo_url=self.url,
            commit_sha=self.sha,
        )
        # Ensure session is a mock we can assert on
        if not isinstance(self.updater.session, mock.Mock):
            self.updater.session = mock.Mock()
        else:
            self.updater.session.reset_mock()

    def test_run_success(self):
        """Test successful course update."""
        self.updater.load_course_data = mock.Mock(return_value={"valid": "data"})

        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"article": {"customId": "course-123"}}
        self.updater.session.request.return_value = mock_response

        self.updater.run()

        self.updater.session.request.assert_called_once()
        args, kwargs = self.updater.session.request.call_args

        payload = json.loads(kwargs["data"])
        assert payload["repoReadToken"] == self.token
        assert payload["forceDuplicateQuestions"] is True
        assert kwargs["headers"]["X-API-Key"] == self.api_key
        assert args[0] == "PUT"
        assert f"/learn/articles/course/{self.course_custom_id}" in args[1]

    def test_run_success_jsend_response(self):
        """Test successful course update with JSend response format."""
        self.updater.load_course_data = mock.Mock(return_value={"valid": "data"})

        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "success",
            "data": {"article": {"customId": "course-456"}},
        }
        self.updater.session.request.return_value = mock_response

        self.updater.run()

        self.updater.session.request.assert_called_once()
        args, kwargs = self.updater.session.request.call_args

        payload = json.loads(kwargs["data"])
        assert payload["repoReadToken"] == self.token
        assert payload["forceDuplicateQuestions"] is True
        assert kwargs["headers"]["X-API-Key"] == self.api_key
        assert args[0] == "PUT"

    def test_run_failure(self):
        """Test failure scenario."""
        self.updater.load_course_data = mock.Mock(return_value={"course": "data"})

        mock_response = mock.Mock()
        mock_response.status_code = 400
        mock_response.text = "bad request"
        self.updater.session.request.return_value = mock_response

        with pytest.raises(ActionError):
            self.updater.run()

        self.updater.session.request.assert_called_once()
        _, kwargs = self.updater.session.request.call_args

        payload = json.loads(kwargs["data"])
        assert payload["data"] == {"course": "data"}

    def test_missing_args(self):
        """Test initialization with missing arguments."""
        updater = CourseUpdater(
            api_key="key",
            course_custom_id="id",
            repo_read_token=None,
            repo_url=None,
            commit_sha=None,
        )
        with pytest.raises(ActionError):
            updater.run()

    def test_no_data_file(self):
        """Test behavior when data file doesn't exist."""
        self.updater.load_course_data = mock.Mock(
            side_effect=ActionError("course_data.json not found")
        )
        with pytest.raises(ActionError):
            self.updater.run()

    def test_api_fail_network(self):
        """Test network failure."""
        self.updater.load_course_data = mock.Mock(return_value={})

        self.updater.session.request.reset_mock()
        self.updater.session.request.side_effect = requests.RequestException(
            "Network Error"
        )

        with pytest.raises(ActionError):
            self.updater.run()

    def test_invalid_article_type(self):
        """Test invalid article type defaults to course."""
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"article": {"customId": "course-123"}}

        updater = CourseUpdater(
            api_key="key",
            course_custom_id="id",
            article_type="invalid_type",
            repo_read_token="t",
            repo_url="u",
            commit_sha="s",
        )
        if not isinstance(updater.session, mock.Mock):
            updater.session = mock.Mock()
        else:
            updater.session.reset_mock()

        updater.load_course_data = mock.Mock(return_value={})
        updater.session.request.return_value = mock_response
        updater.session.request.side_effect = None

        updater.run()

        assert updater._article_type_enum == ArticleType.COURSE
        assert updater.article_type == "course"
        args, kwargs = updater.session.request.call_args
        assert args[0] == "PUT"
        assert "/learn/articles/course/" in args[1]

    def test_run_with_certificate_settings(self):
        """Test course update with certificate settings."""
        cert_settings = {"enabled": True, "criteria": {"type": "completion", "value": 80}}
        updater = CourseUpdater(
            api_key=self.api_key,
            course_custom_id=self.course_custom_id,
            article_type="course",
            force_duplicate_questions=True,
            repo_read_token=self.token,
            repo_url=self.url,
            commit_sha=self.sha,
            certificate_settings=cert_settings,
        )
        if not isinstance(updater.session, mock.Mock):
            updater.session = mock.Mock()
        updater.load_course_data = mock.Mock(return_value={"courseName": "Test"})

        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"article": {"customId": "course-123"}}
        updater.session.request.return_value = mock_response

        updater.run()

        updater.session.request.assert_called_once()
        _, kwargs = updater.session.request.call_args
        payload = json.loads(kwargs["data"])
        assert payload["data"]["certificateSettings"] == cert_settings

    def test_init_with_certificate_settings(self):
        """Test CourseUpdater initialization with certificate settings."""
        cert_settings = {"enabled": True, "criteria": {"type": "points", "value": 500}}
        updater = CourseUpdater(
            api_key="key",
            course_custom_id="id",
            article_type="course",
            force_duplicate_questions=False,
            repo_read_token="token",
            repo_url="url",
            commit_sha="sha",
            certificate_settings=cert_settings,
        )
        assert updater.certificate_settings == cert_settings
        assert updater.course_custom_id == "id"

    def test_certificate_settings_ignored_for_blog(self):
        """Test certificate settings are ignored for blog article type."""
        cert_settings = {"enabled": True, "criteria": {"type": "completion"}}
        updater = CourseUpdater(
            api_key=self.api_key,
            course_custom_id="blog-123",
            article_type="blog",
            force_duplicate_questions=True,
            repo_read_token=self.token,
            repo_url=self.url,
            commit_sha=self.sha,
            certificate_settings=cert_settings,
        )
        if not isinstance(updater.session, mock.Mock):
            updater.session = mock.Mock()
        updater.load_course_data = mock.Mock(return_value={"blogName": "Test Blog"})

        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"article": {"customId": "blog-123"}}
        updater.session.request.return_value = mock_response

        with mock.patch("deploy_common.logger"):
            updater.run()

        _, kwargs = updater.session.request.call_args
        payload = json.loads(kwargs["data"])
        assert "certificateSettings" not in payload["data"]

    def test_update_uses_put_method(self):
        """Test that update uses PUT HTTP method."""
        self.updater.load_course_data = mock.Mock(return_value={})

        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"article": {"customId": "course-123"}}
        self.updater.session.request.return_value = mock_response

        self.updater.run()

        args, _ = self.updater.session.request.call_args
        assert args[0] == "PUT"

    def test_update_url_includes_course_id(self):
        """Test that update URL includes the course custom ID."""
        self.updater.load_course_data = mock.Mock(return_value={})

        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"article": {"customId": "course-123"}}
        self.updater.session.request.return_value = mock_response

        self.updater.run()

        args, _ = self.updater.session.request.call_args
        assert self.course_custom_id in args[1]
