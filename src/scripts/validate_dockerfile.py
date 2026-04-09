# Copyright (C) 2026 qBraid

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from common import setup_logging

logger = setup_logging(__name__)

KERNEL_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]{2,63}$")

SUPPORTED_LANGUAGES = frozenset(
    {"python", "cpp", "julia", "r", "rust", "go", "javascript"}
)

REQUIRED_LABELS = frozenset(
    {"qbraid.kernel.name", "qbraid.kernel.language", "qbraid.kernel.display_name"}
)


@dataclass
class DockerfileValidationResult:
    """Collects validation errors for a Dockerfile."""

    errors: List[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)


def _parse_labels(lines: List[str]) -> Dict[str, str]:
    """Extract LABEL directives from Dockerfile lines."""
    labels: Dict[str, str] = {}
    for line in lines:
        stripped = line.strip()
        if not stripped.upper().startswith("LABEL "):
            continue
        # Handle both LABEL key=value and LABEL key="value"
        content = stripped[6:].strip()
        # Split on whitespace for multi-label lines
        parts = re.findall(r'(\S+?)=("[^"]*"|\S+)', content)
        for key, value in parts:
            labels[key] = value.strip('"')
    return labels


def extract_dockerfile_labels(content: str) -> Dict[str, str]:
    """Extract LABEL directives from raw Dockerfile content."""
    return _parse_labels(_join_continuation_lines(content.splitlines()))


def _get_final_user(lines: List[str]) -> Optional[str]:
    """Get the last USER directive in the Dockerfile."""
    last_user = None
    for line in lines:
        stripped = line.strip()
        if stripped.upper().startswith("USER "):
            last_user = stripped[5:].strip()
    return last_user


def _has_expose_8888(lines: List[str]) -> bool:
    """Check if EXPOSE 8888 is present."""
    for line in lines:
        stripped = line.strip()
        if stripped.upper().startswith("EXPOSE "):
            ports = stripped[7:].strip().split()
            if "8888" in ports or "8888/tcp" in ports:
                return True
    return False


def _get_cmd_or_entrypoint(lines: List[str]) -> Optional[str]:
    """Get the last CMD or ENTRYPOINT directive."""
    last_cmd = None
    for line in lines:
        stripped = line.strip()
        upper = stripped.upper()
        if upper.startswith("CMD ") or upper.startswith("ENTRYPOINT "):
            last_cmd = stripped
    return last_cmd


def _has_kernel_json_copy(lines: List[str]) -> bool:
    """Check if kernel.json is being copied into the image."""
    for line in lines:
        stripped = line.strip()
        lowered = stripped.lower()
        upper = stripped.upper()
        if upper.startswith("COPY ") or upper.startswith("ADD "):
            if "kernel.json" in stripped:
                return True
        # Also check RUN commands that create kernel.json
        if upper.startswith("RUN "):
            if "kernel.json" in stripped and (
                "echo" in lowered
                or "cat" in lowered
                or "tee" in lowered
                or "kernelspec" in lowered
            ):
                return True
            if "ipykernel" in lowered and "install" in lowered:
                return True
    return False


def _has_privileged_flags(lines: List[str]) -> bool:
    """Check for privileged operation flags."""
    for line in lines:
        stripped = line.strip()
        if "--privileged" in stripped or "--cap-add=SYS_ADMIN" in stripped:
            return True
    return False


def _join_continuation_lines(raw_lines: List[str]) -> List[str]:
    """Join lines that end with backslash continuation."""
    joined: List[str] = []
    current = ""
    for line in raw_lines:
        stripped = line.rstrip()
        # Skip comments
        if stripped.lstrip().startswith("#"):
            continue
        if stripped.endswith("\\"):
            current += stripped[:-1] + " "
        else:
            current += stripped
            if current.strip():
                joined.append(current)
            current = ""
    if current.strip():
        joined.append(current)
    return joined


