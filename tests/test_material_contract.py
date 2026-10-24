from pathlib import Path

import pytest

from pult.curriculum.material import Lesson, Phase, Task, TaskMetadata
from pult.curriculum.sequence import (
    Sequence,
    SequenceFileError,
    get_sequence_path,
    load_sequence,
    save_sequence,
)
from pult.storage import load_toml, save_toml
from pult.widgets.sequence_preview import SequencePreview


def sample():
    task = Task(
        "vergleichen",
        "Vergleiche $\\frac{1}{2}$ und $\\frac{2}{4}$.\n",
        "```python\nprint(1 / 2 == 2 / 4)\n```\n",
        metadata=TaskMetadata("Brüche vergleichen", ["K1", "K4"], "II"),
    )
    return Sequence(
        "brueche",
        "M6 1",
        "mathematik",
        6,
        "Brüche",
        2,
        [
            Lesson(
                "erweitern",
                "Erweitern",
                [task],
                "# Ein Beispiel\n\n$$x=1$$\n",
                ["Anteile erklären", "Gezielt erweitern"],
                ["Papierstreifen", "Schere"],
                [
                    Phase("Einstieg", "Anteile vergleichen."),
                    Phase("Sicherung", "Regel festhalten."),
                ],
            ),
            Lesson("vertiefen", "Vertiefen", [task]),
        ],
    )


def store(tmp_path):
    sequence = sample()
    save_sequence(tmp_path, sequence)
    return sequence, get_sequence_path(tmp_path, 6, "mathematik", "brueche")


def test_material_roundtrip_shared_tasks_and_order(tmp_path):
    original, path = store(tmp_path)
    data = load_toml(path)
    assert data["stunden"] == ["erweitern", "vertiefen"]
    assert "lessons" not in data
    loaded = load_sequence(tmp_path, 6, "mathematik", "brueche")
    assert loaded == original
    assert loaded.lessons[0].tasks[0] is loaded.lessons[1].tasks[0]
    data["stunden"].reverse()
    save_toml(path, data)
    reordered = load_sequence(tmp_path, 6, "mathematik", "brueche")
    assert [lesson.id for lesson in reordered.lessons] == ["vertiefen", "erweitern"]
    assert reordered.lessons[1].preparation == original.lessons[0].preparation


def test_preparation_remains_free_and_material_separate(tmp_path):
    _, path = store(tmp_path)
    folder = path.parent / "stunden/erweitern"
    (folder / "vorbereitung.md").unlink()
    loaded = load_sequence(tmp_path, 6, "mathematik", "brueche")
    assert loaded.lessons[0].preparation_markdown() == ""
    assert loaded.lessons[0].material == ["Papierstreifen", "Schere"]
    assert "Papierstreifen" in SequencePreview.render_sequence(loaded)
    assert "vergleichen" not in SequencePreview.render_sequence(loaded)
    assert set(load_toml(folder / "stunde.toml")) == {"titel", "aufgaben"}
    before = (folder / "ziele.md").read_bytes()
    save_sequence(tmp_path, loaded)
    assert (folder / "ziele.md").read_bytes() == before


@pytest.mark.parametrize(
    "field,value",
    [
        ("titel", ""),
        ("ziele", "kein Array"),
        ("material", [""]),
        ("aufgaben", ["../fremd"]),
        ("aufgaben", ["vergleichen", "vergleichen"]),
        ("aufgaben", ["VERGLEICHEN"]),
        ("phasen", ["Einstieg"]),
        ("phasen", [{"titel": "Einstieg"}]),
        ("materail", ["Tippfehler"]),
    ],
)
def test_invalid_lesson_metadata_has_file_context(tmp_path, field, value):
    _, path = store(tmp_path)
    lesson_path = path.parent / "stunden/erweitern/stunde.toml"
    data = load_toml(lesson_path)
    data[field] = value
    save_toml(lesson_path, data)
    with pytest.raises(SequenceFileError, match="stunde.toml"):
        load_sequence(tmp_path, 6, "mathematik", "brueche")


