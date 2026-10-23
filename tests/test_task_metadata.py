from dataclasses import replace

import pytest
from test_material_contract import sample, store

from pult.curriculum.material import Task, TaskMetadata, load_task, save_task
from pult.curriculum.sequence import SequenceFileError, load_sequence, save_sequence
from pult.screens.teaching.task_screen import TaskScreen
from pult.storage import load_toml, save_toml


def test_task_roundtrip_includes_metadata_without_rewriting_markdown(tmp_path):
    level = "II"
    task = Task(
        "terme",
        "# Andere Überschrift\n\na) Berechne $2+3$.\n\nb) Begründe deine Aussage.\n",
        metadata=TaskMetadata("Terme verstehen", ["K1", "K5", "K6"], level),
    )
    save_task(tmp_path, task)
    loaded = load_task(tmp_path, task.id)
    assert loaded == task
    assert loaded.metadata.title == "Terme verstehen"
    assert not (tmp_path / "aufgaben/terme/loesung.md").exists()
    assert load_toml(tmp_path / "aufgaben/terme/aufgabe.toml") == {
        "titel": "Terme verstehen",
        "kompetenzen": ["K1", "K5", "K6"],
        "anforderungsbereich": level,
    }


@pytest.mark.parametrize(
    "field,value",
    [
        ("titel", " "),
        ("titel", 42),
        ("kompetenzen", []),
        ("kompetenzen", "K1"),
        ("kompetenzen", [""]),
        ("kompetenzen", ["K1", " K1 "]),
        ("kompetenzen", ["K1", 2]),
        ("kompetenzen", ["K1", "K2", "K3", "K4"]),
        ("anforderungsbereich", "IV"),
        ("anforderungsbereich", ["I", "II"]),
        ("unbekannt", "Feld"),
    ],
)
def test_invalid_task_metadata_reports_file(tmp_path, field, value):
    _, sequence_path = store(tmp_path)
    path = sequence_path.parent / "aufgaben/vergleichen/aufgabe.toml"
    data = load_toml(path)
    data[field] = value
    save_toml(path, data)
    with pytest.raises(ValueError, match="aufgabe.toml"):
        load_task(sequence_path.parent, "vergleichen")


@pytest.mark.parametrize(
    "field",
    [
        "kompetenzen",
    ],
)
def test_missing_metadata_field_is_rejected(tmp_path, field):
    _, sequence_path = store(tmp_path)
    path = sequence_path.parent / "aufgaben/vergleichen/aufgabe.toml"
    data = load_toml(path)
    del data[field]
    save_toml(path, data)
    with pytest.raises(ValueError, match="aufgabe.toml"):
        load_task(sequence_path.parent, "vergleichen")


def test_broken_toml_is_not_replaced_or_inferred_from_markdown(tmp_path):
    _, sequence_path = store(tmp_path)
    path = sequence_path.parent / "aufgaben/vergleichen/aufgabe.toml"
    path.write_text("titel = [")
    with pytest.raises(ValueError, match="aufgabe.toml"):
        load_task(sequence_path.parent, "vergleichen")
    assert path.read_text() == "titel = ["


def test_metadata_may_use_subject_specific_competencies():
    metadata = TaskMetadata(
        "  Modelle   erklären ", [" Modellieren ", "Kommunizieren"], "II"
    )
    assert metadata.title == "Modelle erklären"
    assert metadata.competencies == ["Modellieren", "Kommunizieren"]


def test_competency_labels_are_literal_text_in_the_viewer(tmp_path):
    sequence, path = store(tmp_path)
    task = sequence.lessons[0].tasks[0]
    task.metadata.competencies = ["Modellieren [K3]"]
    save_task(path.parent, task)
    screen = TaskScreen(sequence, path.parent)
    subtitle = screen.material_subtitle()
    assert subtitle.plain == "Aufgabe · AFB II · Modellieren [K3]"
    assert subtitle.spans == []


def test_metadata_cannot_follow_external_symlinks_on_read_or_write(tmp_path):
    _, sequence_path = store(tmp_path)
    folder = sequence_path.parent
    path = folder / "aufgaben/vergleichen/aufgabe.toml"
    outside = tmp_path / "outside.toml"
    outside.write_bytes(path.read_bytes())
    path.unlink()
    path.symlink_to(outside)
    before = outside.read_bytes()
    with pytest.raises(ValueError, match="außerhalb"):
        load_task(folder, "vergleichen")
    with pytest.raises(ValueError, match="außerhalb"):
        save_task(folder, sample().lessons[0].tasks[0])
    assert outside.read_bytes() == before


def test_conflicting_metadata_for_shared_task_rejected_before_writing(tmp_path):
    sequence = sample()
    task = sequence.lessons[0].tasks[0]
    sequence.lessons[1].tasks = [
        replace(task, metadata=replace(task.metadata, requirement_level="III"))
    ]
    with pytest.raises(ValueError, match="Widersprüchliche"):
        save_sequence(tmp_path, sequence)
    assert not (tmp_path / "sequences").exists()


def test_sequence_reports_invalid_task_metadata_file(tmp_path):
    _, sequence_path = store(tmp_path)
    path = sequence_path.parent / "aufgaben/vergleichen/aufgabe.toml"
    data = load_toml(path)
    data["titel"] = " "
    save_toml(path, data)
    with pytest.raises(SequenceFileError, match="aufgabe.toml"):
        load_sequence(tmp_path, 6, "mathematik", "brueche")
