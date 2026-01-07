import os
import sys
import pytest
from unittest import mock

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

from validate_api_key import AuthValidator
from common import Config

class TestAuthValidator:
    
    @mock.patch('validate_api_key.QbraidSessionV1')
    def test_validate_success(self, mock_session_cls):
        """Test successful API key validation."""
        # Setup mock session and response
        mock_instance = mock_session_cls.return_value
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"email": "test@example.com"}
        mock_instance.get.return_value = mock_response

        validator = AuthValidator("valid_key")
        # Should execute without raising SystemExit
        validator.validate()
        
        # Verify call
        mock_instance.get.assert_called_once()
    
    @mock.patch('validate_api_key.QbraidSessionV1')
    def test_validate_invalid(self, mock_session_cls):
        """Test invalid API key validation."""
        mock_instance = mock_session_cls.return_value
        mock_response = mock.Mock()
        mock_response.status_code = 401
        mock_instance.get.return_value = mock_response

        validator = AuthValidator("invalid_key")
        # Expect sys.exit(1)
        with pytest.raises(SystemExit) as e:
            validator.validate()
        
        assert e.value.code == 1

    @mock.patch('validate_api_key.QbraidSessionV1')
    def test_validate_connection_error(self, mock_session_cls):
        """Test connection error."""
        mock_instance = mock_session_cls.return_value
        mock_instance.get.side_effect = Exception("Connection failed")
        
        validator = AuthValidator("any_key")
        with pytest.raises(SystemExit) as e:
            validator.validate()
        assert e.value.code == 1
