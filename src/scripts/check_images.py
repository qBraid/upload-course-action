# Copyright (C) 2026 qBraid


import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

import nbformat
from common import Config, setup_logging

logger = setup_logging(__name__)


class ImageValidator:
    """Verifies that all images referenced in the course exist and are within the size limit."""

    def __init__(self):
        self.image_issues: List[Dict[str, Any]] = []
        self.max_size_bytes = Config.MAX_IMAGE_SIZE_MB * 1024 * 1024

    def check_notebook_images(self, notebook_path: str) -> None:
        """
        Check all image references in a notebook.

        Args:
            notebook_path (str): Path to the notebook file.
        """
        notebook_dir = os.path.dirname(notebook_path)
        if not notebook_dir:  # Handle case where notebook is in root directory
            notebook_dir = "."

        try:
            with open(notebook_path, "r", encoding="utf-8") as f:
                nb = nbformat.read(f, as_version=4)
        except Exception as e:
            logger.warning(f"Could not read notebook {notebook_path}: {e}")
            return

        images_to_check: List[str] = []

        for cell in nb.cells:
            if cell.cell_type == "markdown":
                # Find markdown image references: ![alt](path)
                md_images = re.findall(r"!\[.*?\]\((.*?)\)", cell.source)
                images_to_check.extend(md_images)

                # Find HTML img tags: <img src="path">
                html_images = re.findall(
                    r'<img[^>]+src=["\']([^"\']+)["\']', cell.source
                )
                images_to_check.extend(html_images)

        for img_ref in images_to_check:
            # Skip URLs
            if img_ref.startswith(("http://", "https://")):
                continue

            file_path_to_check: Path | None = None

            # Check absolute path from repo root
            if img_ref.startswith("/"):
                abs_path = img_ref[1:]  # Remove leading /
                if not os.path.exists(abs_path):
                    self.image_issues.append(
                        {
                            "notebook": notebook_path,
                            "image": img_ref,
                            "issue": "missing",
                            "type": "absolute",
                        }
                    )
                else:
                    file_path_to_check = Path(abs_path)

            else:
                # Check relative path from notebook directory
                rel_path = os.path.join(notebook_dir, img_ref)
                if not os.path.exists(rel_path):
                    self.image_issues.append(
                        {
                            "notebook": notebook_path,
                            "image": img_ref,
                            "issue": "missing",
                            "type": "relative",
                        }
                    )
                else:
                    file_path_to_check = Path(rel_path)

            if file_path_to_check:
                try:
                    size = file_path_to_check.stat().st_size
                    if size > self.max_size_bytes:
                        self.image_issues.append(
                            {
                                "notebook": notebook_path,
                                "image": img_ref,
                                "issue": "oversized",
                                "size": size,
                                "max_size": self.max_size_bytes,
                            }
                        )
                except OSError as e:
                    logger.warning(f"Could not check size of {file_path_to_check}: {e}")

    def run(self) -> None:
        """
        Executes the image verification process.
        """
        if not os.path.exists(Config.COURSE_DATA_FILE_NAME):
            logger.error(
                f"{Config.COURSE_DATA_FILE_NAME} not found. Run validation first."
            )
            sys.exit(1)

        try:
            with open(Config.COURSE_DATA_FILE_NAME, "r") as f:
                course_data = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load {Config.COURSE_DATA_FILE_NAME}: {e}")
            sys.exit(1)

        # Check all notebooks
        for chapter in course_data["content"]:
            file_path = chapter["baseFilePath"]
            self.check_notebook_images(file_path)

            if "sections" in chapter:
                for section in chapter["sections"]:
                    section_path = section["baseFilePath"]
                    self.check_notebook_images(section_path)

        if self.image_issues:
            logger.error("Found issues with image references:")
            for item in self.image_issues:
                if item["issue"] == "missing":
                    logger.error(f"  Notebook: {item['notebook']}")
                    logger.error(f"    Missing {item['type']} path: {item['image']}")
                elif item["issue"] == "oversized":
                    size_mb = item["size"] / (1024 * 1024)
                    max_mb = item["max_size"] / (1024 * 1024)
                    logger.error(f"  Notebook: {item['notebook']}")
                    logger.error(
                        f"    Image too large ({size_mb:.2f}MB > {max_mb:.0f}MB): {item['image']}"
                    )
            sys.exit(1)

        logger.info("✅ All image references in notebooks are valid")


if __name__ == "__main__":
    validator = ImageValidator()
    validator.run()
