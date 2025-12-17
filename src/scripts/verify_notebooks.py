import json
import os
import sys

def verify_notebooks():
    if not os.path.exists('course_data.json'):
        print("ERROR: course_data.json not found. Run validation first.")
        sys.exit(1)

    with open('course_data.json', 'r') as f:
        course_data = json.load(f)

    missing_files = []

    for chapter in course_data['content']:
        file_path = chapter['baseFilePath']
        if not os.path.exists(file_path):
            missing_files.append(f"Chapter: {file_path}")
        
        if 'sections' in chapter:
            for section in chapter['sections']:
                section_path = section['baseFilePath']
                if not os.path.exists(section_path):
                    missing_files.append(f"Section: {section_path}")

    if missing_files:
        print("ERROR: The following notebook files are missing:")
        for file in missing_files:
            print(f"  - {file}")
        sys.exit(1)

    print("✅ All notebook files exist at specified paths")

if __name__ == "__main__":
    verify_notebooks()
