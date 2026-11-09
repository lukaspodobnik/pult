from copy import deepcopy

import pytest

from pult.curriculum.material import (
    Task,
    TaskMetadata,
    TaskSource,
    load_task,
    save_task,
)
from pult.curriculum.sequence import load_sequence, save_sequence
from pult.services.exports.task_export import workbook_html
from pult.services.exports.task_export_profile import WorkbookProfile


def task(source=None):
    title = "Eigene Aufgabe"
    if source is not None and source.kind == "buch":
        reference = f"A. {source.number}" if source.number else source.label
        title = f"S. {source.page} {reference}"
    return Task(
        "buch-s32-a08",
        "# Interner Titel\n\nRechne $2x$.",
        "Ergebnis: $2x$.",
        metadata=TaskMetadata(title, ["K5"], "I", source=source),
    )


def book_source(**overrides):
    data = {
        "art": "buch",
        "buch": "fokus-7",
        "seite": 32,
        "nummer": "8",
        "rubrik": "Trainieren",
    }
    data.update(overrides)
    return data


@pytest.mark.parametrize(
    "data",
    [
        {"art": "eigen"},
        book_source(),
        {
            "art": "buch",
            "buch": "fokus-7",
            "seite": 52,
            "bezeichnung": "Äquivalente Terme",
            "rubrik": "Einstieg",
        },
    ],
)
def test_source_roundtrip(tmp_path, data):
    exercise = task(TaskSource.from_dict(data))
    save_task(tmp_path, exercise)
    assert load_task(tmp_path, exercise.id) == exercise
    assert exercise.metadata.source.to_dict() == data


@pytest.mark.parametrize(
    "data",
    [
        [],
        {},
        {"art": "web"},
        {"art": "eigen", "seite": 1},
        book_source(art=["buch"]),
        book_source(buch="../fokus"),
        book_source(buch="FOKUS"),
        book_source(buch=None),
        book_source(seite=True),
        book_source(seite=0),
        book_source(seite="32"),
        book_source(nummer=8),
        book_source(nummer=""),
        book_source(nummer=None),
        book_source(bezeichnung="Text"),
        book_source(rubrik=""),
        book_source(unbekannt=True),
    ],
)
def test_source_rejects_incomplete_or_ambiguous_data(data):
    with pytest.raises(ValueError):
        TaskSource.from_dict(data)


def test_books_survive_sequence_load_and_save(tmp_path, sequences):
    seq = deepcopy(sequences[0])
    seq.books = {"fokus-7": "Fokus Mathematik 7"}
    seq.lessons[0].tasks = [task(TaskSource.from_dict(book_source()))]
    save_sequence(tmp_path, seq)
    result = load_sequence(tmp_path, seq.grade_level, seq.subject_id, seq.id)
    assert result == seq
    save_sequence(tmp_path, result)
    assert load_sequence(tmp_path, seq.grade_level, seq.subject_id, seq.id) == seq


@pytest.mark.parametrize("books", [[], {"Bad": "Buch"}, {"buch": ""}, {"buch": 123}])
def test_invalid_book_registry(books, sequences):
    seq = deepcopy(sequences[0])
    seq.books = books
    with pytest.raises(ValueError):
        seq.__post_init__()


def test_profiles_choose_from_actual_selection_and_preserve_source_in_solutions(
    tmp_path, sequences
):
    seq = deepcopy(sequences[0])
    seq.books = {"fokus-7": "Fokus <Mathematik> & 7", "unused": "Nicht verwendet"}
    exercise = task(TaskSource.from_dict(book_source()))
    own = task(TaskSource())
    own.id = "eigene-aufgabe"
    legacy = task()
    for tasks, mode, author in [
        ([exercise], "buch", ""),
        ([own, legacy], "eigen", "Name"),
        ([exercise, own], "gemischt", ""),
    ]:
        profile = WorkbookProfile.for_tasks(tasks, seq)
        assert profile.kind == mode
        assert profile.author("Name") == author
        for solutions in (False, True):
            html = workbook_html(tasks, seq, tmp_path, solutions=solutions)
            assert "Nicht verwendet" not in html
            assert "<h1>Interner Titel" not in html
            if mode == "buch":
                assert "S. 32 · Aufgabe 8</h2>" in html
                assert "1. Aufgabe</h2>" not in html
                assert "Trainieren" in html
            elif mode == "gemischt":
                assert "1. Aufgabe</h2>" in html
                assert "S. 32 · Aufgabe 8" in html
            if mode != "eigen":
                assert "Fokus &lt;Mathematik&gt; &amp; 7" in html
                assert ("Lösungen zu Aufgaben aus" in html) == solutions


def test_unnumbered_and_multiple_books_are_unambiguous(sequences):
    seq = deepcopy(sequences[0])
    seq.books = {"fokus-7": "Fokus Mathematik 7", "anderes-buch": "Anderes Buch"}
    first = task(
        TaskSource("buch", "fokus-7", 52, label="Äquivalente Terme", rubric="Einstieg")
    )
    second = task(TaskSource("buch", "anderes-buch", 52, "1"))
    profile = WorkbookProfile.for_tasks([first, second], seq)
    assert profile.heading(first, 1) == "S. 52 · Äquivalente Terme"
    assert profile.caption(first) == "Fokus Mathematik 7 · Einstieg"
    assert profile.caption(second) == "Anderes Buch"


def test_unknown_book_is_rejected_even_for_unassigned_tasks(tmp_path, sequences):
    exercise = task(TaskSource.from_dict(book_source()))
    save_task(tmp_path, exercise)
    with pytest.raises(ValueError, match="Unbekanntes Buch"):
        workbook_html([load_task(tmp_path, exercise.id)], sequences[0], tmp_path)