def validate_dockerfile(content: str) -> DockerfileValidationResult:
    """
    Validate a Dockerfile for qBraid kernel compatibility.

    Checks:
    1. Required LABEL directives (qbraid.kernel.name, language, display_name)
    2. EXPOSE 8888 present
    3. CMD/ENTRYPOINT references jupyter kernelgateway
    4. Final USER is not root
    5. No --privileged flags
    6. kernel.json is copied or created
    7. Kernel name matches naming pattern
    """
    result = DockerfileValidationResult()

    if not content.strip():
        result.add_error("Dockerfile is empty")
        return result

    raw_lines = content.splitlines()
    lines = _join_continuation_lines(raw_lines)

    if not lines:
        result.add_error("Dockerfile contains no instructions")
        return result

    # 1. Check required LABEL directives
    labels = _parse_labels(lines)
    for required_label in REQUIRED_LABELS:
        if required_label not in labels:
            result.add_error(f"Missing required LABEL: {required_label}")

    # 1a. Validate kernel name format
    kernel_name = labels.get("qbraid.kernel.name", "")
    if kernel_name and not KERNEL_NAME_PATTERN.match(kernel_name):
        result.add_error(
            f'LABEL qbraid.kernel.name "{kernel_name}" is invalid. '
            "Must start with a lowercase letter and contain only lowercase letters, "
            "digits, and underscores (3-64 chars)"
        )

    # 1b. Validate language
    language = labels.get("qbraid.kernel.language", "")
    if language and language not in SUPPORTED_LANGUAGES:
        result.add_error(
            f'LABEL qbraid.kernel.language "{language}" is not supported. '
            f"Supported: {', '.join(sorted(SUPPORTED_LANGUAGES))}"
        )

    # 1c. Validate display name is non-empty
    display_name = labels.get("qbraid.kernel.display_name", "")
    if "qbraid.kernel.display_name" in labels and not display_name:
        result.add_error("LABEL qbraid.kernel.display_name cannot be empty")

    # 2. Check EXPOSE 8888
    if not _has_expose_8888(lines):
        result.add_error("Missing EXPOSE 8888 (required for kernel gateway)")

    # 3. Check CMD/ENTRYPOINT references jupyter kernelgateway
    cmd = _get_cmd_or_entrypoint(lines)
    if cmd is None:
        result.add_error(
            "Missing CMD or ENTRYPOINT. Must reference 'jupyter kernelgateway'"
        )
    elif "kernelgateway" not in cmd.lower() and "kernel_gateway" not in cmd.lower():
        result.add_error(
            "CMD/ENTRYPOINT must reference 'jupyter kernelgateway'. " f"Found: {cmd}"
        )

    # 4. Final USER must not be root
    final_user = _get_final_user(lines)
    if final_user and final_user.lower() in ("root", "0"):
        result.add_error("Final USER directive must not be root (security requirement)")

    # 5. No privileged flags
    if _has_privileged_flags(lines):
        result.add_error("Dockerfile must not use --privileged or --cap-add=SYS_ADMIN")

    # 6. kernel.json must be copied or created
    if not _has_kernel_json_copy(lines):
        result.add_error(
            "kernel.json must be COPY'd, ADD'd, or created via RUN in the Dockerfile. "
            "It should be placed under /usr/local/share/jupyter/kernels/<name>/"
        )

    return result


def validate_dockerfile_file(dockerfile_path: str) -> None:
    """
    Validate a Dockerfile from a file path.
    Exits with code 1 on validation failure.
    """
    path = Path(dockerfile_path)
    if not path.exists():
        logger.error(f"Dockerfile not found: {path}")
        sys.exit(1)

    content = path.read_text()
    result = validate_dockerfile(content)

    if not result.is_valid:
        logger.error("Dockerfile validation failed:")
        for error in result.errors:
            logger.error(f"  - {error}")
        sys.exit(1)

    logger.info("Dockerfile validation passed")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        logger.error("Usage: python validate_dockerfile.py <dockerfile_path>")
        sys.exit(1)
    validate_dockerfile_file(sys.argv[1])
