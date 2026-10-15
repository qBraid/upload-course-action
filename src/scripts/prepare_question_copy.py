# Copyright (C) 2026 qBraid

"""Apply a saved MCP copy result to a destination course checkout before a PR."""

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, field_validator

MARKERS = {"mcq": "MultipleChoiceQuestion", "frq": "FreeResponseQuestion"}
PATTERNS = {
    kind: re.compile(rf"{marker}\(\s*(['\"])([^'\"]+)\1\s*\)")
    for kind, marker in MARKERS.items()
}
CUSTOM_ID = r"^[\w.\-:]{10,200}$"


class CopiedQuestion(BaseModel):
    """The reference mapping returned by copy_qbook_questions."""

    sourceCustomId: str = Field(pattern=CUSTOM_ID)
    customId: str = Field(pattern=CUSTOM_ID)
    type: Literal["mcq", "frq"]


class CopyResult(BaseModel):
    """A saved, successful MCP result or the data from the REST response."""

    questions: list[CopiedQuestion] = Field(min_length=1, max_length=100)

    @field_validator("questions")
    @classmethod
    def unique_mapping(cls, questions: list[CopiedQuestion]) -> list[CopiedQuestion]:
        """Reject ambiguous mappings so applying the result twice is safe."""
        sources = [question.sourceCustomId for question in questions]
        targets = [question.customId for question in questions]
        if len(set(sources)) != len(sources) or len(set(targets)) != len(targets):
            raise ValueError("Source and destination customIds must each be unique")
        if set(sources) & set(targets):
            raise ValueError("Source and destination customIds must not overlap")
        return questions


def repository_path(root: Path, path: str) -> Path:
    """Resolve an existing file without allowing writes outside the checkout."""
    resolved = (root / path).resolve(strict=True)
    if not resolved.is_relative_to(root):
        raise ValueError(f"Path is outside the destination repository: {path}")
    if not resolved.is_file():
        raise ValueError(f"Expected a file: {path}")
    return resolved


def rewrite_notebook(
    notebook: dict, questions: list[CopiedQuestion]
) -> tuple[dict, set]:
    """Rewrite widget arguments and derive the processor's placement lists.

    The processor records one widget per type per cell and numbers repeated
    placements within each file. Refuse extra widgets instead of silently losing
    a reference when the course is deployed.
    """
    mapping = {
        kind: {q.sourceCustomId: q.customId for q in questions if q.type == kind}
        for kind in MARKERS
    }
    targets = {
        kind: {q.customId for q in questions if q.type == kind} for kind in MARKERS
    }
    references = {"MCQ": [], "FRQ": []}
    seen = set()
    counts = {kind: Counter() for kind in MARKERS}
    for cell in notebook["cells"]:
        source = cell["source"]
        text = "".join(source) if isinstance(source, list) else source
        original_text = text
        for kind, pattern in PATTERNS.items():
            if len(list(pattern.finditer(text))) > 1:
                raise ValueError(
                    f"Put each {MARKERS[kind]} in a separate notebook cell"
                )

            def replace(match, question_type=kind):
                old = match.group(2)
                new = mapping[question_type].get(old, old)
                if new in targets[question_type]:
                    seen.add((question_type, new))
                occurrence = counts[question_type][new]
                counts[question_type][new] += 1
                references[question_type.upper()].append(f"{new}:{occurrence}")
                # Preserve quote style, whitespace, and surrounding source.
                start = match.start(2) - match.start()
                end = match.end(2) - match.start()
                return match.group(0)[:start] + new + match.group(0)[end:]

            text = pattern.sub(replace, text)
        if text != original_text:
            cell["source"] = (
                text.splitlines(keepends=True) if isinstance(source, list) else text
            )
    return references, seen


def prepare_copy(
    root: Path, course_json: str, mapping_file: str, *, write: bool = False
) -> list[str]:
    """Validate all changes before writing; reuse the saved mapping on retry.

    Notebook paths are relative to the repository root, matching the upload
    Action. This command neither copies backend records nor deploys a course.
    """
    root = root.resolve()
    course_path = repository_path(root, course_json)
    mapping_path = repository_path(root, mapping_file)
    saved = json.loads(mapping_path.read_text(encoding="utf-8"))
    result = CopyResult.model_validate(saved.get("data", saved))
    original_course = json.loads(course_path.read_text(encoding="utf-8"))
    course = json.loads(json.dumps(original_course))
    pending = {}
    seen = set()
    notebooks = {}
    for chapter in course["content"]:
        items = [(chapter, "chapterQuestions")]
        items.extend(
            (section, "sectionQuestions") for section in chapter.get("sections") or []
        )
        for item, field in items:
            notebook_path = repository_path(root, item["baseFilePath"])
            if notebook_path not in notebooks:
                original = json.loads(notebook_path.read_text(encoding="utf-8"))
                notebook = json.loads(json.dumps(original))
                references, used = rewrite_notebook(notebook, result.questions)
                notebooks[notebook_path] = references
                seen.update(used)
                if notebook != original:
                    pending[notebook_path] = notebook
            # This operation owns MCQ and FRQ; retain any CQ references.
            item[field] = {**(item.get(field) or {}), **notebooks[notebook_path]}
    unused = {(q.type, q.customId) for q in result.questions} - seen
    if unused:
        raise ValueError(
            "Copied questions are missing from the destination notebooks: "
            + ", ".join(sorted(custom_id for _, custom_id in unused))
        )
    if course != original_course:
        pending[course_path] = course
    if write:
        for path, document in pending.items():
            path.write_text(
                json.dumps(document, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
    return [str(path.relative_to(root)) for path in pending]


def main() -> None:
    """Preview changes by default; write or check them only when requested."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--course-json", default="course.json")
    parser.add_argument(
        "--mapping",
        required=True,
        help="Saved MCP result or REST response, without credentials",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--write", action="store_true", help="Update notebooks and course.json"
    )
    mode.add_argument(
        "--check",
        action="store_true",
        help="Fail if notebooks or course.json still need changes",
    )
    args = parser.parse_args()
    try:
        changed = prepare_copy(
            Path.cwd(), args.course_json, args.mapping, write=args.write
        )
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.exit(2, f"Cannot prepare question copy: {error}\n")
    print(
        json.dumps({"files": changed, "written": args.write, "courseDeployed": False})
    )
    if args.check and changed:
        parser.exit(
            1, "Apply the saved mapping with --write and commit the changed files.\n"
        )


if __name__ == "__main__":
    main()
