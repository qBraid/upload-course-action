import os
import sys
import importlib
from unittest import mock

# Add src/scripts to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src/scripts')))

def test_config_default():
    """Test that default API_BASE_URL is set correctly when env var is missing."""
    with mock.patch.dict(os.environ, {}, clear=True):
        if 'common' in sys.modules:
            import common
            importlib.reload(common)
        else:
            import common
            
        assert common.Config.API_BASE_URL == "https://c94ea32cc919.ngrok-free.app/app1"

def test_config_env_override():
    """Test that API_BASE_URL honors environment variable override."""
    test_url = "https://test.qbraid.com"
    with mock.patch.dict(os.environ, {"QBRAID_API_BASE_URL": test_url}):
        if 'common' in sys.modules:
            import common
            importlib.reload(common)
        else:
            import common
            
        assert common.Config.API_BASE_URL == test_url

