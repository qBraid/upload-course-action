# Copyright (C) 2026 qBraid

import argparse
import base64
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, Optional

import requests
from validate_dockerfile import (
    SUPPORTED_LANGUAGES,
    extract_dockerfile_labels,
    KERNEL_NAME_PATTERN,
)

logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

MAX_POLL_ATTEMPTS = 60
POLL_INTERVAL_SECONDS = 30
REQUEST_TIMEOUT_SECONDS = 30
KERNEL_ALREADY_EXISTS_CODE = "KERNEL_ALREADY_EXISTS"
FATAL_POLL_STATUS_CODES = {400, 401, 403, 404}
DEFAULT_TIMEOUT_SECONDS = 1800
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


def write_github_output(key: str, value: str) -> None:
    """Safely write a key-value pair to GITHUB_OUTPUT."""
    if "GITHUB_OUTPUT" not in os.environ:
        return
    try:
        output_file = os.environ["GITHUB_OUTPUT"]
        if "\n" in value:
            delimiter = f"GITHUB_OUTPUT_DELIMITER_{key.upper()}"
            while delimiter in value:
                delimiter = f"{delimiter}_ALT"
            with open(output_file, "a") as f:
                f.write(f"{key}<<{delimiter}\n")
                f.write(value)
                if not value.endswith("\n"):
                    f.write("\n")
                f.write(f"{delimiter}\n")
            return

        with open(output_file, "a") as f:
            f.write(f"{key}={value}\n")
    except (IOError, OSError) as e:
        logger.warning(f"Failed to write to GITHUB_OUTPUT: {e}")


def _encode_file(path: Path) -> str:
    """Base64-encode a file."""
    return base64.b64encode(path.read_bytes()).decode("utf-8")


def _parse_error_response(response: requests.Response) -> tuple[Optional[str], str]:
    """Extract a stable error code/message pair from qBraid API error responses."""
    try:
        payload = response.json()
    except ValueError:
        return None, response.text

    error = payload.get("error", payload)
    error_code = error.get("code") if isinstance(error, dict) else None
    message = error.get("message") if isinstance(error, dict) else response.text
    return error_code, message or response.text


def _parse_status_response(
    response: requests.Response,
) -> tuple[Optional[str], Optional[str]]:
    """Extract a stable status/error pair from a deploy status response."""
    try:
        payload = response.json()
    except ValueError:
        return None, response.text

    data = payload.get("data", payload)
    if not isinstance(data, dict):
        return None, response.text

    status = data.get("status")
    error = data.get("error")
    return status, error if isinstance(error, str) else None


def _collect_context_files(context_dir: Path, dockerfile_path: Path) -> Dict[str, str]:
    """Collect and base64-encode context files from the context directory."""
    context_files = {}
    if not context_dir.is_dir():
        return context_files

    for item in context_dir.iterdir():
        if not item.is_file() or item == dockerfile_path:
            continue

        item_name = item.name
        lowered_name = item_name.lower()
        if (
            item_name in SKIPPED_CONTEXT_FILES
            or item_name.startswith(".")
            or lowered_name.endswith(SKIPPED_CONTEXT_SUFFIXES)
            or any(part in lowered_name for part in SKIPPED_CONTEXT_SUBSTRINGS)
        ):
            logger.info(f"  Skipping sensitive context file: {item_name}")
            continue

        # Skip very large files (> 10MB)
        if item.stat().st_size > 10 * 1024 * 1024:
            logger.warning(
                f"Skipping large file: {item.name} ({item.stat().st_size} bytes)"
            )
            continue
        context_files[item.name] = _encode_file(item)
        logger.info(f"  Including context file: {item.name}")

    return context_files


def _validate_deploy_inputs(kernel_name: str, language: str, display_name: str) -> None:
    if not KERNEL_NAME_PATTERN.match(kernel_name):
        logger.error(
            "Invalid kernel name '%s'. Use lowercase letters, digits, and underscores (3-64 chars, starting with a letter).",
            kernel_name,
        )
        sys.exit(1)

    if language not in SUPPORTED_LANGUAGES:
        logger.error(
            "Unsupported kernel language '%s'. Supported values: %s",
            language,
            ", ".join(sorted(SUPPORTED_LANGUAGES)),
        )
        sys.exit(1)

    if not display_name.strip():
        logger.error("Display name must not be empty")
        sys.exit(1)


def _validate_dockerfile_labels(
    dockerfile_content: str,
    kernel_name: str,
    language: str,
    display_name: str,
) -> None:
    labels = extract_dockerfile_labels(dockerfile_content)
    expected_labels = {
        "qbraid.kernel.name": kernel_name,
        "qbraid.kernel.language": language,
        "qbraid.kernel.display_name": display_name,
    }

    for label_key, expected_value in expected_labels.items():
        actual_value = labels.get(label_key)
        if actual_value is None:
            continue
        if actual_value != expected_value:
            logger.error(
                "Dockerfile label %s=%r does not match action input %r",
                label_key,
                actual_value,
                expected_value,
            )
            sys.exit(1)


