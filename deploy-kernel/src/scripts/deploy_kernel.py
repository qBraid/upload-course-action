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

logger = logging.getLogger(__name__)
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


def write_github_output(key: str, value: str) -> None:
    """Write a key-value pair to GITHUB_OUTPUT."""
    if "GITHUB_OUTPUT" not in os.environ:
        return
    try:
        output_file = os.environ["GITHUB_OUTPUT"]
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


def _parse_status_response(response: requests.Response) -> tuple[Optional[str], Optional[str]]:
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
        if item.is_file() and item != dockerfile_path and item.name != ".gitignore":
            # Skip very large files (> 10MB)
            if item.stat().st_size > 10 * 1024 * 1024:
                logger.warning(f"Skipping large file: {item.name} ({item.stat().st_size} bytes)")
                continue
            context_files[item.name] = _encode_file(item)
            logger.info(f"  Including context file: {item.name}")

    return context_files


def deploy_kernel(
    api_key: str,
    dockerfile_path: str,
    kernel_name: str,
    language: str,
    display_name: str,
    context_dir: str,
    api_base_url: str,
) -> None:
    """Deploy a custom kernel to qBraid."""
    dockerfile = Path(dockerfile_path)
    if not dockerfile.exists():
        logger.error(f"Dockerfile not found: {dockerfile}")
        sys.exit(1)

    ctx_dir = Path(context_dir)

    # Encode Dockerfile
    logger.info(f"Encoding Dockerfile: {dockerfile}")
    dockerfile_b64 = _encode_file(dockerfile)

    # Collect context files
    logger.info(f"Collecting context files from: {ctx_dir}")
    context_files = _collect_context_files(ctx_dir, dockerfile)

    # Submit deploy request
    logger.info(f"Deploying kernel '{kernel_name}' ({language})...")
    headers = {
        "X-API-Key": api_key,
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
        resp = requests.post(url, headers=headers, json=payload, timeout=REQUEST_TIMEOUT_SECONDS)
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
    for attempt in range(1, MAX_POLL_ATTEMPTS + 1):
        logger.info(f"Polling build status (attempt {attempt}/{MAX_POLL_ATTEMPTS})...")
        time.sleep(POLL_INTERVAL_SECONDS)

        try:
            poll_resp = requests.get(poll_url, headers=headers, timeout=REQUEST_TIMEOUT_SECONDS)
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

    logger.error(f"Build timed out after {MAX_POLL_ATTEMPTS * POLL_INTERVAL_SECONDS} seconds")
    write_github_output("status", "timeout")
    sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deploy a custom kernel to qBraid")
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--dockerfile-path", required=True)
    parser.add_argument("--kernel-name", required=True)
    parser.add_argument("--language", required=True)
    parser.add_argument("--display-name", required=True)
    parser.add_argument("--context-dir", default=".")
    parser.add_argument("--api-base-url", default="https://api-v2.qbraid.com/api/v1")

    args = parser.parse_args()
    deploy_kernel(
        api_key=args.api_key,
        dockerfile_path=args.dockerfile_path,
        kernel_name=args.kernel_name,
        language=args.language,
        display_name=args.display_name,
        context_dir=args.context_dir,
        api_base_url=args.api_base_url,
    )
