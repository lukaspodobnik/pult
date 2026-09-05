from datetime import date, time

import pytest

from schooltools_tui.curriculum.sequence import (
    Lesson,
    Sequence,
    SequenceFileError,
    get_sequence_directory,
    load_sequence,
    save_sequence,
)
from schooltools_tui.progress.class_progress import (
    ActiveSequence,
    ClassProgress,
    ClassProgressFileError,
    TeachingAction,
    TeachingLogEntry,
    TeachingOrigin,
    get_class_progress_path,
    load_class_progress,
    save_class_progress,
    validate_class_progress,
)
from schooltools_tui.school.period import Period, PeriodsFileError, load_periods, save_periods
from schooltools_tui.school.school_class import (
    SchoolClass,
    get_school_class_path,
    load_school_class,
    save_school_class,
)
from schooltools_tui.school.timetable import (
    TimetableEntry,
    get_timetable_path,
    load_timetable,
    save_timetable,
)
from schooltools_tui.storage import load_toml, save_toml


def test_load_toml_raises_for_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_toml(tmp_path / "missing.toml")


def test_save_toml_does_not_create_parent_directory(tmp_path):
    with pytest.raises(FileNotFoundError):
        save_toml(tmp_path / "missing" / "data.toml", {"value": 1})


def test_sequence_roundtrip(tmp_path, sequences):
    sequence = sequences[0]
    get_sequence_directory(tmp_path, 5, "mathematik").mkdir(parents=True)
    save_sequence(tmp_path, sequence)
    assert load_sequence(tmp_path, 5, "mathematik", sequence.id) == sequence


def test_sequence_rejects_duplicate_lesson_ids():
    lessons = [
        Lesson("same", "A", [], ""),
        Lesson("same", "B", [], ""),
    ]
    with pytest.raises(ValueError):
        Sequence("sequence", "M5 1", "mathematik", 5, "Titel", 2, lessons)


def test_sequence_loader_rejects_location_mismatch(tmp_path):
    directory = get_sequence_directory(tmp_path, 5, "mathematik")
    directory.mkdir(parents=True)
    save_toml(
        directory / "wrong.toml",
        {
            "id": "different",
            "curriculum_section_id": "M5 1",
            "subject_id": "mathematik",
            "grade_level": 5,
            "title": "Titel",
            "recommended_lesson_count": 1,
            "lessons": [{"id": "lesson", "title": "Titel", "tasks": [], "notes": ""}],
        },
    )
    with pytest.raises(SequenceFileError):
        load_sequence(tmp_path, 5, "mathematik", "wrong")


def test_school_class_normalizes_id_and_roundtrips(tmp_path):
    school_class = SchoolClass(" 5a ", 5, ["mathematik"])
    path = get_school_class_path(tmp_path, "2026-2027", school_class.id)
    path.parent.mkdir(parents=True)
    save_school_class(tmp_path, "2026-2027", school_class)
    assert load_school_class(tmp_path, "2026-2027", "5A") == school_class


@pytest.mark.parametrize("class_id", ["A5", "5 A", "  "])
def test_school_class_rejects_invalid_id(class_id):
    with pytest.raises(ValueError):
        SchoolClass(class_id, 5, ["mathematik"])


def test_school_class_requires_subject():
    with pytest.raises(ValueError):
        SchoolClass("5A", 5, [])


def test_periods_roundtrip(tmp_path):
    periods = [Period(1, time(8), time(8, 45)), Period(2, time(9), time(9, 45))]
    save_periods(tmp_path, periods)
    assert load_periods(tmp_path) == periods


def test_periods_reject_overlap(tmp_path):
    with pytest.raises(PeriodsFileError):
        save_periods(
            tmp_path,
            [Period(1, time(8), time(9)), Period(2, time(8, 30), time(9, 30))],
        )


def test_timetable_roundtrip(tmp_path):
    path = get_timetable_path(tmp_path, "2026-2027")
    path.parent.mkdir(parents=True)
    entries = [TimetableEntry("monday", 1, "5A", "mathematik", "101")]
    save_timetable(path, entries)
    assert load_timetable(path) == entries


def test_class_progress_roundtrip(tmp_path, school_class, sequences):
    path = get_class_progress_path(tmp_path, "2026-2027", "5A")
    path.parent.mkdir(parents=True)
    progress = ClassProgress(
        (ActiveSequence("mathematik", "sequence-1"),),
        (
            TeachingLogEntry(
                date(2026, 9, 7), "mathematik", "sequence-1",
                TeachingAction.COMPLETED, TeachingOrigin.SCHEDULED,
                "Erledigt", "lesson-1", 1,
            ),
        ),
    )
    save_class_progress(tmp_path, "2026-2027", "5A", progress)
    loaded = load_class_progress(tmp_path, "2026-2027", "5A")
    validate_class_progress(loaded, school_class, sequences)
    assert loaded == progress


def test_progress_rejects_duplicate_scheduled_occurrence():
    entries = tuple(
        TeachingLogEntry(
            date(2026, 9, 7), "mathematik", "sequence-1", action,
            TeachingOrigin.SCHEDULED, lesson_id="lesson-1", period=1,
        )
        for action in (TeachingAction.CONTINUED, TeachingAction.COMPLETED)
    )
    with pytest.raises(ValueError):
        ClassProgress((ActiveSequence("mathematik", "sequence-1"),), entries)


def test_progress_loader_rejects_unknown_keys(tmp_path):
    path = get_class_progress_path(tmp_path, "2026-2027", "5A")
    path.parent.mkdir(parents=True)
    save_toml(path, {"active_sequences": [], "entries": [], "unexpected": True})
    with pytest.raises(ClassProgressFileError):
        load_class_progress(tmp_path, "2026-2027", "5A")
