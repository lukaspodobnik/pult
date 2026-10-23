from dataclasses import replace
from unittest.mock import Mock

import pytest

from pult.config import AppConfig
from pult.progress.class_progress import (
    ActiveSequence,
    ClassProgress,
    ClassProgressValidationError,
    get_class_progress_path,
    load_class_progress,
)
from pult.school.school_class import SchoolClass
from pult.school.timetable import TimetableEntry
from pult.services import progress as service


@pytest.fixture
def loaders(
    tmp_path,
    monkeypatch,
    school_class,
    sequences,
    empty_progress,
    school_calendar,
    timetable_entries,
):
    values = {
        "load_school_classes": [school_class, SchoolClass("5B", 5, ["mathematik"])],
        "load_sequence_library": sequences,
        "load_class_progress": empty_progress,
        "load_timetable": timetable_entries,
        "load_school_calendar": school_calendar,
        "load_school_closures": [],
        "load_class_closures": [],
    }
    mocks = {}
    for name, value in values.items():
        mocks[name] = Mock(return_value=value)
        monkeypatch.setattr(service, name, mocks[name])
    return AppConfig(tmp_path, "true", "2026-2027"), mocks


@pytest.mark.parametrize(
    "class_id, expected_ids", [(None, ["5A", "5B"]), ("5A", ["5A"])]
)
def test_planning_loads_only_requested_progress_and_closures(
    loaders, class_id, expected_ids
):
    config, mocks = loaders
    data = service.load_planning_data(config, class_id)

    assert list(data.progresses_by_class_id) == expected_ids
    assert [school_class.id for school_class in data.school_classes] == expected_ids
    assert set(data.class_closures_by_class_id) == set(expected_ids)


def test_loading_validates_progress_against_library(loaders):
    config, mocks = loaders
    mocks["load_class_progress"].return_value = ClassProgress(
        (ActiveSequence("mathematik", "missing-sequence"),), ()
    )
    with pytest.raises(ValueError):
        service.load_planning_data(config, "5A")


def test_loading_propagates_file_errors(loaders, school_class):
    config, mocks = loaders
    mocks["load_class_progress"].side_effect = FileNotFoundError("Missing progress")
    with pytest.raises(FileNotFoundError):
        service.load_class_progress_data(config, school_class)


@pytest.mark.parametrize(
    "class_id, subject_id, expected_class_id, expected_period",
    [
        (None, None, "5B", 1),
        ("5A", "mathematik", "5A", 2),
        ("5A", "informatik", None, None),
    ],
)
def test_planned_context_respects_class_and_subject_selection(
    loaders, planned_lesson, class_id, subject_id, expected_class_id, expected_period
):
    config, mocks = loaders
    mocks["load_timetable"].return_value = [
        TimetableEntry("monday", 1, "5B", "mathematik", "102"),
        TimetableEntry("monday", 2, "5A", "mathematik", "101"),
    ]
    data = service.load_planning_data(config)

    context = service.get_planned_lesson_context(data, class_id, subject_id)

    if expected_class_id is None:
        assert context is None
    else:
        assert context is not None
        assert context.school_class.id == expected_class_id
        assert context.planned_lesson == replace(
            planned_lesson, school_class_id=expected_class_id, period=expected_period
        )
        assert context.progress == data.progresses_by_class_id[expected_class_id]
        assert context.sequences == data.sequences


def test_invalid_progress_does_not_overwrite_saved_progress(
    tmp_path, school_class, sequences, empty_progress
):
    config = AppConfig(tmp_path, "true", "2026-2027")
    path = get_class_progress_path(tmp_path, "2026-2027", "5A")
    path.parent.mkdir(parents=True)
    service.save_class_progress_data(
        config, school_class, empty_progress, sequences=sequences
    )
    assert load_class_progress(tmp_path, "2026-2027", "5A") == empty_progress
    saved = path.read_bytes()
    invalid_progress = ClassProgress(
        (ActiveSequence("mathematik", "missing-sequence"),), ()
    )

    with pytest.raises(ClassProgressValidationError, match="missing-sequence"):
        service.save_class_progress_data(
            config, school_class, invalid_progress, sequences=sequences
        )

    assert path.read_bytes() == saved
