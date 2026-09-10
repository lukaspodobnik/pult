from pathlib import Path

import pytest

from pult.curriculum.material import Lesson, Phase, Task
from pult.curriculum.sequence import (
    Sequence,
    SequenceFileError,
    get_sequence_path,
    load_sequence,
    load_sequence_library,
    save_sequence,
)
from pult.storage import load_toml, save_toml
from pult.widgets.sequence_preview import SequencePreview


def sample():
    task = Task(
        "vergleichen",
        "Vergleiche $\\frac{1}{2}$ und $\\frac{2}{4}$.\n",
        "```python\nprint(1 / 2 == 2 / 4)\n```\n",
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


def test_optional_files_and_material_only_preparation(tmp_path):
    _, path = store(tmp_path)
    lesson_path = path.parent / "stunden/erweitern/stunde.toml"
    save_toml(lesson_path, {"titel": "Offene Stunde", "material": ["Schere"]})
    (lesson_path.parent / "vorbereitung.md").unlink()
    lesson = load_sequence(tmp_path, 6, "mathematik", "brueche").lessons[0]
    assert lesson.tasks == lesson.goals == lesson.phases == []
    assert lesson.preparation is None
    assert lesson.preparation_markdown() == "## Benötigtes Material\n\n- Schere"
    assert not (lesson_path.parent / "vorbereitung.md").exists()
    empty = Lesson("frei", "Projektarbeit")
    assert empty.preparation_markdown() == ""


def test_material_section_is_derived_and_solutions_are_optional(tmp_path):
    _, path = store(tmp_path)
    (path.parent / "aufgaben/vergleichen/loesung.md").unlink()
    loaded = load_sequence(tmp_path, 6, "mathematik", "brueche")
    lesson = loaded.lessons[0]
    before = (path.parent / "stunden/erweitern/vorbereitung.md").read_bytes()
    assert lesson.preparation_markdown().startswith("## Benötigtes Material")
    assert lesson.tasks[0].solution is None
    assert "Papierstreifen" in SequencePreview.render_sequence(loaded)
    assert "Anteile erklären" in SequencePreview.render_sequence(loaded)
    save_sequence(tmp_path, loaded)
    assert (path.parent / "stunden/erweitern/vorbereitung.md").read_bytes() == before
    assert not (path.parent / "aufgaben/vergleichen/loesung.md").exists()


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
    "relative", ["stunden/erweitern/stunde.toml", "aufgaben/vergleichen/aufgabe.md"]
)
def test_missing_required_reference_is_not_silently_skipped(tmp_path, relative):
    _, path = store(tmp_path)
    (path.parent / relative).unlink()
    with pytest.raises(SequenceFileError, match=Path(relative).name):
        load_sequence(tmp_path, 6, "mathematik", "brueche")


def test_reject_conflicting_shared_tasks_before_writing(tmp_path):
    sequence = sample()
    sequence.lessons[1].tasks = [Task("vergleichen", "Anderer Inhalt")]
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


def test_all_default_ids_and_planning_slots_preserved():
    root = Path(__file__).parents[1] / "src/pult/defaults"
    library = load_sequence_library(root)
    assert len(library) == 116
    assert sum(len(s.lessons) for s in library) == 1645
    assert all(
        lesson.title == "Noch nicht vorbereitet"
        for s in library
        for lesson in s.lessons
    )


def test_material_summary_in_home_and_class_view(planned_lesson, sequences, subject):
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
    assert home._texts()["next-lesson-material"] == "Material: Papierstreifen · Schere"
    summary = SimpleNamespace(
        next_planned_lesson=planned_lesson,
        sequences=[
            SimpleNamespace(
                sequence_id=sequences[0].id,
                title=sequences[0].title,
                curriculum_section_id=sequences[0].curriculum_section_id,
            )
        ],
    )
    assert (
        SubjectProgressBlock._next_lesson_texts(SimpleNamespace(summary=summary))[
            "next-lesson-material"
        ]
        == "Material: Papierstreifen · Schere"
    )


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
