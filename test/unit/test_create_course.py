import json
from unittest import mock

import pytest
import requests
from common import ActionError, ArticleType
from create_course import CourseCreator


@pytest.mark.unit
class TestCourseCreator:

    def setup_method(self):
        self.api_key = "test_key"
        self.token = "test_token"
        self.url = "test_url"
        self.sha = "test_sha"
        self.creator = CourseCreator(
            api_key=self.api_key,
            article_type="course",
            force_duplicate_questions=True,
            repo_read_token=self.token,
            repo_url=self.url,
            commit_sha=self.sha,
        )
        # Ensure session is a mock we can assert on
        if not isinstance(self.creator.session, mock.Mock):
            self.creator.session = mock.Mock()
        else:
            self.creator.session.reset_mock()

    def test_run_success(self):
        """Test successful course creation."""
        self.creator.load_course_data = mock.Mock(return_value={"valid": "data"})

        mock_response = mock.Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"article": {"customId": "123"}}
        self.creator.session.request.return_value = mock_response

        self.creator.run()

        self.creator.session.request.assert_called_once()
        args, kwargs = self.creator.session.request.call_args

        payload = json.loads(kwargs["data"])
        assert payload["repoReadToken"] == self.token
        assert payload["forceDuplicateQuestions"] is True
        assert kwargs["headers"]["X-API-Key"] == self.api_key
        assert args[0] == "POST"
        assert "/learn/articles/course/ingest" in args[1]

    def test_run_success_jsend_response(self):
        """Test successful course creation with JSend response format."""
        self.creator.load_course_data = mock.Mock(return_value={"valid": "data"})

        mock_response = mock.Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {
            "status": "success",
            "data": {"article": {"customId": "course-456"}},
        }
        self.creator.session.request.return_value = mock_response

        self.creator.run()

        self.creator.session.request.assert_called_once()
        args, kwargs = self.creator.session.request.call_args

        payload = json.loads(kwargs["data"])
        assert payload["repoReadToken"] == self.token
        assert payload["forceDuplicateQuestions"] is True
        assert kwargs["headers"]["X-API-Key"] == self.api_key
        assert args[0] == "POST"
        assert "/learn/articles/course/ingest" in args[1]

    def test_run_failure(self):
        """Test failure scenario."""
        self.creator.load_course_data = mock.Mock(return_value={"course": "data"})

        mock_response = mock.Mock()
        mock_response.status_code = 400
        mock_response.text = "bad request"
        self.creator.session.request.return_value = mock_response

        with pytest.raises(ActionError):
            self.creator.run()

        self.creator.session.request.assert_called_once()
        _, kwargs = self.creator.session.request.call_args

        payload = json.loads(kwargs["data"])
        assert payload["data"] == {"course": "data"}

    def test_missing_args(self):
        """Test initialization with missing arguments."""
        creator = CourseCreator(
            api_key="key", repo_read_token=None, repo_url=None, commit_sha=None
        )
        with pytest.raises(ActionError):
            creator.run()

    def test_no_data_file(self):
        """Test behavior when data file doesn't exist."""
        self.creator.load_course_data = mock.Mock(
            side_effect=ActionError("course_data.json not found")
        )
        with pytest.raises(ActionError):
            self.creator.run()

    def test_api_fail_network(self):
        """Test network failure."""
        self.creator.load_course_data = mock.Mock(return_value={})

        self.creator.session.request.reset_mock()
        self.creator.session.request.side_effect = requests.RequestException(
            "Network Error"
        )

        with pytest.raises(ActionError):
            self.creator.run()

    def test_invalid_article_type(self):
        """Test invalid article type defaults to course."""
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"article": {"customId": "course-123"}}

        creator = CourseCreator(
            api_key="key",
            article_type="invalid_type",
            repo_read_token="t",
            repo_url="u",
            commit_sha="s",
        )
        if not isinstance(creator.session, mock.Mock):
            creator.session = mock.Mock()
        else:
            creator.session.reset_mock()

        creator.load_course_data = mock.Mock(return_value={})
        creator.session.request.return_value = mock_response
        creator.session.request.side_effect = None

        creator.run()

        assert creator.article_type == ArticleType.COURSE
        args, kwargs = creator.session.request.call_args
        assert args[0] == "POST"
        assert "/learn/articles/course/ingest" in args[1]
