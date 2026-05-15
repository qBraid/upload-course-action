# Copyright (C) 2026 qBraid

import json
import os
import sys
import urllib.request
from pathlib import Path
from typing import List, Optional, Set

from common import Config, setup_logging
from pydantic import BaseModel, Field, ValidationError, field_validator

logger = setup_logging(__name__)

MAX_KERNEL_NAME_SAMPLE = 10


def _fetch_available_kernels(catalog_url: str) -> Optional[Set[str]]:
    """Fetch the available kernel names from the configured catalog."""
    try:
        with urllib.request.urlopen(catalog_url, timeout=10) as resp:
            catalog = json.loads(resp.read().decode())
    except Exception:
        logger.warning("Could not fetch kernel catalog from %s", catalog_url)
        return None

    kernels = set(catalog.get("kernels", {}).keys())
    if not kernels:
        logger.warning("Kernel catalog at %s is empty", catalog_url)
        return None
    return kernels


def _format_missing_kernel_error(
    kernel_name: str, catalog_url: str, available_kernels: Set[str]
) -> str:
    """Build a concise missing-kernel error without dumping the full catalog."""
    sample = ", ".join(sorted(available_kernels)[:MAX_KERNEL_NAME_SAMPLE])
    suffix = "" if len(available_kernels) <= MAX_KERNEL_NAME_SAMPLE else ", ..."
    return (
        f"Kernel '{kernel_name}' not found in catalog at {catalog_url}. "
        f"Catalog contains {len(available_kernels)} kernels. Sample: [{sample}{suffix}]"
    )


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

    @field_validator("content")
    @classmethod
    def check_kernel_references(cls, chapters: List["Chapter"]) -> List["Chapter"]:
        """Validate kernel references when a catalog URL is explicitly configured."""
        catalog_url = os.environ.get("KERNEL_CATALOG_URL")
        if not catalog_url:
            return chapters

        available_kernels = _fetch_available_kernels(catalog_url)
        if not available_kernels:
            logger.warning("Skipping kernel name validation")
            return chapters

        for chapter in chapters:
            if chapter.kernelName not in available_kernels:
                raise ValueError(
                    _format_missing_kernel_error(
                        chapter.kernelName, catalog_url, available_kernels
                    )
                )
            for section in chapter.sections or []:
                if section.kernelName not in available_kernels:
                    raise ValueError(
                        _format_missing_kernel_error(
                            section.kernelName, catalog_url, available_kernels
                        )
                    )
        return chapters


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
                loc = " -> ".join(str(location) for location in error["loc"])
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

        from common import write_github_output

        write_github_output("course_name", str(course_name))


def validate_course_json(course_file: str):
    validator = CourseValidator(course_file)
    validator.validate()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        logger.error("Usage: python validate_course.py <course_json_path>")
        sys.exit(1)
    validate_course_json(sys.argv[1])
