import json
import sys
import os
import re

def validate_course_json(course_file):
    if not os.path.exists(course_file):
        print(f"ERROR: {course_file} not found in repository root")
        sys.exit(1)

    with open(course_file, 'r') as f:
        course_data = json.load(f)

    # Validate structure
    required_fields = ['owner_email', 'course_name', 'content']
    for field in required_fields:
        if field not in course_data:
            print(f"ERROR: Missing required field: {field}")
            sys.exit(1)

    # Validate content structure
    if not isinstance(course_data['content'], list):
        print("ERROR: 'content' must be a list of chapters")
        sys.exit(1)

    for idx, chapter in enumerate(course_data['content']):
        if 'kernel_name' not in chapter:
            print(f"ERROR: Chapter {idx} missing 'kernel_name'")
            sys.exit(1)
        if 'chapter_name' not in chapter:
            print(f"ERROR: Chapter {idx} missing 'chapter_name'")
            sys.exit(1)
        if 'file_path' not in chapter:
            print(f"ERROR: Chapter {idx} missing 'file_path'")
            sys.exit(1)
        
        # Check for sections if present
        if 'sections' in chapter:
            if not isinstance(chapter['sections'], list):
                print(f"ERROR: Chapter {idx} 'sections' must be a list")
                sys.exit(1)
            for section_idx, section in enumerate(chapter['sections']):
                if 'section_obj' not in section:
                    print(f"ERROR: Chapter {idx}, Section {section_idx} missing 'section_obj'")
                    sys.exit(1)
                if 'section_name' not in section:
                    print(f"ERROR: Chapter {idx}, Section {section_idx} missing 'section_name'")
                    sys.exit(1)
                if 'file_path' not in section:
                    print(f"ERROR: Chapter {idx}, Section {section_idx} missing 'file_path'")
                    sys.exit(1)

    print("✅ course.json structure is valid")

    # Save course data for next steps
    with open('course_data.json', 'w') as f:
        json.dump(course_data, f)

    # Format course name for GCS
    course_name = course_data['course_name']
    formatted_name = course_name.replace(' ', '_').replace('/', '-').replace('\\', '-')
    # Remove special characters except _ and -
    formatted_name = re.sub(r'[^a-zA-Z0-9_-]', '', formatted_name)

    print(f"formatted_course_name={formatted_name}")
    
    # Write to GITHUB_OUTPUT if available
    if 'GITHUB_OUTPUT' in os.environ:
        with open(os.environ['GITHUB_OUTPUT'], 'a') as f:
            f.write(f"formatted_course_name={formatted_name}\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validate_course.py <course_json_path>")
        sys.exit(1)
    validate_course_json(sys.argv[1])
