from unittest.mock import Mock

import pytest

from schooltools_tui.config import AppConfig
from schooltools_tui.progress.class_progress import ActiveSequence, ClassProgress
from schooltools_tui.school.school_class import SchoolClass
from schooltools_tui.services import progress as service


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
    for name in ("load_class_progress", "load_class_closures"):
        assert [call.args[2] for call in mocks[name].call_args_list] == expected_ids
    mocks["load_sequence_library"].assert_called_once_with(config.root)


def test_loading_validates_progress_against_library(loaders):
    config, mocks = loaders
    mocks["load_class_progress"].return_value = ClassProgress(
        (ActiveSequence("mathematik", "missing-sequence"),), ()
    )
    with pytest.raises(ValueError):
        service.load_planning_data(config, "5A")


def test_class_progress_can_reuse_loaded_library(loaders, school_class, sequences):
    config, mocks = loaders
    data = service.load_class_progress_data(config, school_class, sequences=sequences)
    assert data.sequences is sequences
    mocks["load_sequence_library"].assert_not_called()


def test_loading_propagates_file_errors(loaders, school_class):
    config, mocks = loaders
    mocks["load_class_progress"].side_effect = FileNotFoundError("Missing progress")
    with pytest.raises(FileNotFoundError):
        service.load_class_progress_data(config, school_class)
