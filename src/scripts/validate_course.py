import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

from common import Config
from common import ValidationError as ActionValidationError
from common import setup_logging
from pydantic import BaseModel, Field, ValidationError, field_validator

logger = setup_logging(__name__)


class ImageLink(BaseModel):
    """Model for image links."""

    darkLogo: str
    lightLogo: str


class Section(BaseModel):
    """Model for course sections."""

    sectionNumber: float
    sectionName: str
    baseFilePath: Path
    kernelName: str
    kernelId: str

    @field_validator("baseFilePath")
    @classmethod
    def check_file(cls, v: Path) -> Path:
        if not v.exists():
            raise ValueError(f"File not found: {v}")

        size_bytes = v.stat().st_size
        max_bytes = Config.MAX_NOTEBOOK_SIZE_MB * 1024 * 1024
        if size_bytes > max_bytes:
            raise ValueError(
                f"File {v} exceeds {Config.MAX_NOTEBOOK_SIZE_MB}MB limit "
                f"({size_bytes/1024/1024:.2f}MB)"
            )
        return v


class Chapter(BaseModel):
    """Model for course chapters."""

    chapterName: str
    chapterFileName: str
    baseFilePath: Path
    chapterNumber: float
    kernelName: str
    kernelId: str
    sections: Optional[List[Section]] = []

    @field_validator("baseFilePath")
    @classmethod
    def check_file(cls, v: Path) -> Path:
        if not v.exists():
            raise ValueError(f"File not found: {v}")

        size_bytes = v.stat().st_size
        max_bytes = Config.MAX_NOTEBOOK_SIZE_MB * 1024 * 1024
        if size_bytes > max_bytes:
            raise ValueError(
                f"File {v} exceeds {Config.MAX_NOTEBOOK_SIZE_MB}MB limit "
                f"({size_bytes/1024/1024:.2f}MB)"
            )
        return v


class Course(BaseModel):
    """Model for course configuration."""

    courseName: str
    courseDescription: str
    visibility: str
    imageLink: ImageLink
    tags: List[str]
    content: List[Chapter]
    deployedTo: List[str] = Field(..., min_length=1)

    @field_validator("deployedTo")
    @classmethod
    def check_domains(cls, v: List[str]) -> List[str]:
        invalid = [d for d in v if d not in Config.VALID_DOMAINS]
        if invalid:
            raise ValueError(
                f"Invalid domains: {set(invalid)}. Allowed: {Config.VALID_DOMAINS}"
            )
        return v


class CourseValidator:
    """Validates the course.json structure and file sizes."""

    def __init__(self, course_file: str):
        self.course_file = Path(course_file)

    def validate(self) -> None:
        """
        Executes the validation process.
        Raises:
            SystemExit: If validation fails.
        """
        if not self.course_file.exists():
            logger.error(f"{self.course_file} not found in repository root")
            sys.exit(1)

        try:
            with open(self.course_file, "r") as f:
                course_data = json.load(f)

            # Validate structure using Pydantic
            course = Course(**course_data)

        except ValidationError as e:
            logger.error("Validation failed for course.json")
            for error in e.errors():
                loc = " -> ".join(str(l) for l in error["loc"])
                logger.error(f"  Field: {loc}")
                logger.error(f"  Error: {error['msg']}")
            sys.exit(1)
        except json.JSONDecodeError:
            logger.error(f"{self.course_file} is not a valid JSON file")
            sys.exit(1)
        except Exception as e:
            logger.error(f"Unexpected error validating course: {e}")
            sys.exit(1)

        logger.info("✅ course.json structure and file sizes are valid")

        # Save course data for next steps
        try:
            with open(Config.COURSE_DATA_FILE_NAME, "w") as f:
                json.dump(course.model_dump(mode="json"), f)
        except IOError as e:
            logger.error(f"Failed to write {Config.COURSE_DATA_FILE_NAME}: {e}")
            sys.exit(1)

        course_name = course.courseName
        logger.info(f"Course Name={course_name}")

        if "GITHUB_OUTPUT" in os.environ:
            try:
                with open(os.environ["GITHUB_OUTPUT"], "a") as f:
                    f.write(f"course_name={course_name}\n")
            except IOError as e:
                logger.warning(f"Failed to write to GITHUB_OUTPUT: {e}")


def validate_course_json(course_file: str):
    validator = CourseValidator(course_file)
    validator.validate()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        logger.error("Usage: python validate_course.py <course_json_path>")
        sys.exit(1)
    validate_course_json(sys.argv[1])
