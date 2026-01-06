import os
import sys
import pytest
from unittest import mock

# Add src/scripts to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src/scripts')))

import poll_files_progress

class TestPollWorker:

    @mock.patch('poll_files_progress.requests.get')
    @mock.patch('poll_files_progress.time.sleep')
    def test_poll_worker_success(self, mock_sleep, mock_get):
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "processed", "qbookUrl": "http://url"}
        mock_get.return_value = mock_response
        
        with pytest.raises(SystemExit) as e:
            poll_files_progress.poll_worker("key", "id")
        assert e.value.code == 0
        
    @mock.patch('poll_files_progress.requests.get')
    @mock.patch('poll_files_progress.time.sleep')
    def test_poll_worker_processing_then_success(self, mock_sleep, mock_get):
        resp_processing = mock.Mock()
        resp_processing.status_code = 200
        resp_processing.json.return_value = {"status": "processing"}
        
        resp_success = mock.Mock()
        resp_success.status_code = 200
        resp_success.json.return_value = {"status": "processed"}
        
        mock_get.side_effect = [resp_processing, resp_success]
        
        with pytest.raises(SystemExit) as e:
            poll_files_progress.poll_worker("key", "id")
        assert e.value.code == 0
        assert mock_get.call_count == 2
        assert mock_sleep.call_count == 1 # Slept once between calls

    @mock.patch('poll_files_progress.requests.get')
    @mock.patch('poll_files_progress.time.sleep')
    def test_poll_worker_failed(self, mock_sleep, mock_get):
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "failed"}
        mock_get.return_value = mock_response
        
        with pytest.raises(SystemExit) as e:
            poll_files_progress.poll_worker("key", "id")
        assert e.value.code == 1

    @mock.patch('poll_files_progress.requests.get')
    @mock.patch('poll_files_progress.time.sleep')
    def test_poll_worker_timeout(self, mock_sleep, mock_get):
        # Simulate max attempts of processing
        mock_response = mock.Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "processing"}
        mock_get.return_value = mock_response
        
        
        with pytest.raises(SystemExit) as e:
            poll_files_progress.poll_worker("key", "id")
        assert e.value.code == 1
        assert mock_get.call_count == 60

    @mock.patch('poll_files_progress.requests.get')
    @mock.patch('poll_files_progress.time.sleep')
    def test_poll_worker_too_many_errors(self, mock_sleep, mock_get):
        mock_get.side_effect = poll_files_progress.requests.exceptions.ConnectionError
        
        with pytest.raises(SystemExit) as e:
            poll_files_progress.poll_worker("key", "id")
        assert e.value.code == 1
        # Test that after 6 consecutive connection errors, the function exits with code 1.
        assert mock_get.call_count == 6

