# Copyright (C) 2026 qBraid

import json
import os
import sys
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Set

from common import Config, setup_logging
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

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


class CertificateCriteria(BaseModel):
    """When a learner earns the certificate: a completion percentage or a
    points total, both of which the qBraid API accepts as `value >= 0`.

    Unknown keys are refused so a misspelled key fails validation instead of
    being dropped. `value` is strict: a string or a boolean is refused
    rather than coerced, and so are infinity and NaN."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["completion", "points"]
    value: float = Field(..., ge=0, strict=True, allow_inf_nan=False)


class CertificateSettings(BaseModel):
    """Per-course certificate settings, forwarded verbatim to the qBraid API.

    `templateId` picks the certificate design. The API's enum is the source
    of truth; this list mirrors it so a typo fails here with a field-level
    message instead of a 400 at deploy time. Omitted, the API keeps the
    template already stored for the course. A new course gets `quera` when
    it deploys to quera.com and its organization holds the quera grant,
    otherwise `qbraid`.

    Unknown keys are refused: `templateID` would otherwise be ignored and
    the course deployed with the default design. The validation error names
    the unknown key."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = Field(..., strict=True)
    criteria: Optional[CertificateCriteria] = None
    templateId: Optional[Literal["qbraid", "quera", "qct"]] = None


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
    # Author-declared course length in weeks, forwarded to the qBraid API,
    # which enforces the same 1-52 integer range. Optional: courses without
    # it keep the platform's chapter-count estimate. strict, because pydantic
    # would otherwise coerce "3" to 3 and forward a value the API rejects.
    durationWeeks: Optional[int] = Field(None, ge=1, le=52, strict=True)
    # Optional certificate settings, including the template. The API rejects
    # an explicit null here, so `to_payload` drops the key when absent.
    certificateSettings: Optional[CertificateSettings] = None

    def to_payload(self) -> Dict[str, Any]:
        """The deploy payload the API receives.

        `model_dump` alone would serialize an absent `certificateSettings` (and
        an absent `criteria` inside it) as null, which the API's validator
        refuses; those keys are dropped instead. `durationWeeks` stays as
        null on purpose: the API treats it as not declared.
        """
        payload = self.model_dump(mode="json")
        if self.certificateSettings is None:
            payload.pop("certificateSettings")
        else:
            payload["certificateSettings"] = self.certificateSettings.model_dump(
                mode="json", exclude_none=True
            )
        return payload

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

        # Save course data for next steps.
        try:
            with open(Config.COURSE_DATA_FILE_NAME, "w") as f:
                json.dump(course.to_payload(), f)
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
