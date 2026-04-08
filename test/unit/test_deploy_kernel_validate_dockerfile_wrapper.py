# Copyright (C) 2026 qBraid

import importlib.util
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).parent.parent.parent
SHARED_VALIDATOR_PATH = PROJECT_ROOT / "src" / "scripts" / "validate_dockerfile.py"
WRAPPER_VALIDATOR_PATH = (
    PROJECT_ROOT / "deploy-kernel" / "src" / "scripts" / "validate_dockerfile.py"
)


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    import sys

    sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    return module


@pytest.mark.unit
def test_deploy_kernel_validator_wrapper_uses_shared_implementation():
    shared_module = _load_module("shared_validator", SHARED_VALIDATOR_PATH)
    wrapper_module = _load_module("wrapper_validator", WRAPPER_VALIDATOR_PATH)

    result = wrapper_module.validate_dockerfile(
        'FROM python:3.11\nLABEL qbraid.kernel.name="bad-name"\n'
    )

    assert result.errors == shared_module.validate_dockerfile(
        'FROM python:3.11\nLABEL qbraid.kernel.name="bad-name"\n'
    ).errors
    assert (
        wrapper_module.KERNEL_NAME_PATTERN.pattern
        == shared_module.KERNEL_NAME_PATTERN.pattern
    )
