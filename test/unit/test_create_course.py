import os
import sys
import pytest
from unittest import mock
import json
import requests

# Add src/scripts to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src/scripts')))

# Mock QbraidSessionV1 for import
try:
    import qbraid_core
    if not hasattr(qbraid_core, 'QbraidSessionV1'):
        qbraid_core.QbraidSessionV1 = mock.Mock()
except ImportError:
    qbraid_core = mock.Mock()
    sys.modules['qbraid_core'] = qbraid_core
    if not hasattr(qbraid_core, 'QbraidSessionV1'):
        qbraid_core.QbraidSessionV1 = mock.Mock()

from create_course import CourseCreator
from common import Config, ActionError, ArticleType

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
            commit_sha=self.sha
        )
        # Ensure session is a mock we can assert on
        if not isinstance(self.creator.session, mock.Mock):
             self.creator.session = mock.Mock()
        else:
             self.creator.session.reset_mock()

    @mock.patch('builtins.open', new_callable=mock.mock_open)
    @mock.patch('json.load')
    @mock.patch('create_course.Path.exists')
    def test_run_success(self, mock_exists, mock_json_load, mock_file):
        """Test successful course creation."""
        mock_exists.return_value = True
        mock_json_load.return_value = {"valid": "data"}
        
        mock_response = mock.Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"article": {"customId": "123"}}
        self.creator.session.post.return_value = mock_response
        
        self.creator.run()
        
        # Verify post called
        self.creator.session.post.assert_called_once()
        args, kwargs = self.creator.session.post.call_args
        
        payload = json.loads(kwargs['data'])
        assert payload['repoReadToken'] == self.token
        assert payload['forceDuplicateQuestions'] is True
        assert kwargs['headers']['X-API-Key'] == self.api_key

    @mock.patch('builtins.open', new_callable=mock.mock_open)
    @mock.patch('json.load')
    @mock.patch('create_course.Path.exists')
    def test_run_failure(self, mock_exists, mock_json_load, mock_file):
        """Test failure scenario."""
        mock_exists.return_value = True
        mock_json_load.return_value = {"course": "data"}
        
        mock_response = mock.Mock()
        mock_response.status_code = 400
        self.creator.session.post.return_value = mock_response
        
        with pytest.raises(ActionError):
            self.creator.run()
        
        # Verify
        self.creator.session.post.assert_called_once()
        args, kwargs = self.creator.session.post.call_args
        
        payload = json.loads(kwargs['data'])
        assert payload['data'] == {"course": "data"}

    def test_missing_args(self):
        """Test initialization with missing arguments."""
        creator = CourseCreator(api_key="key", repo_read_token=None, repo_url=None, commit_sha=None)
        with pytest.raises(ActionError):
            creator.run()

    @mock.patch('create_course.Path.exists')
    def test_no_data_file(self, mock_exists):
        """Test behavior when data file doesn't exist."""
        mock_exists.return_value = False
        with pytest.raises(ActionError):
            self.creator.run()

    @mock.patch('builtins.open', new_callable=mock.mock_open)
    @mock.patch('json.load')
    @mock.patch('create_course.Path.exists')
    def test_api_fail_network(self, mock_exists, mock_json, mock_open):
        """Test network failure."""
        mock_exists.return_value = True
        mock_json.return_value = {}
        
        self.creator.session.post.reset_mock()
        self.creator.session.post.side_effect = requests.RequestException("Network Error")
        
        with pytest.raises(ActionError):
            self.creator.run()

    @mock.patch('builtins.open', new_callable=mock.mock_open)
    @mock.patch('json.load')
    @mock.patch('create_course.Path.exists')
    def test_invalid_article_type(self, mock_exists, mock_json, mock_open):
        """Test invalid article type defaults to course."""
        mock_exists.return_value = True
        mock_json.return_value = {}
        
        mock_response = mock.Mock()
        mock_response.status_code = 200
        
        creator = CourseCreator(
            api_key="key", 
            article_type="invalid_type", 
            repo_read_token="t", 
            repo_url="u", 
            commit_sha="s"
        )
        if not isinstance(creator.session, mock.Mock):
            creator.session = mock.Mock()
        else:
            creator.session.reset_mock()
            
        creator.session.post.return_value = mock_response
        creator.session.post.side_effect = None

        creator.run()
        
        assert creator.article_type == ArticleType.COURSE
        args, kwargs = creator.session.post.call_args
        assert "/learn/articles/course/ingest" in args[0]
