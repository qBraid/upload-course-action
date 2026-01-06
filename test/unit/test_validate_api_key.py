import os
import sys
import pytest
from unittest import mock

# Add src/scripts to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src/scripts')))

import validate_api_key

class TestValidateApiKey:
    
    @mock.patch('validate_api_key.requests.get')
    def test_validate_api_key_success(self, mock_get):
        """Test successful API key validation."""
        # Setup mock response
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"email": "test@example.com"}
        mock_get.return_value = mock_response

        # Expect sys.exit(0)
        with pytest.raises(SystemExit) as pytest_wrapped_e:
            validate_api_key.validate_api_key("valid_key")
        
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 0
        
        # Verify URL and Headers
        mock_get.assert_called_once()
        args, kwargs = mock_get.call_args
        assert kwargs['headers']['X-API-Key'] == 'valid_key'

    @mock.patch('validate_api_key.requests.get')
    def test_validate_api_key_invalid(self, mock_get):
        """Test invalid API key (401)."""
        mock_response = mock.Mock()
        mock_response.status_code = 401
        mock_get.return_value = mock_response

        with pytest.raises(SystemExit) as pytest_wrapped_e:
            validate_api_key.validate_api_key("invalid_key")
        
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 1

    @mock.patch('validate_api_key.requests.get')
    def test_validate_api_key_other_error(self, mock_get):
        """Test other API error."""
        mock_response = mock.Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_get.return_value = mock_response

        with pytest.raises(SystemExit) as pytest_wrapped_e:
            validate_api_key.validate_api_key("key")
        
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 1

    @mock.patch('validate_api_key.requests.get')
    def test_validate_api_key_timeout(self, mock_get):
        """Test timeout exception."""
        mock_get.side_effect = validate_api_key.requests.exceptions.Timeout

        with pytest.raises(SystemExit) as pytest_wrapped_e:
            validate_api_key.validate_api_key("key")
        
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 1

    @mock.patch('validate_api_key.requests.get')
    def test_validate_api_key_connection_error(self, mock_get):
        """Test connection error."""
        mock_get.side_effect = validate_api_key.requests.exceptions.ConnectionError

        with pytest.raises(SystemExit) as pytest_wrapped_e:
            validate_api_key.validate_api_key("key")
        
        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 1
