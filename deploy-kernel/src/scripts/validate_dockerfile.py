# Copyright (C) 2026 qBraid
# Symlink / copy of upload-course-action/src/scripts/validate_dockerfile.py
# This file re-exports the Dockerfile validation for use in the deploy-kernel-action.

import logging
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S"
)
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

KERNEL_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9_]{2,63}$")

SUPPORTED_LANGUAGES = frozenset(
    {"python", "cpp", "julia", "r", "rust", "go", "javascript"}
)

REQUIRED_LABELS = frozenset(
    {"qbraid.kernel.name", "qbraid.kernel.language", "qbraid.kernel.display_name"}
)


@dataclass
class DockerfileValidationResult:
    errors: List[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)


def _parse_labels(lines: List[str]) -> Dict[str, str]:
    labels: Dict[str, str] = {}
    for line in lines:
        stripped = line.strip()
        if not stripped.upper().startswith("LABEL "):
            continue
        content = stripped[6:].strip()
        parts = re.findall(r'(\S+?)=("[^"]*"|\S+)', content)
        for key, value in parts:
            labels[key] = value.strip('"')
    return labels


def _join_continuation_lines(raw_lines: List[str]) -> List[str]:
    joined: List[str] = []
    current = ""
    for line in raw_lines:
        stripped = line.rstrip()
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
    result = DockerfileValidationResult()

    if not content.strip():
        result.add_error("Dockerfile is empty")
        return result

    raw_lines = content.splitlines()
    lines = _join_continuation_lines(raw_lines)

    if not lines:
        result.add_error("Dockerfile contains no instructions")
        return result

    labels = _parse_labels(lines)
    for required_label in REQUIRED_LABELS:
        if required_label not in labels:
            result.add_error(f"Missing required LABEL: {required_label}")

    kernel_name = labels.get("qbraid.kernel.name", "")
    if kernel_name and not KERNEL_NAME_PATTERN.match(kernel_name):
        result.add_error(
            f'LABEL qbraid.kernel.name "{kernel_name}" is invalid. '
            "Must start with lowercase letter, contain only lowercase letters, digits, underscores (3-64 chars)"
        )

    language = labels.get("qbraid.kernel.language", "")
    if language and language not in SUPPORTED_LANGUAGES:
        result.add_error(
            f'LABEL qbraid.kernel.language "{language}" not supported. '
            f"Supported: {', '.join(sorted(SUPPORTED_LANGUAGES))}"
        )

    display_name = labels.get("qbraid.kernel.display_name", "")
    if "qbraid.kernel.display_name" in labels and not display_name:
        result.add_error("LABEL qbraid.kernel.display_name cannot be empty")

    has_expose = any(
        line.strip().upper().startswith("EXPOSE ")
        and ("8888" in line.strip().split())
        for line in lines
    )
    if not has_expose:
        result.add_error("Missing EXPOSE 8888 (required for kernel gateway)")

    last_cmd = None
    for line in lines:
        upper = line.strip().upper()
        if upper.startswith("CMD ") or upper.startswith("ENTRYPOINT "):
            last_cmd = line.strip()
    if last_cmd is None:
        result.add_error("Missing CMD or ENTRYPOINT. Must reference 'jupyter kernelgateway'")
    elif "kernelgateway" not in last_cmd.lower() and "kernel_gateway" not in last_cmd.lower():
        result.add_error(f"CMD/ENTRYPOINT must reference 'jupyter kernelgateway'. Found: {last_cmd}")

    last_user = None
    for line in lines:
        if line.strip().upper().startswith("USER "):
            last_user = line.strip()[5:].strip()
    if last_user and last_user.lower() in ("root", "0"):
        result.add_error("Final USER directive must not be root (security requirement)")

    has_privileged = any("--privileged" in line or "--cap-add=SYS_ADMIN" in line for line in lines)
    if has_privileged:
        result.add_error("Dockerfile must not use --privileged or --cap-add=SYS_ADMIN")

    has_kernel_json = any(
        (
            (line.strip().upper().startswith("COPY ") or line.strip().upper().startswith("ADD "))
            and "kernel.json" in line
        )
        or (
            line.strip().upper().startswith("RUN ")
            and "kernel.json" in line
            and any(kw in line.lower() for kw in ("echo", "cat", "tee", "kernelspec"))
        )
        for line in lines
    )
    if not has_kernel_json:
        result.add_error(
            "kernel.json must be COPY'd, ADD'd, or created via RUN in the Dockerfile"
        )

    return result


def validate_dockerfile_file(dockerfile_path: str) -> None:
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