@pytest.mark.parametrize(
    "relative",
    [
        "stunden/erweitern/stunde.toml",
        "aufgaben/vergleichen/aufgabe.md",
        "aufgaben/vergleichen/aufgabe.toml",
    ],
)
def test_missing_required_reference_is_not_silently_skipped(tmp_path, relative):
    _, path = store(tmp_path)
    (path.parent / relative).unlink()
    with pytest.raises(SequenceFileError, match=Path(relative).name):
        load_sequence(tmp_path, 6, "mathematik", "brueche")


def test_reject_conflicting_shared_tasks_before_writing(tmp_path):
    sequence = sample()
    sequence.lessons[1].tasks = [
        Task(
            "vergleichen",
            "Anderer Inhalt",
            metadata=TaskMetadata("Vergleichen", ["K1"], "I"),
        )
    ]
    with pytest.raises(ValueError, match="Widersprüchliche"):
        save_sequence(tmp_path, sequence)
    assert not (tmp_path / "sequences").exists()


def test_removed_reference_does_not_delete_material(tmp_path):
    original, path = store(tmp_path)
    original.lessons = [Lesson("neu", "Neue Stunde")]
    save_sequence(tmp_path, original)
    assert (path.parent / "aufgaben/vergleichen/aufgabe.md").is_file()
    assert (path.parent / "stunden/erweitern/vorbereitung.md").is_file()
    assert len(load_sequence(tmp_path, 6, "mathematik", "brueche").lessons) == 1


def test_external_symlink_reference_rejected(tmp_path):
    _, path = store(tmp_path)
    target = tmp_path / "external.md"
    target.write_text("Privat")
    task = path.parent / "aufgaben/vergleichen/aufgabe.md"
    task.unlink()
    task.symlink_to(target)
    with pytest.raises(SequenceFileError, match="außerhalb"):
        load_sequence(tmp_path, 6, "mathematik", "brueche")


def test_home_and_class_summaries_omit_material_details(
    planned_lesson, sequences, subject
):
    from types import SimpleNamespace

    from pult.views.school_class_view import SubjectProgressBlock
    from pult.widgets.dashboard.next_lesson import NextLessonPanel

    planned_lesson.lesson.material = ["Papierstreifen", "Schere"]
    home = NextLessonPanel(
        planned_lesson,
        planned_lesson.date,
        {subject.id: subject},
        {(s.grade_level, s.subject_id, s.id): s for s in sequences},
    )
    assert "next-lesson-material" not in home._texts()
    summary = SimpleNamespace(
        next_planned_lesson=planned_lesson,
        next_scheduled_assessment=None,
        sequences=[
            SimpleNamespace(
                sequence_id=sequences[0].id,
                title=sequences[0].title,
                curriculum_section_id=sequences[0].curriculum_section_id,
            )
        ],
    )
    texts = SubjectProgressBlock._next_lesson_texts(SimpleNamespace(summary=summary))
    assert texts["next-lesson-title"] == planned_lesson.lesson.title
    assert all(
        "Papierstreifen" not in value and "Schere" not in value
        for value in texts.values()
    )
    assert planned_lesson.lesson.material == ["Papierstreifen", "Schere"]


def test_neutral_example_matches_contract():
    root = Path(__file__).parents[1] / "examples/unterricht"
    sequence = load_sequence(root, 6, "mathematik", "formatbeispiel")
    lesson = sequence.lessons[0]
    assert lesson.goals and lesson.material and lesson.phases
    assert lesson.tasks[0].solution
    assert lesson.preparation and "../../dateien/anteile.svg" in lesson.preparation
    assert (
        root / "sequences/6/mathematik/formatbeispiel/dateien/anteile.svg"
    ).is_file()


