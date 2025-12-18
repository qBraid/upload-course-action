import json
import os
import sys
import nbformat
import re

def contains_script_tag(input_string):
    """Checks if the input string contains any <script> tags."""
    # Regex to match <script> tags, handling attributes and content
    script_tag_regex = re.compile(r'<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>', re.IGNORECASE)
    return bool(script_tag_regex.search(input_string))

def contains_malicious_iframe(input_string):
    """Checks if the input string contains any <iframe> tags with a src attribute that uses the "javascript:" protocol."""
    # Regex to match <iframe> tags
    iframe_regex = re.compile(r'<iframe\b[^<]*(?:(?!<\/iframe>)<[^<]*)*<\/iframe>', re.IGNORECASE)
    # Regex to match src="javascript:..."
    src_attribute_regex = re.compile(r'src\s*=\s*["\'][^"\']*javascript:', re.IGNORECASE)
    
    # Check if iframe exists and if it contains a malicious src attribute
    if iframe_regex.search(input_string):
        return bool(src_attribute_regex.search(input_string))
    return False

def validate_notebook_content(file_path):
    """Validates the content of a notebook file for security issues."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            nb = nbformat.read(f, as_version=4)
    except Exception as e:
        return [f"Could not read notebook: {str(e)}"]

    errors = []
    for idx, cell in enumerate(nb.cells):
        if cell.cell_type == 'markdown':
            content = cell.source
            if contains_script_tag(content):
                errors.append(f"Cell {idx+1}: Contains forbidden <script> tag")
            if contains_malicious_iframe(content):
                errors.append(f"Cell {idx+1}: Contains forbidden malicious <iframe> tag")
    return errors

def verify_notebooks():
    if not os.path.exists('course_data.json'):
        print("ERROR: course_data.json not found. Run validation first.")
        sys.exit(1)

    with open('course_data.json', 'r') as f:
        course_data = json.load(f)

    missing_files = []
    content_errors = {}

    def check_file(path, context):
        if not os.path.exists(path):
            missing_files.append(f"{context}: {path}")
        else:
            # Validate content if file exists
            errors = validate_notebook_content(path)
            if errors:
                content_errors[f"{context} ({path})"] = errors

    for chapter in course_data['content']:
        check_file(chapter['baseFilePath'], "Chapter")
        
        if 'sections' in chapter:
            for section in chapter['sections']:
                check_file(section['baseFilePath'], "Section")

    failed = False

    if missing_files:
        print("ERROR: The following notebook files are missing:")
        for file in missing_files:
            print(f"  - {file}")
        failed = True

    if content_errors:
        print("ERROR: The following notebooks contain validation errors:")
        for file, errors in content_errors.items():
            print(f"  {file}:")
            for error in errors:
                print(f"    - {error}")
        failed = True

    if failed:
        sys.exit(1)

    print("✅ All notebook files exist and passed content validation")

if __name__ == "__main__":
    verify_notebooks()
