"""Exercise the saved MCP mapping through notebook edits and Action payloads."""

import json
import subprocess
import sys
from pathlib import Path

import nbformat
import pytest
from common import Config
from create_course import CourseCreator
from prepare_question_copy import prepare_copy
from update_course import CourseUpdater
from validate_course import Course, validate_course_json
from verify_notebooks import NotebookVerifier

SCRIPT = Path(__file__).resolve().parents[2] / "src/scripts/prepare_question_copy.py"
MAPPING = {
    "questions": [
        {
            "sourceCustomId": "source-question-mcq",
            "customId": "copied-question-mcq",
            "type": "mcq",
        },
        {
            "sourceCustomId": "source-question-frq",
            "customId": "copied-question-frq",
            "type": "frq",
        },
    ]
}


@pytest.fixture
def checkout(tmp_path, sample_course_json, monkeypatch):
    monkeypatch.chdir(tmp_path)
    chapter = sample_course_json["content"][0]
    chapter["baseFilePath"] = "chapter1.ipynb"
    chapter["chapterQuestions"] = {"CQ": ["existing-coding-question:0"]}
    chapter["sections"] = [
        {
            "sectionName": "Section",
            "sectionNumber": 1,
            "baseFilePath": "section.ipynb",
            "kernelName": "qbraid_python",
            "kernelId": "qbraid_python",
        }
    ]
    (tmp_path / "course.json").write_text(json.dumps(sample_course_json))
    (tmp_path / "question-copy.json").write_text(json.dumps(MAPPING))
    chapter_nb = nbformat.v4.new_notebook(
        cells=[
            nbformat.v4.new_markdown_cell(
                "Keep source-question-mcq in this explanation."
            ),
            nbformat.v4.new_code_cell(
                "MultipleChoiceQuestion( 'source-question-mcq' )\n"
            ),
            nbformat.v4.new_code_cell('MultipleChoiceQuestion("source-question-mcq")'),
            nbformat.v4.new_code_cell('MultipleChoiceQuestion("unrelated-question")'),
        ]
    )
    # Exercise the multiline list encoding used by checked-in .ipynb files.
    chapter_nb["cells"][1]["source"] = [
        "MultipleChoiceQuestion( ",
        "'source-question-mcq' )\n",
    ]
    (tmp_path / "chapter1.ipynb").write_text(json.dumps(chapter_nb))
    nbformat.write(
        nbformat.v4.new_notebook(
            cells=[
                nbformat.v4.new_code_cell('FreeResponseQuestion("source-question-frq")')
            ]
        ),
        tmp_path / "section.ipynb",
    )
    return tmp_path


def read(root, path):
    return json.loads((root / path).read_text())


def test_preview_then_write_is_repeatable_and_preserves_other_content(checkout):
    originals = {path.name: path.read_bytes() for path in checkout.iterdir()}
    changes = prepare_copy(checkout, "course.json", "question-copy.json")
    assert set(changes) == {"chapter1.ipynb", "section.ipynb", "course.json"}
    assert originals == {path.name: path.read_bytes() for path in checkout.iterdir()}
    prepare_copy(checkout, "course.json", "question-copy.json", write=True)
    notebook = read(checkout, "chapter1.ipynb")
    assert (
        notebook["cells"][0]["source"]
        == "Keep source-question-mcq in this explanation."
    )
    assert notebook["cells"][1]["source"] == [
        "MultipleChoiceQuestion( 'copied-question-mcq' )\n"
    ]
    assert notebook["cells"][1]["outputs"] == []
    assert (
        notebook["cells"][3]["source"] == 'MultipleChoiceQuestion("unrelated-question")'
    )
    chapter = read(checkout, "course.json")["content"][0]
    assert chapter["chapterQuestions"] == {
        "MCQ": [
            "copied-question-mcq:0",
            "copied-question-mcq:1",
            "unrelated-question:0",
        ],
        "FRQ": [],
        "CQ": ["existing-coding-question:0"],
    }
    assert chapter["sections"][0]["sectionQuestions"] == {
        "MCQ": [],
        "FRQ": ["copied-question-frq:0"],
    }
    assert prepare_copy(checkout, "course.json", "question-copy.json", write=True) == []


