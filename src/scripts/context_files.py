# Copyright (C) 2026 qBraid

"""Single source of truth for what gets uploaded as Cloud Build context.

Both the deploy-kernel action's upload step and the Dockerfile validator
need to agree on the set of files that will end up in the tarball. Without
a shared listing, a validator that walks the raw filesystem would mismatch
the uploader's sensitive-file filter and produce false positives (or, the
other way around, false negatives that let a broken Dockerfile through).
"""

from __future__ import annotations

from pathlib import Path
from typing import Set

from common import setup_logging

logger = setup_logging(__name__)

MAX_CONTEXT_FILE_BYTES = 10 * 1024 * 1024

SKIPPED_CONTEXT_FILES = frozenset(
    {
        ".gitignore",
        ".dockerignore",
        ".env",
        ".env.local",
        ".env.production",
        ".env.staging",
        ".npmrc",
        ".pypirc",
        ".netrc",
        "id_rsa",
        "id_ed25519",
        "credentials",
    }
)
SKIPPED_CONTEXT_SUFFIXES = (".pem", ".key", ".p12", ".crt", ".kubeconfig")
SKIPPED_CONTEXT_SUBSTRINGS = ("secret", "token", "password", "credential")


def is_skipped_context_file(name: str) -> bool:
    """Return True for files we refuse to ship as build context.

    Matches three filters: explicit deny-list, sensitive suffixes, and
    sensitive substrings. Also skips dotfiles, which generally hold local
    config that should not enter a public image.
    """
    if name in SKIPPED_CONTEXT_FILES or name.startswith("."):
        return True
    lowered = name.lower()
    if lowered.endswith(SKIPPED_CONTEXT_SUFFIXES):
        return True
    return any(part in lowered for part in SKIPPED_CONTEXT_SUBSTRINGS)


def list_context_files(context_dir: Path, dockerfile_path: Path) -> Set[str]:
    """Names of files that will reach Cloud Build as build context.

    Mirrors the filter the uploader applies, so a preflight validator that
    consults this set sees exactly what `_collect_context_files` will ship.
    Reasons a file would be skipped (sensitive name, oversize) are logged
    once here; the uploader does not need to re-log them.
    """
    names: Set[str] = set()
    if not context_dir.is_dir():
        return names

    for item in context_dir.iterdir():
        if not item.is_file() or item == dockerfile_path:
            continue
        if is_skipped_context_file(item.name):
            logger.info("  Skipping sensitive context file: %s", item.name)
            continue
        if item.stat().st_size > MAX_CONTEXT_FILE_BYTES:
            logger.warning(
                "Skipping large file: %s (%d bytes)",
                item.name,
                item.stat().st_size,
            )
            continue
        names.add(item.name)
    return names
