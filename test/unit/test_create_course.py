import os
import sys
import pytest
from unittest import mock

# Add src/scripts to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src/scripts')))

import create_course

class TestCreateCourse:
    
    @mock.patch('create_course.requests.post')
    @mock.patch('builtins.open', new_callable=mock.mock_open)
    @mock.patch('json.load')
    @mock.patch('os.path.exists')
    def test_create_course_success(self, mock_exists, mock_json, mock_open, mock_post):
        mock_exists.return_value = True
        mock_json.return_value = {"course": "data"}
        
        mock_response = mock.Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {"article": {"customId": "123"}}
        mock_post.return_value = mock_response
        
        # Call
        create_course.create_course(
            "key", "course", True, "token", "url", "sha"
        )
        
        # Verify
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert kwargs['headers']['X-API-Key'] == 'key'
        assert kwargs['json']['data'] == {"course": "data"}
        assert kwargs['json']['repoReadToken'] == "token"

    def test_create_course_missing_args(self):
        with pytest.raises(SystemExit) as e:
            create_course.create_course("key", repo_read_token=None)
        assert e.value.code == 1

    @mock.patch('os.path.exists')
    def test_create_course_no_data_file(self, mock_exists):
        mock_exists.return_value = False
        with pytest.raises(SystemExit) as e:
             create_course.create_course("key", "course", True, "token", "url", "sha")
        assert e.value.code == 1

    @mock.patch('create_course.requests.post')
    @mock.patch('builtins.open', new_callable=mock.mock_open)
    @mock.patch('json.load')
    @mock.patch('os.path.exists')
    def test_create_course_api_fail(self, mock_exists, mock_json, mock_open, mock_post):
        mock_exists.return_value = True
        mock_json.return_value = {}
        
        mock_response = mock.Mock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_post.return_value = mock_response
        
        with pytest.raises(SystemExit) as e:
             create_course.create_course("key", "course", True, "token", "url", "sha")
        assert e.value.code == 1

    @mock.patch('create_course.requests.post')
    @mock.patch('builtins.open', new_callable=mock.mock_open)
    @mock.patch('json.load')
    @mock.patch('os.path.exists')
    def test_create_course_invalid_response(self, mock_exists, mock_json, mock_open, mock_post):
        mock_exists.return_value = True
        mock_json.return_value = {}
        
        mock_response = mock.Mock()
        mock_response.status_code = 201
        mock_response.json.return_value = {} # Missing 'article' key
        mock_post.return_value = mock_response
        
        with pytest.raises(SystemExit) as e:
             create_course.create_course("key", "course", True, "token", "url", "sha")
        assert e.value.code == 1

    @mock.patch('create_course.requests.post')
    @mock.patch('builtins.open', new_callable=mock.mock_open)
    @mock.patch('json.load')
    @mock.patch('os.path.exists')
    def test_create_course_network_error(self, mock_exists, mock_json, mock_open, mock_post):
        mock_exists.return_value = True
        mock_json.return_value = {}
        
        mock_post.side_effect = create_course.requests.exceptions.ConnectionError
        
        with pytest.raises(SystemExit) as e:
             create_course.create_course("key", "course", True, "token", "url", "sha")
        assert e.value.code == 1

