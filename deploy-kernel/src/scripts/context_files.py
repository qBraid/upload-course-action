"""Delegate to the shared context-files helper (single source of truth)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_shared_context_files_module():
    repo_root = Path(__file__).resolve().parents[3]
    shared_path = repo_root / "src" / "scripts" / "context_files.py"

    spec = importlib.util.spec_from_file_location(
        "shared_context_files", shared_path
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load shared context_files from {shared_path}")

    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(shared_path.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        sys.path.pop(0)
    return module


_shared = _load_shared_context_files_module()

MAX_CONTEXT_FILE_BYTES = _shared.MAX_CONTEXT_FILE_BYTES
SKIPPED_CONTEXT_FILES = _shared.SKIPPED_CONTEXT_FILES
SKIPPED_CONTEXT_SUFFIXES = _shared.SKIPPED_CONTEXT_SUFFIXES
SKIPPED_CONTEXT_SUBSTRINGS = _shared.SKIPPED_CONTEXT_SUBSTRINGS
is_skipped_context_file = _shared.is_skipped_context_file
list_context_files = _shared.list_context_files
