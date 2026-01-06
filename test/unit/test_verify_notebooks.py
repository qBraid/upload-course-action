import os
import sys
import pytest
from unittest import mock

# Add src/scripts to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src/scripts')))

import verify_notebooks

class TestVerifyNotebooks:

    def test_check_file_size(self):
        with mock.patch('os.path.getsize') as mock_size:
            mock_size.return_value = 100
            assert verify_notebooks.check_file_size("file") == []
            
            mock_size.return_value = 6 * 1024 * 1024 # 6MB
            errors = verify_notebooks.check_file_size("file")
            assert len(errors) == 1
            assert "exceeds limit" in errors[0]

    def test_check_nbformat_validity(self):
        with mock.patch('nbformat.validate') as mock_validate:
            # Valid
            msg = verify_notebooks.check_nbformat_validity(mock.Mock())
            assert msg == []
            
            # Invalid
            mock_validate.side_effect = verify_notebooks.nbformat.ValidationError("Error")
            msg = verify_notebooks.check_nbformat_validity(mock.Mock())
            assert len(msg) == 1

    def test_check_forbidden_patterns(self):
        # Safe content
        assert verify_notebooks.check_forbidden_patterns("Just some text") == []
        
        # Unsafe content
        unsafe_key = "api_key = '1234567890abcdef1234567890'"
        errors = verify_notebooks.check_forbidden_patterns(unsafe_key)
        assert len(errors) > 0
        assert "Potential API token" in errors[0]
        
        unsafe_aws = "AKIAABCDEFGHIJKLMNOP"
        errors = verify_notebooks.check_forbidden_patterns(unsafe_aws)
        assert len(errors) > 0
        assert "Potential AWS" in errors[0]

    def test_contains_script_tag(self):
        assert verify_notebooks.contains_script_tag("<script>alert(1)</script>") is True
        assert verify_notebooks.contains_script_tag("<div>text</div>") is False

    def test_contains_malicious_iframe(self):
        assert verify_notebooks.contains_malicious_iframe('<iframe src="javascript:alert(1)"></iframe>') is True
        assert verify_notebooks.contains_malicious_iframe('<iframe src="http://example.com"></iframe>') is False
        assert verify_notebooks.contains_malicious_iframe('<div>text</div>') is False

    @mock.patch('nbformat.read')
    @mock.patch('builtins.open', new_callable=mock.mock_open)
    @mock.patch('verify_notebooks.check_file_size')
    @mock.patch('verify_notebooks.check_nbformat_validity')
    def test_validate_notebook_content(self, mock_nb_valid, mock_size, mock_open, mock_nb_read):
        mock_size.return_value = []
        mock_nb_valid.return_value = []
        
        # Valid notebook
        mock_cell = mock.Mock()
        mock_cell.cell_type = 'markdown'
        mock_cell.source = 'Clean content'
        mock_nb = mock.Mock()
        mock_nb.cells = [mock_cell]
        mock_nb_read.return_value = mock_nb
        
        errors = verify_notebooks.validate_notebook_content("path")
        assert len(errors) == 0
        
        # Invalid notebook (script tag)
        mock_cell.source = '<script>alert(1)</script>'
        errors = verify_notebooks.validate_notebook_content("path")
        assert len(errors) > 0
        assert "forbidden <script> tag" in errors[0]

    @mock.patch('builtins.open', new_callable=mock.mock_open)
    @mock.patch('json.load')
    @mock.patch('os.path.exists')
    @mock.patch('verify_notebooks.validate_notebook_content')
    def test_verify_notebooks_success(self, mock_validate, mock_exists, mock_json, mock_open):
        mock_exists.return_value = True
        mock_json.return_value = {
            'content': [{'baseFilePath': 'nb1.ipynb'}]
        }
        mock_validate.return_value = []
        
        verify_notebooks.verify_notebooks()
        # Should finish without error

    @mock.patch('builtins.open', new_callable=mock.mock_open)
    @mock.patch('json.load')
    @mock.patch('os.path.exists')
    @mock.patch('verify_notebooks.validate_notebook_content')
    def test_verify_notebooks_missing_file(self, mock_validate, mock_exists, mock_json, mock_open):
        # Logic: if course_data exists -> True. 
        # Inside loop: check_file -> os.path.exists(path) -> False
        mock_json.return_value = {
            'content': [{'baseFilePath': 'nb1.ipynb'}]
        }
        
        # side_effect for exists: True for course_data.json, False for notebook
        def side_effect(path):
            if path == 'course_data.json': return True
            return False
        
        mock_exists.side_effect = side_effect
        
        with pytest.raises(SystemExit) as e:
            verify_notebooks.verify_notebooks()
        assert e.value.code == 1

    @mock.patch('builtins.open', new_callable=mock.mock_open)
    @mock.patch('json.load')
    @mock.patch('os.path.exists')
    @mock.patch('verify_notebooks.validate_notebook_content')
    def test_verify_notebooks_content_error(self, mock_validate, mock_exists, mock_json, mock_open):
        mock_exists.return_value = True
        mock_json.return_value = {
            'content': [{'baseFilePath': 'nb1.ipynb'}]
        }
        mock_validate.return_value = ["Some error"]
        
        with pytest.raises(SystemExit) as e:
            verify_notebooks.verify_notebooks()
        assert e.value.code == 1
