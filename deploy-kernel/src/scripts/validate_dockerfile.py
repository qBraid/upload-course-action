"""Delegate deploy-kernel Dockerfile validation to the shared validator."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_shared_validator_module():
    repo_root = Path(__file__).resolve().parents[3]
    shared_validator_path = repo_root / "src" / "scripts" / "validate_dockerfile.py"

    spec = importlib.util.spec_from_file_location(
        "shared_validate_dockerfile", shared_validator_path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load shared validator from {shared_validator_path}")

    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(shared_validator_path.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    return module


_shared_validator = _load_shared_validator_module()

DockerfileValidationResult = _shared_validator.DockerfileValidationResult
KERNEL_NAME_PATTERN = _shared_validator.KERNEL_NAME_PATTERN
SUPPORTED_LANGUAGES = _shared_validator.SUPPORTED_LANGUAGES
REQUIRED_LABELS = _shared_validator.REQUIRED_LABELS
extract_dockerfile_labels = _shared_validator.extract_dockerfile_labels
validate_dockerfile = _shared_validator.validate_dockerfile
validate_dockerfile_file = _shared_validator.validate_dockerfile_file


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(
            "Usage: python validate_dockerfile.py <dockerfile_path> [<context_dir>]",
            file=sys.stderr,
        )
        sys.exit(1)
    ctx = sys.argv[2] if len(sys.argv) >= 3 else None
    validate_dockerfile_file(sys.argv[1], ctx)
