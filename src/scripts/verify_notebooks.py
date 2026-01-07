import json
import os
import sys
import nbformat
import re
from typing import List, Dict, Any, Union
from common import setup_logging, Config

logger = setup_logging(__name__)

class NotebookVerifier:
    """Verifies that all notebook files exist and contain valid and safe content."""

    def __init__(self):
        self.missing_files: List[str] = []
        self.content_errors: Dict[str, List[str]] = {}
        self.forbidden_patterns = [
            # More specific patterns to reduce false positives
            # Look for actual token/key assignments with realistic values
            (re.compile(r'(?:api[_-]?key|token|access[_-]?token|auth[_-]?token)\s*[=:]\s*[\'"][-a-zA-Z0-9_]{20,}[\'"]', re.IGNORECASE), 
             "Potential API token/key found (long alphanumeric value)"),
            (re.compile(r'\bpassword\s*[=:]\s*[\'"][^\'"]{8,}[\'"]', re.IGNORECASE), 
             "Potential password found (8+ chars)"),
            # AWS keys pattern - AKIA or A3T followed by exactly 16 characters
            (re.compile(r'(?:AKIA|A3T)[A-Z0-9]{16}'), 
             "Potential AWS access key found"),
            # Private keys
            (re.compile(r'-----BEGIN (?:RSA |DSA |EC )?PRIVATE KEY-----'), 
             "Private key found"),
        ]
        self.script_tag_regex = re.compile(r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>', re.IGNORECASE)
        self.iframe_regex = re.compile(r'<iframe\b[^<]*(?:(?!<\/iframe>)<[^<]*)*<\/iframe>', re.IGNORECASE)
        self.src_attribute_regex = re.compile(r'src\s*=\s*["\'][^"\']*javascript:', re.IGNORECASE)


    def check_file_size(self, file_path: str, max_size_mb: int = Config.MAX_NOTEBOOK_SIZE_MB) -> List[str]:
        """Checks if the file size is within the allowed limit."""
        try:
            size_mb = os.path.getsize(file_path) / (1024 * 1024)
            if size_mb > max_size_mb:
                return [f"File size {size_mb:.2f}MB exceeds limit of {max_size_mb}MB"]
            return []
        except OSError as e:
            return [f"Could not check file size: {str(e)}"]

    def check_nbformat_validity(self, nb: nbformat.NotebookNode) -> List[str]:
        """Checks if the notebook conforms to the nbformat schema."""
        try:
            nbformat.validate(nb)
            return []
        except nbformat.ValidationError as e:
            return [f"Notebook validation error: {str(e)}"]

    def check_forbidden_patterns(self, content: str) -> List[str]:
        """Checks for forbidden patterns in the notebook content."""
        errors = []
        for pattern, message in self.forbidden_patterns:
            if pattern.search(content):
                errors.append(message)
        return errors

    def contains_script_tag(self, input_string: str) -> bool:
        """Checks if the input string contains any <script> tags."""
        return bool(self.script_tag_regex.search(input_string))

    def contains_malicious_iframe(self, input_string: str) -> bool:
        """Checks if the input string contains any <iframe> tags with a src attribute that uses the "javascript:" protocol."""
        # Check if iframe exists and if it contains a malicious src attribute
        if self.iframe_regex.search(input_string):
            return bool(self.src_attribute_regex.search(input_string))
        return False

    def validate_notebook_content(self, file_path: str) -> List[str]:
        """Validates the content of a notebook file for security issues."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                nb = nbformat.read(f, as_version=4)
        except Exception as e:
            return [f"Could not read notebook: {str(e)}"]

        errors: List[str] = []
        for idx, cell in enumerate(nb.cells):
            if cell.cell_type == 'markdown':
                content = cell.source
                if self.contains_script_tag(content):
                    errors.append(f"Cell {idx+1}: Contains forbidden <script> tag")
                if self.contains_malicious_iframe(content):
                    errors.append(f"Cell {idx+1}: Contains forbidden malicious <iframe> tag")
                
                pattern_errors = self.check_forbidden_patterns(content)
                for err in pattern_errors:
                    errors.append(f"Cell {idx+1}: {err}")
                        
        size_errors = self.check_file_size(file_path)
        errors.extend(size_errors)
        format_errors = self.check_nbformat_validity(nb)
        errors.extend(format_errors)
                
        return errors

    def check_file(self, path: str, context: str) -> None:
        if not os.path.exists(path):
            self.missing_files.append(f"{context}: {path}")
        else:
            # Validate content if file exists
            errors = self.validate_notebook_content(path)
            if errors:
                self.content_errors[f"{context} ({path})"] = errors

    def run(self) -> None:
        """
        Verifies that all notebook files exist and contain valid and safe content.
        """
        if not os.path.exists(Config.COURSE_DATA_FILE_NAME):
            logger.error(f"{Config.COURSE_DATA_FILE_NAME} not found. Run validation first.")
            sys.exit(1)

        try:
            with open(Config.COURSE_DATA_FILE_NAME, 'r') as f:
                course_data = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load {Config.COURSE_DATA_FILE_NAME}: {e}")
            sys.exit(1)

        for chapter in course_data['content']:
            self.check_file(chapter['baseFilePath'], "Chapter")
            
            if 'sections' in chapter:
                for section in chapter['sections']:
                    self.check_file(section['baseFilePath'], "Section")

        failed = False

        if self.missing_files:
            logger.error("The following notebook files are missing:")
            for file in self.missing_files:
                logger.error(f"  - {file}")
            failed = True

        if self.content_errors:
            logger.error("The following notebooks contain validation errors:")
            for file, errors in self.content_errors.items():
                logger.error(f"  {file}:")
                for error in errors:
                    logger.error(f"    - {error}")
            failed = True

        if failed:
            sys.exit(1)

        logger.info("✅ All notebook files exist and passed content validation")

def verify_notebooks():
    """Wrapper function for backwards compatibility."""
    verifier = NotebookVerifier()
    verifier.run()

if __name__ == "__main__":
    verify_notebooks()
