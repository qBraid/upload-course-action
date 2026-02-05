import importlib
import os
import sys
from unittest import mock

import pytest


@pytest.mark.unit
def test_config_default():
    """Test that default API_BASE_URL is set correctly when env var is missing."""
    with mock.patch.dict(os.environ, {}, clear=True):
        if "common" in sys.modules:
            import common

            importlib.reload(common)
        else:
            import common

        assert common.Config.API_BASE_URL == "https://api-staging.qbraid.com/api/v1"
        assert common.Config.MAX_POLL_ATTEMPTS == 15
        assert common.Config.POLL_INTERVAL_SECONDS == 15
        assert common.Config.MAX_CONSECUTIVE_ERRORS == 5
        assert common.Config.REQUEST_TIMEOUT_SECONDS == 30


@pytest.mark.unit
def test_config_env_override():
    """Test that API_BASE_URL honors environment variable override."""
    test_url = "https://test.qbraid.com"
    with mock.patch.dict(os.environ, {"QBRAID_API_BASE_URL": test_url}):
        if "common" in sys.modules:
            import common

            importlib.reload(common)
        else:
            import common

        assert common.Config.API_BASE_URL == test_url


@pytest.mark.unit
def test_config_polling_env_overrides():
    """Test polling env var overrides and fallback behavior."""
    with mock.patch.dict(
        os.environ,
        {
            "QBRAID_MAX_POLL_ATTEMPTS": "20",
            "QBRAID_POLL_INTERVAL_SECONDS": "30",
            "QBRAID_MAX_CONSECUTIVE_ERRORS": "7",
        },
    ):
def test_config_timeout_env_override():
    """Test timeout env var override and fallback behavior."""
    with mock.patch.dict(os.environ, {"QBRAID_REQUEST_TIMEOUT_SECONDS": "60"}):
        if "common" in sys.modules:
            import common

            importlib.reload(common)
        else:
            import common

        assert common.Config.MAX_POLL_ATTEMPTS == 20
        assert common.Config.POLL_INTERVAL_SECONDS == 30
        assert common.Config.MAX_CONSECUTIVE_ERRORS == 7

    with mock.patch.dict(
        os.environ,
        {
            "QBRAID_MAX_POLL_ATTEMPTS": "invalid",
            "QBRAID_POLL_INTERVAL_SECONDS": "-1",
            "QBRAID_MAX_CONSECUTIVE_ERRORS": "0",
        },
    ):
        import common

        importlib.reload(common)
        assert common.Config.MAX_POLL_ATTEMPTS == 15
        assert common.Config.POLL_INTERVAL_SECONDS == 15
        assert common.Config.MAX_CONSECUTIVE_ERRORS == 5
        assert common.Config.REQUEST_TIMEOUT_SECONDS == 60

    with mock.patch.dict(os.environ, {"QBRAID_REQUEST_TIMEOUT_SECONDS": "invalid"}):
        import common

        importlib.reload(common)
        assert common.Config.REQUEST_TIMEOUT_SECONDS == 30
