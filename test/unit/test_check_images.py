import os
import sys
import pytest
from unittest import mock

# Add src/scripts to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src/scripts')))

import check_images

class TestCheckImages:

    @mock.patch('nbformat.read')
    @mock.patch('builtins.open', new_callable=mock.mock_open)
    @mock.patch('os.path.exists')
    @mock.patch('os.path.getsize')
    def test_check_notebook_images_valid(self, mock_getsize, mock_exists, mock_open, mock_nb_read):
        """Test with valid images."""
        mock_exists.return_value = True
        mock_getsize.return_value = 500 # Small size
        
        # Mock Notebook
        mock_cell = mock.Mock()
        mock_cell.cell_type = 'markdown'
        mock_cell.source = '![img](valid.png) <img src="valid2.png">'
        mock_nb = mock.Mock()
        mock_nb.cells = [mock_cell]
        mock_nb_read.return_value = mock_nb
        
        issues = []
        check_images.check_notebook_images("notebook.ipynb", issues)
        assert len(issues) == 0

    @mock.patch('nbformat.read')
    @mock.patch('builtins.open', new_callable=mock.mock_open)
    @mock.patch('os.path.exists')
    def test_check_notebook_images_missing(self, mock_exists, mock_open, mock_nb_read):
        """Test with missing images."""
        # Simulate that all referenced image paths do not exist so missing images are reported.
        mock_exists.return_value = False
        
        mock_cell = mock.Mock()
        mock_cell.cell_type = 'markdown'
        mock_cell.source = '![img](missing.png)'
        mock_nb = mock.Mock()
        mock_nb.cells = [mock_cell]
        mock_nb_read.return_value = mock_nb
        
        issues = []
        check_images.check_notebook_images("notebook.ipynb", issues)
        assert len(issues) == 1
        assert issues[0]['issue'] == 'missing'

    @mock.patch('nbformat.read')
    @mock.patch('builtins.open', new_callable=mock.mock_open)
    @mock.patch('os.path.exists')
    @mock.patch('os.path.getsize')
    def test_check_notebook_images_oversized(self, mock_getsize, mock_exists, mock_open, mock_nb_read):
        """Test with oversized images."""
        mock_exists.return_value = True
        mock_getsize.return_value = 2 * 1024 * 1024 # 2MB
        
        mock_cell = mock.Mock()
        mock_cell.cell_type = 'markdown'
        mock_cell.source = '![img](large.png)'
        mock_nb = mock.Mock()
        mock_nb.cells = [mock_cell]
        mock_nb_read.return_value = mock_nb
        
        issues = []
        check_images.check_notebook_images("notebook.ipynb", issues)
        assert len(issues) == 1
        assert issues[0]['issue'] == 'oversized'

    @mock.patch('builtins.open', new_callable=mock.mock_open)
    @mock.patch('json.load')
    @mock.patch('os.path.exists')
    @mock.patch('check_images.check_notebook_images')
    def test_verify_images_success(self, mock_check, mock_exists, mock_json, mock_open):
        """Test verify_images with no issues."""
        mock_exists.return_value = True
        mock_json.return_value = {
            'content': [{'baseFilePath': 'nb1.ipynb', 'sections': [{'baseFilePath': 'nb2.ipynb'}]}]
        }
        
        # mock_check appends nothing to issues list
        
        # Should finish without error and not raise SystemExit
        check_images.verify_images()
        
        assert mock_check.call_count == 2

        
    @mock.patch('builtins.open', new_callable=mock.mock_open)
    @mock.patch('json.load')
    @mock.patch('os.path.exists')
    @mock.patch('check_images.check_notebook_images')
    def test_verify_images_success_implementation(self, mock_check, mock_exists, mock_json, mock_open):
        mock_exists.return_value = True
        mock_json.return_value = {
            'content': [{'baseFilePath': 'nb1.ipynb'}]
        }
        
        # Function just returns if successful
        check_images.verify_images()
        
        assert mock_check.call_count == 1

    @mock.patch('builtins.open', new_callable=mock.mock_open)
    @mock.patch('json.load')
    @mock.patch('os.path.exists')
    @mock.patch('check_images.check_notebook_images')
    def test_verify_images_failure(self, mock_check, mock_exists, mock_json, mock_open):
        """Test verify_images with issues."""
        mock_exists.return_value = True
        mock_json.return_value = {
            'content': [{'baseFilePath': 'nb1.ipynb'}]
        }
        
        def side_effect(path, issues):
            issues.append({'issue': 'missing', 'notebook': path, 'type': 'relative', 'image': 'img.png'})
        
        mock_check.side_effect = side_effect
        
        with pytest.raises(SystemExit) as e:
            check_images.verify_images()
        assert e.value.code == 1

