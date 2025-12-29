import json
import sys
import os
import re


def check_file_size(file_path, context):
    limit_mb = 5  # 5MB limit
    limit_bytes = limit_mb * 1024 * 1024
    if os.path.exists(file_path):
        size = os.path.getsize(file_path)
        if size > limit_bytes:
            print(
                f"ERROR: {context} file '{file_path}' exceeds {limit_mb}MB limit ({size/1024/1024:.2f}MB)"
            )
            sys.exit(1)


def validate_course_json(course_file):
    if not os.path.exists(course_file):
        print(f"ERROR: {course_file} not found in repository root")
        sys.exit(1)

    with open(course_file, "r") as f:
        course_data = json.load(f)

    # Validate structure
    required_fields = [
        "courseName",
        "courseDescription",
        "visibility",
        "imageLink",
        "tags",
        "content",
        "deployedTo",
    ]
    for field in required_fields:
        if field not in course_data:
            print(f"ERROR: Missing required field: {field}")
            sys.exit(1)

    # Validate imageLink structure
    if not isinstance(course_data["imageLink"], dict):
        print("ERROR: 'imageLink' must be an object")
        sys.exit(1)
    if (
        "darkLogo" not in course_data["imageLink"]
        or "lightLogo" not in course_data["imageLink"]
    ):
        print("ERROR: 'imageLink' must contain 'darkLogo' and 'lightLogo'")
        sys.exit(1)

    # Validate content structure
    if not isinstance(course_data["content"], list):
        print("ERROR: 'content' must be a list of chapters")
        sys.exit(1)

    if not isinstance(course_data["deployedTo"], list):
        print("ERROR: 'deployedTo' must be a list")
        sys.exit(1)

    if len(course_data["deployedTo"]) == 0:
        print("ERROR: 'deployedTo' must contain at least one deployment target")
        sys.exit(1)

    valid_domains = {"qbraid.com", "quera.com"}
    for domain in course_data["deployedTo"]:
        if domain not in valid_domains:
            print(
                f"ERROR: Invalid domain '{domain}' in 'deployedTo'. Allowed domains are: {', '.join(valid_domains)}"
            )
            sys.exit(1)

    for idx, chapter in enumerate(course_data["content"]):
        required_chapter_fields = [
            "chapterName",
            "baseFilePath",
            "chapterNumber",
            "kernelName",
            "kernelId",
        ]
        for field in required_chapter_fields:
            if field not in chapter:
                print(f"ERROR: Chapter {idx} missing '{field}'")
                sys.exit(1)

        # Check chapter file size
        check_file_size(chapter["baseFilePath"], f"Chapter {idx}")

        # Check for sections if present
        if "sections" in chapter:
            if not isinstance(chapter["sections"], list):
                print(f"ERROR: Chapter {idx} 'sections' must be a list")
                sys.exit(1)
            for section_idx, section in enumerate(chapter["sections"]):
                required_section_fields = [
                    "sectionNumber",
                    "sectionName",
                    "baseFilePath",
                    "kernelName",
                    "kernelId",
                ]
                for field in required_section_fields:
                    if field not in section:
                        print(
                            f"ERROR: Chapter {idx}, Section {section_idx} missing '{field}'"
                        )
                        sys.exit(1)

                # Check section file size
                check_file_size(
                    section["baseFilePath"], f"Chapter {idx}, Section {section_idx}"
                )

    print("✅ course.json structure is valid")

    # Save course data for next steps
    with open("course_data.json", "w") as f:
        json.dump(course_data, f)

    course_name = course_data["courseName"]

    print(f"Course Name={course_name}")

    # Write to GITHUB_OUTPUT if available
    if "GITHUB_OUTPUT" in os.environ:
        with open(os.environ["GITHUB_OUTPUT"], "a") as f:
            f.write(f"course_name={course_name}\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python validate_course.py <course_json_path>")
        sys.exit(1)
    validate_course_json(sys.argv[1])
