import os
import sys
import pytest
from unittest import mock

# Add src/scripts to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src/scripts')))

from poll_files_progress import ProgressPoller
from common import Config

class TestProgressPoller:

    @mock.patch('poll_files_progress.requests.get')
    # Since I exposed time in poll_files_progress.py, this should work
    @mock.patch('poll_files_progress.time.sleep') 
    def test_run_success(self, mock_sleep, mock_get):
        """Test successful polling."""
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "processed", "qbookUrl": "http://url"}
        mock_get.return_value = mock_response
        
        poller = ProgressPoller("key", "id")
        
        with pytest.raises(SystemExit) as e:
            poller.run()
        assert e.value.code == 0
        
    @mock.patch('poll_files_progress.requests.get')
    @mock.patch('poll_files_progress.time.sleep')
    def test_run_processing_then_success(self, mock_sleep, mock_get):
        """Test polling with intermediate processing status."""
        resp_processing = mock.Mock()
        resp_processing.status_code = 200
        resp_processing.json.return_value = {"status": "processing"}
        
        resp_success = mock.Mock()
        resp_success.status_code = 200
        resp_success.json.return_value = {"status": "processed", "qbookUrl": "http://url"}
        
        mock_get.side_effect = [resp_processing, resp_success]
        
        poller = ProgressPoller("key", "id")
        
        with pytest.raises(SystemExit) as e:
            poller.run()
        assert e.value.code == 0
        
        assert mock_get.call_count == 2
        assert mock_sleep.call_count >= 1

    @mock.patch('poll_files_progress.requests.get')
    @mock.patch('poll_files_progress.time.sleep')
    def test_run_failed(self, mock_sleep, mock_get):
        """Test polling resulting in failure."""
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "failed"}
        mock_get.return_value = mock_response
        
        poller = ProgressPoller("key", "id")
        
        with pytest.raises(SystemExit) as e:
            poller.run()
        assert e.value.code == 1