def test_starter_files_are_short_and_never_overwrite(tmp_path):
    from pult.curriculum.material import initialize_lesson_files, load_lesson

    initialize_lesson_files(tmp_path, "neu")
    folder = tmp_path / "stunden/neu"
    assert load_toml(folder / "stunde.toml") == {
        "titel": "Noch nicht vorbereitet",
        "aufgaben": [],
    }
    assert (folder / "vorbereitung.md").read_text() == "# Noch nicht vorbereitet\n"
    assert (
        folder / "ziele.md"
    ).read_text() == "- Die Schüler können\n- Die Schüler können\n"
    assert (folder / "verlauf.md").read_text() == "# Einstieg\n"
    assert (folder / "material.md").read_text() == ""
    assert load_lesson(tmp_path, "neu", {}).phases == [Phase("Einstieg", "")]
    (folder / "vorbereitung.md").write_text("Eigene Vorbereitung")
    initialize_lesson_files(tmp_path, "neu")
    assert (folder / "vorbereitung.md").read_text() == "Eigene Vorbereitung"


@pytest.mark.parametrize(
    "source", ["# Ziel", "1. Ziel", "- Ziel\n  - Unterziel", "Text\n\n- Ziel", "- "]
)
def test_goals_reject_non_flat_lists(source):
    from pult.curriculum.material import unordered_items

    with pytest.raises(ValueError, match="ziele.md"):
        unordered_items(source, "ziele.md")


def test_phase_parser_handles_code_and_preserves_body():
    from pult.curriculum.material import parse_phases

    source = (
        "\n# Einstieg\n\nText mit $x$.\n\n```python\n## kein Heading\n```\n\n# Übung\n"
    )
    phases = parse_phases(source)
    assert [p.title for p in phases] == ["Einstieg", "Übung"]
    assert "## kein Heading" in phases[0].text
    assert phases[1].text == ""


@pytest.mark.parametrize(
    "source",
    ["Text\n# Einstieg", "## Einstieg", "# Einstieg\n## Übung", "Phase\n====", "#"],
)
def test_phase_parser_rejects_invalid_headings(source):
    from pult.curriculum.material import parse_phases

    with pytest.raises(ValueError):
        parse_phases(source)


def test_material_links_are_named_and_separate_from_preparation():
    from pult.curriculum.material import material_entries

    entries = material_entries(
        "- Schere\n- [Keynote](../../dateien/beispiel.key)\n- [Webseite](https://example.org)\n"
    )
    assert [e.label for e in entries] == ["Schere", "Keynote", "Webseite"]
    assert entries[1].target == "../../dateien/beispiel.key"


def test_task_assignment_only_changes_metadata(tmp_path):
    from pult.curriculum.material import save_lesson_metadata

    sequence, path = store(tmp_path)
    folder = path.parent / "stunden/erweitern"
    before = {p.name: p.read_bytes() for p in folder.glob("*.md")}
    sequence.lessons[0].tasks = []
    save_lesson_metadata(path.parent, sequence.lessons[0])
    assert load_toml(folder / "stunde.toml")["aufgaben"] == []
    assert {p.name: p.read_bytes() for p in folder.glob("*.md")} == before


def test_explicit_new_hours_get_same_starters_after_validation(tmp_path):
    sequence, path = store(tmp_path)
    data = load_toml(path)
    data["stunden"].append("weitere")
    save_toml(path, data)
    loaded = load_sequence(tmp_path, 6, "mathematik", "brueche", create_missing=True)
    assert loaded.lessons[-1].title == "Noch nicht vorbereitet"
    assert (path.parent / "stunden/weitere/verlauf.md").read_text() == "# Einstieg\n"
    data["stunden"].append("ungueltig")
    data["subject_id"] = "informatik"
    save_toml(path, data)
    with pytest.raises(SequenceFileError):
        load_sequence(tmp_path, 6, "mathematik", "brueche", create_missing=True)
    assert not (path.parent / "stunden/ungueltig").exists()
