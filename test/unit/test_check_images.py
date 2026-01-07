import os
import sys
import pytest
from unittest import mock
from pathlib import Path

# Add src/scripts to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src/scripts')))

from check_images import ImageValidator
from common import Config

class TestImageValidator:

    def setup_method(self):
        self.validator = ImageValidator()

    @mock.patch('nbformat.read')
    @mock.patch('builtins.open', new_callable=mock.mock_open)
    @mock.patch('os.path.exists')
    @mock.patch('check_images.Path.stat')
    def test_check_notebook_images_valid(self, mock_stat, mock_exists, mock_open, mock_nb_read):
        """Test with valid images."""
        mock_exists.return_value = True
        mock_stat.return_value.st_size = 500 # Small size
        
        # Mock Notebook
        mock_cell = mock.Mock()
        mock_cell.cell_type = 'markdown'
        mock_cell.source = '![img](valid.png) <img src="valid2.png">'
        mock_nb = mock.Mock()
        mock_nb.cells = [mock_cell]
        mock_nb_read.return_value = mock_nb
        
        self.validator.check_notebook_images("notebook.ipynb")
        assert len(self.validator.image_issues) == 0

    @mock.patch('nbformat.read')
    @mock.patch('builtins.open', new_callable=mock.mock_open)
    @mock.patch('os.path.exists')
    def test_check_notebook_images_missing(self, mock_exists, mock_open, mock_nb_read):
        """Test with missing images."""
        mock_exists.return_value = False
        
        mock_cell = mock.Mock()
        mock_cell.cell_type = 'markdown'
        mock_cell.source = '![img](missing.png)'
        mock_nb = mock.Mock()
        mock_nb.cells = [mock_cell]
        mock_nb_read.return_value = mock_nb
        
        self.validator.check_notebook_images("notebook.ipynb")
        assert len(self.validator.image_issues) == 1
        assert self.validator.image_issues[0]['issue'] == 'missing'

    @mock.patch('nbformat.read')
    @mock.patch('builtins.open', new_callable=mock.mock_open)
    @mock.patch('os.path.exists')
    @mock.patch('check_images.Path.stat')
    def test_check_notebook_images_oversized(self, mock_stat, mock_exists, mock_open, mock_nb_read):
        """Test with oversized images."""
        mock_exists.return_value = True
        # Make it larger than Config.MAX_IMAGE_SIZE_MB (15MB)
        mock_stat.return_value.st_size = 20 * 1024 * 1024 # 20MB
        
        mock_cell = mock.Mock()
        mock_cell.cell_type = 'markdown'
        mock_cell.source = '![img](large.png)'
        mock_nb = mock.Mock()
        mock_nb.cells = [mock_cell]
        mock_nb_read.return_value = mock_nb
        
        self.validator.check_notebook_images("notebook.ipynb")
        assert len(self.validator.image_issues) == 1
        assert self.validator.image_issues[0]['issue'] == 'oversized'

    @mock.patch('builtins.open', new_callable=mock.mock_open)
    @mock.patch('json.load')
    @mock.patch('os.path.exists')
    @mock.patch('check_images.ImageValidator.check_notebook_images')
    def test_verify_images_success(self, mock_check, mock_exists, mock_json, mock_open):
        """Test verify_images with no issues."""
        mock_exists.return_value = True
        mock_json.return_value = {
            'content': [{'baseFilePath': 'nb1.ipynb', 'sections': [{'baseFilePath': 'nb2.ipynb'}]}]
        }
        
        # Should finish without error
        try:
            self.validator.run()
        except SystemExit:
            pytest.fail("Verifier raised SystemExit unexpectedly!")
        
    @mock.patch('builtins.open', new_callable=mock.mock_open)
    @mock.patch('json.load')
    @mock.patch('os.path.exists')
    def test_verify_images_failed(self, mock_exists, mock_json, mock_open):
        """Test verify_images with issues (simulated by injecting issue manually or mocking check_notebook_images logic)."""
        mock_exists.return_value = True
        mock_json.return_value = {
            'content': [{'baseFilePath': 'nb1.ipynb'}]
        }
        
        # We can subclass or mock the internal check, or simpler: just mock check_notebook_images to append to self.image_issues
        
        # Actually since we are testing self.validator.run(), we need to mock check_notebook_images on self.validator object if we were using a single instance, but run() calls check_notebook_images on itself.
        # We can use mock.patch object
        
        with mock.patch.object(self.validator, 'check_notebook_images', side_effect=lambda x: self.validator.image_issues.append({'issue': 'missing', 'notebook': x, 'type': 'absolute', 'image': 'img.png'})):
             # Should raise SystemExit
            with pytest.raises(SystemExit) as e:
                self.validator.run()
            assert e.value.code == 1

