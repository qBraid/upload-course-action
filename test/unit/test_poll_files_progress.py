import os
import sys
from unittest import mock

import pytest
import requests

# Add src/scripts to path
sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src/scripts"))
)

# Mock QbraidSessionV1 for import
try:
    import qbraid_core

    if not hasattr(qbraid_core, "QbraidSessionV1"):
        qbraid_core.QbraidSessionV1 = mock.Mock()
except ImportError:
    qbraid_core = mock.Mock()
    sys.modules["qbraid_core"] = qbraid_core
    if not hasattr(qbraid_core, "QbraidSessionV1"):
        qbraid_core.QbraidSessionV1 = mock.Mock()

from common import Config
from poll_files_progress import ProgressPoller


class TestProgressPoller:

    @mock.patch("poll_files_progress.ProgressPoller.fetch_status")
    @mock.patch("poll_files_progress.time.sleep")
    def test_run_success(self, mock_sleep, mock_fetch):
        """Test successful polling."""

        poller = ProgressPoller("key", "id")

        mock_fetch.return_value = {"status": "processed", "qbookUrl": "http://url"}

        with pytest.raises(SystemExit) as e:
            poller.run()
        assert e.value.code == 0

        mock_fetch.assert_called()

    @mock.patch("poll_files_progress.ProgressPoller.fetch_status")
    @mock.patch("poll_files_progress.time.sleep")
    def test_run_processing_then_success(self, mock_sleep, mock_fetch):
        """Test polling with intermediate processing status."""

        poller = ProgressPoller("key", "id")

        mock_fetch.side_effect = [
            {"status": "processing"},
            {"status": "processed", "qbookUrl": "http://url"},
        ]

        with pytest.raises(SystemExit) as e:
            poller.run()
        assert e.value.code == 0

        assert mock_fetch.call_count == 2
        assert mock_sleep.call_count >= 1

    @mock.patch("poll_files_progress.ProgressPoller.fetch_status")
    @mock.patch("poll_files_progress.time.sleep")
    def test_run_failed(self, mock_sleep, mock_fetch):
        """Test polling resulting in failure."""
        poller = ProgressPoller("key", "id")

        mock_fetch.return_value = {"status": "failed"}

        with pytest.raises(SystemExit) as e:
            poller.run()
        assert e.value.code == 1
