import os
import sys
import pytest
from unittest import mock
import json
import requests

# Add src/scripts to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src/scripts')))

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

    @mock.patch('create_course.requests.post')
    @mock.patch('builtins.open', new_callable=mock.mock_open)
    @mock.patch('json.load')
    @mock.patch('create_course.Path.exists')
    def test_run_success(self, mock_exists, mock_json_load, mock_file, mock_post):
        """Test successful course creation."""
        mock_exists.return_value = True
        mock_json_load.return_value = {"valid": "data"}
        
        mock_response = mock.Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"article": {"customId": "123"}}
        mock_post.return_value = mock_response
        
        self.creator.run()
        
        # Verify post called
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert kwargs['json']['repoReadToken'] == self.token
        assert kwargs['json']['forceDuplicateQuestions'] is True
        assert kwargs['headers']['X-API-Key'] == self.api_key

    @mock.patch('create_course.requests.post')
    @mock.patch('builtins.open', new_callable=mock.mock_open)
    @mock.patch('json.load')
    @mock.patch('create_course.Path.exists')
    def test_run_failure(self, mock_exists, mock_json_load, mock_file, mock_post):
        """Test failure scenario."""
        mock_exists.return_value = True
        mock_json_load.return_value = {"course": "data"}
        
        mock_response = mock.Mock()
        mock_response.status_code = 400
        mock_post.return_value = mock_response
        
        with pytest.raises(ActionError):
            self.creator.run()
        
        # Verify
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert kwargs['json']['data'] == {"course": "data"}

    def test_missing_args(self):
        """Test initialization with missing arguments."""
        creator = CourseCreator(api_key="key", repo_read_token=None)
        with pytest.raises(ActionError):
            creator.run()

    @mock.patch('create_course.Path.exists')
    def test_no_data_file(self, mock_exists):
        """Test behavior when data file doesn't exist."""
        mock_exists.return_value = False
        with pytest.raises(ActionError):
            self.creator.run()

    @mock.patch('create_course.requests.post')
    @mock.patch('builtins.open', new_callable=mock.mock_open)
    @mock.patch('json.load')
    @mock.patch('create_course.Path.exists')
    def test_api_fail_network(self, mock_exists, mock_json, mock_open, mock_post):
        """Test network failure."""
        mock_exists.return_value = True
        mock_json.return_value = {}
        
        mock_post.side_effect = requests.RequestException("Network Error")
        
        with pytest.raises(ActionError):
            self.creator.run()

    @mock.patch('create_course.requests.post')
    @mock.patch('builtins.open', new_callable=mock.mock_open)
    @mock.patch('json.load')
    @mock.patch('create_course.Path.exists')
    def test_invalid_article_type(self, mock_exists, mock_json, mock_open, mock_post):
        """Test invalid article type defaults to course."""
        mock_exists.return_value = True
        mock_json.return_value = {}
        
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        creator = CourseCreator(
            api_key="key", 
            article_type="invalid_type", 
            repo_read_token="t", 
            repo_url="u", 
            commit_sha="s"
        )
        
        creator.run()
        
        assert creator.article_type == ArticleType.COURSE
        args, kwargs = mock_post.call_args
        # Should call the course endpoint
        assert "/api/v1/learn/articles/course/ingest" in args[0]