def deploy_kernel(
    dockerfile_path: str,
    kernel_name: str,
    language: str,
    display_name: str,
    context_dir: str,
    api_base_url: str,
    api_key: Optional[str] = None,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> None:
    """Deploy a custom kernel to qBraid."""
    dockerfile = Path(dockerfile_path)
    if not dockerfile.exists():
        logger.error(f"Dockerfile not found: {dockerfile}")
        sys.exit(1)

    resolved_api_key = api_key or os.getenv("QBRAID_API_KEY", "").strip()
    if not resolved_api_key:
        logger.error("Missing qBraid API key. Set QBRAID_API_KEY or pass --api-key.")
        sys.exit(1)

    _validate_deploy_inputs(kernel_name, language, display_name)

    ctx_dir = Path(context_dir)

    # Encode Dockerfile
    logger.info(f"Encoding Dockerfile: {dockerfile}")
    dockerfile_content = dockerfile.read_text()
    _validate_dockerfile_labels(dockerfile_content, kernel_name, language, display_name)
    dockerfile_b64 = base64.b64encode(dockerfile_content.encode("utf-8")).decode(
        "utf-8"
    )

    # Collect context files
    logger.info(f"Collecting context files from: {ctx_dir}")
    context_files = _collect_context_files(ctx_dir, dockerfile)

    # Submit deploy request
    logger.info(f"Deploying kernel '{kernel_name}' ({language})...")
    headers = {
        "X-API-Key": resolved_api_key,
        "Content-Type": "application/json",
    }
    payload = {
        "kernelName": kernel_name,
        "language": language,
        "displayName": display_name,
        "dockerfile": dockerfile_b64,
    }
    if context_files:
        payload["contextFiles"] = context_files

    url = f"{api_base_url}/kernels/deploy"
    try:
        resp = requests.post(
            url, headers=headers, json=payload, timeout=REQUEST_TIMEOUT_SECONDS
        )
    except requests.RequestException as e:
        logger.error(f"Failed to submit deploy request: {e}")
        sys.exit(1)

    if resp.status_code not in (200, 201):
        error_code, error_message = _parse_error_response(resp)
        if error_code == KERNEL_ALREADY_EXISTS_CODE:
            logger.info(
                "Kernel '%s' already exists and is active; treating deploy as successful.",
                kernel_name,
            )
            write_github_output("kernel-name", kernel_name)
            write_github_output("status", "active")
            return

        logger.error(f"Deploy request failed: {resp.status_code} {error_message}")
        sys.exit(1)

    resp_data = resp.json()
    data = resp_data.get("data", resp_data)
    build_id = data.get("buildId")
    if not build_id:
        logger.error("No build ID returned from API")
        sys.exit(1)

    logger.info(f"Build submitted. Build ID: {build_id}")
    write_github_output("build-id", build_id)
    write_github_output("kernel-name", kernel_name)

    # Poll for completion
    poll_url = f"{api_base_url}/kernels/deploy/{build_id}"
    deadline = time.monotonic() + timeout_seconds
    for attempt in range(1, MAX_POLL_ATTEMPTS + 1):
        logger.info(f"Polling build status (attempt {attempt}/{MAX_POLL_ATTEMPTS})...")

        try:
            poll_resp = requests.get(
                poll_url, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS
            )
        except requests.RequestException as e:
            logger.warning(f"Poll request failed: {e}")
            continue

        if poll_resp.status_code != 200:
            error_code, error_message = _parse_error_response(poll_resp)
            log_message = (
                f"Poll returned {poll_resp.status_code}"
                f"{f' ({error_code})' if error_code else ''}: {error_message}"
            )
            if poll_resp.status_code in FATAL_POLL_STATUS_CODES:
                logger.error(log_message)
                write_github_output("status", "failed")
                sys.exit(1)
            logger.warning(log_message)
            continue

        status, error = _parse_status_response(poll_resp)
        if not status:
            logger.warning("Poll returned 200 without a readable build status")
            continue
        logger.info(f"Build status: {status}")

        if status == "active":
            logger.info(f"Kernel '{kernel_name}' deployed successfully!")
            write_github_output("status", "active")
            status_data = poll_resp.json().get("data", poll_resp.json())
            image_uri = status_data.get("imageUri", "")
            if image_uri:
                write_github_output("image-uri", image_uri)
            return

        if status == "failed":
            logger.error(f"Kernel build failed: {error or 'Unknown error'}")
            write_github_output("status", "failed")
            sys.exit(1)

        if time.monotonic() >= deadline:
            break

        time.sleep(POLL_INTERVAL_SECONDS)

    logger.error(f"Build timed out after {timeout_seconds} seconds")
    write_github_output("status", "timeout")
    sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deploy a custom kernel to qBraid")
    parser.add_argument("--api-key")
    parser.add_argument("--dockerfile-path", required=True)
    parser.add_argument("--kernel-name", required=True)
    parser.add_argument("--language", required=True)
    parser.add_argument("--display-name", required=True)
    parser.add_argument("--context-dir", default=".")
    parser.add_argument("--api-base-url", default="https://api-v2.qbraid.com/api/v1")
    parser.add_argument("--timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS)

    args = parser.parse_args()
    deploy_kernel(
        dockerfile_path=args.dockerfile_path,
        kernel_name=args.kernel_name,
        language=args.language,
        display_name=args.display_name,
        context_dir=args.context_dir,
        api_base_url=args.api_base_url,
        api_key=args.api_key,
        timeout_seconds=args.timeout_seconds,
    )
