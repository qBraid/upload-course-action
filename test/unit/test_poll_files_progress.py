from unittest import mock

import pytest
from common import Config
from poll_files_progress import ProgressPoller


@pytest.mark.unit
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

    @mock.patch("poll_files_progress.ProgressPoller.fetch_status")
    @mock.patch("poll_files_progress.time.sleep")
    def test_run_qbookurl_exits_immediately(self, mock_sleep, mock_fetch):
        """Test that qbookUrl presence causes immediate exit regardless of status."""
        poller = ProgressPoller("key", "id")

        # qbookUrl present but status is not "processed" - should still exit successfully
        mock_fetch.return_value = {"status": "processing", "qbookUrl": "http://url"}

        with pytest.raises(SystemExit) as e:
            poller.run()
        assert e.value.code == 0

        # Should only call fetch_status once since we exit immediately
        assert mock_fetch.call_count == 1
        # Should not sleep since we exit immediately
        assert mock_sleep.call_count == 0

    def test_normalize_qbook_url_legacy_format(self):
        url = "https://qbook-staging.qbraid.com/learn/?article=abc&file=def"
        assert (
            ProgressPoller.normalize_qbook_url(url)
            == "https://qbook-staging.qbraid.com/learn/course/abc/def"
        )

    def test_normalize_qbook_url_non_legacy(self):
        url = "https://qbook-staging.qbraid.com/learn/course/abc/def"
        assert ProgressPoller.normalize_qbook_url(url) == url