def test_action_validation_and_create_update_payloads_keep_the_mapping(checkout):
    before = Course(**read(checkout, "course.json")).to_payload()
    prepare_copy(checkout, "course.json", "question-copy.json", write=True)
    validate_course_json("course.json")
    NotebookVerifier().run()
    validated = read(checkout, Config.COURSE_DATA_FILE_NAME)
    assert validated["content"] != before["content"]
    creator = CourseCreator(
        "fixture-key",
        "fixture-token",
        "https://github.com/qBraid/demo",
        "a" * 40,
        force_duplicate_questions=False,
    )
    updater = CourseUpdater(
        "fixture-key",
        "destination-course",
        "fixture-token",
        "https://github.com/qBraid/demo",
        "b" * 40,
        force_duplicate_questions=False,
    )
    create_payload = creator.get_common_payload()
    update_payload = updater.get_common_payload()
    assert create_payload["data"] == update_payload["data"] == validated
    assert create_payload["forceDuplicateQuestions"] is False
    assert (
        update_payload["data"]["content"][0]["chapterQuestions"]["MCQ"][0]
        == "copied-question-mcq:0"
    )
    assert update_payload["data"]["content"][0]["sections"][0]["sectionQuestions"][
        "FRQ"
    ] == ["copied-question-frq:0"]
    # A deployment retry uses the same mapping and manifest, without recopying.
    assert prepare_copy(checkout, "course.json", "question-copy.json", write=True) == []
    validate_course_json("course.json")
    assert updater.get_common_payload()["data"] == validated


def test_existing_courses_without_reference_fields_keep_their_payload(checkout):
    course = read(checkout, "course.json")
    course["content"][0].pop("chapterQuestions")
    payload = Course(**course).to_payload()
    assert "chapterQuestions" not in payload["content"][0]
    assert "sectionQuestions" not in payload["content"][0]["sections"][0]
    assert payload["durationWeeks"] is None


@pytest.mark.parametrize(
    "mapping",
    [
        {"questions": []},
        {"questions": [MAPPING["questions"][0]] * 2},
        {"questions": [{**MAPPING["questions"][0], "customId": "source-question-mcq"}]},
        {"questions": [{**MAPPING["questions"][0], "type": "cq"}]},
        {"questions": [{**MAPPING["questions"][0], "customId": 'bad"reference'}]},
        {
            "questions": [
                {**MAPPING["questions"][0], "sourceCustomId": "absent-question"}
            ]
        },
        {"questions": [{**MAPPING["questions"][0], "type": "frq"}]},
    ],
)
def test_invalid_or_unused_mappings_fail_before_writes(checkout, mapping):
    (checkout / "question-copy.json").write_text(json.dumps(mapping))
    originals = {path.name: path.read_bytes() for path in checkout.iterdir()}
    with pytest.raises(ValueError):
        prepare_copy(checkout, "course.json", "question-copy.json", write=True)
    assert originals == {path.name: path.read_bytes() for path in checkout.iterdir()}


def test_rest_envelope_is_accepted(checkout):
    (checkout / "question-copy.json").write_text(
        json.dumps({"status": "success", "data": MAPPING})
    )
    assert prepare_copy(checkout, "course.json", "question-copy.json", write=True)


def test_missing_file_fails_before_any_notebook_is_written(checkout):
    (checkout / "section.ipynb").unlink()
    before = (checkout / "chapter1.ipynb").read_bytes()
    with pytest.raises(FileNotFoundError):
        prepare_copy(checkout, "course.json", "question-copy.json", write=True)
    assert (checkout / "chapter1.ipynb").read_bytes() == before


def test_symlink_cannot_rewrite_a_source_repository(checkout, tmp_path_factory):
    outside = tmp_path_factory.mktemp("source") / "original.ipynb"
    outside.write_bytes((checkout / "chapter1.ipynb").read_bytes())
    (checkout / "chapter1.ipynb").unlink()
    (checkout / "chapter1.ipynb").symlink_to(outside)
    original = outside.read_bytes()
    with pytest.raises(ValueError, match="outside"):
        prepare_copy(checkout, "course.json", "question-copy.json", write=True)
    assert outside.read_bytes() == original


def test_multiple_widgets_of_same_type_in_one_cell_are_rejected(checkout):
    notebook = read(checkout, "chapter1.ipynb")
    notebook["cells"][2]["source"] *= 2
    (checkout / "chapter1.ipynb").write_text(json.dumps(notebook))
    with pytest.raises(ValueError, match="separate notebook cell"):
        prepare_copy(checkout, "course.json", "question-copy.json", write=True)


def test_cli_check_fails_until_saved_mapping_is_applied(checkout):
    command = [sys.executable, str(SCRIPT), "--mapping", "question-copy.json"]
    preview = subprocess.run(
        command, cwd=checkout, capture_output=True, text=True, check=True
    )
    assert json.loads(preview.stdout)["written"] is False
    pending = subprocess.run(
        command + ["--check"], cwd=checkout, capture_output=True, text=True
    )
    assert pending.returncode == 1
    subprocess.run(command + ["--write"], cwd=checkout, capture_output=True, check=True)
    ready = subprocess.run(
        command + ["--check"], cwd=checkout, capture_output=True, text=True, check=True
    )
    assert json.loads(ready.stdout)["files"] == []
