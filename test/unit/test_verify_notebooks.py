from unittest import mock

import nbformat
import pytest
from common import Config
from verify_notebooks import NotebookVerifier


@pytest.mark.unit
class TestNotebookVerifier:

    def setup_method(self):
        self.verifier = NotebookVerifier()

    def test_check_file_size(self):
        """Test file size checking."""
        with mock.patch("os.path.getsize") as mock_size:
            # Under limit
            mock_size.return_value = 1 * 1024 * 1024  # 1MB
            assert self.verifier.check_file_size("dummy.ipynb") == []

            # Over limit
            mock_size.return_value = (Config.MAX_NOTEBOOK_SIZE_MB + 1) * 1024 * 1024
            errors = self.verifier.check_file_size("dummy.ipynb")
            assert len(errors) == 1
            assert "exceeds limit" in errors[0]

    def test_check_nbformat_validity(self):
        """Test nbformat validation."""
        with mock.patch("nbformat.validate") as mock_validate:
            # Valid
            errors = self.verifier.check_nbformat_validity(mock.Mock())
            assert errors == []

            # Invalid
            mock_validate.side_effect = nbformat.ValidationError("Invalid format")
            errors = self.verifier.check_nbformat_validity(mock.Mock())
            assert len(errors) == 1
            assert "validation error" in errors[0]

    def test_check_forbidden_patterns(self):
        """Test regex pattern matching for secrets."""
        # Safe content
        assert self.verifier.check_forbidden_patterns("print('Hello World')") == []

        # API Key
        unsafe_key = "api_key = 'abcdef1234567890abcdef1234567890'"
        errors = self.verifier.check_forbidden_patterns(unsafe_key)
        assert len(errors) > 0

        # AWS Key
        unsafe_aws = "AKIAABCDEFGHIJKLMNOP"
        errors = self.verifier.check_forbidden_patterns(unsafe_aws)
        assert len(errors) > 0

    def test_contains_script_tag(self):
        """Test script tag detection."""
        assert self.verifier.contains_script_tag("<script>alert(1)</script>") is True
        assert self.verifier.contains_script_tag("<div>text</div>") is False

    @mock.patch("nbformat.read")
    @mock.patch("builtins.open", new_callable=mock.mock_open)
    @mock.patch("verify_notebooks.NotebookVerifier.check_file_size")
    @mock.patch("verify_notebooks.NotebookVerifier.check_nbformat_validity")
    def test_validate_notebook_content(
        self, mock_nb_valid, mock_size, mock_open, mock_nb_read
    ):
        """Test full notebook content validation."""
        mock_size.return_value = []
        mock_nb_valid.return_value = []

        # Valid notebook
        mock_cell = mock.Mock()
        mock_cell.cell_type = "markdown"
        mock_cell.source = "Clean content"
        mock_nb = mock.Mock()
        mock_nb.cells = [mock_cell]
        mock_nb_read.return_value = mock_nb

        errors = self.verifier.validate_notebook_content("path.ipynb")
        assert len(errors) == 0

        # Invalid notebook
        mock_cell.source = "<script>alert(1)</script>"
        errors = self.verifier.validate_notebook_content("path.ipynb")
        assert len(errors) > 0

    @mock.patch("builtins.open", new_callable=mock.mock_open)
    @mock.patch("json.load")
    @mock.patch("os.path.exists")
    @mock.patch("verify_notebooks.NotebookVerifier.validate_notebook_content")
    def test_verify_notebooks_success(
        self, mock_validate, mock_exists, mock_json, mock_open
    ):
        """Test successful execution of run."""
        mock_exists.return_value = True
        mock_json.return_value = {"content": [{"baseFilePath": "nb1.ipynb"}]}
        mock_validate.return_value = []

        try:
            self.verifier.run()
        except SystemExit:
            pytest.fail("Verifier raised SystemExit unexpectedly!")

    @mock.patch("os.path.exists")
    def test_verify_notebooks_missing_course_data(self, mock_exists):
        """Test run when course_data.json is missing."""
        mock_exists.return_value = False
        with pytest.raises(SystemExit) as e:
            self.verifier.run()
        assert e.value.code == 1
