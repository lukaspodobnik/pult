from dataclasses import replace
from datetime import date, time

import pytest

from pult.school.assessment import (
    Assessment,
    AssessmentKind,
    AssessmentsFileError,
    get_assessments_path,
    load_assessments,
    save_assessments,
)
from pult.storage import load_toml, save_toml


def assessment(**changes):
    base = Assessment(
        id="bmt-8",
        subject_id="mathematik",
        kind=AssessmentKind.YEAR_GROUP_TEST,
        title="BMT 8",
        date=date(2026, 10, 1),
        start=time(8, 0),
        duration_minutes=45,
    )
    return replace(base, **changes)


@pytest.mark.parametrize("minutes,periods", [(20, (2,)), (60, (2, 3)), (45, ())])
def test_duration_does_not_determine_occupied_periods(minutes, periods):
    entry = assessment(duration_minutes=minutes, occupied_periods=periods)
    assert entry.duration_minutes == minutes
    assert entry.occupied_periods == periods


@pytest.mark.parametrize(
    "changes",
    [
        {"duration_minutes": 0},
        {"duration_minutes": True},
        {"occupied_periods": (2, 2)},
        {"occupied_periods": (0,)},
        {"occupied_periods": (True,)},
        {"group_id": " "},
    ],
)
def test_invalid_time_consumption_and_group_are_rejected(changes):
    with pytest.raises(ValueError):
        assessment(**changes)


def test_linked_tests_remain_separate_appointments():
    bmt = assessment(group_id="sa-1")
    follow_up = assessment(
        id="test-1",
        date=date(2026, 10, 15),
        kind=AssessmentKind.ANNOUNCED_TEST,
        group_id="sa-1",
    )
    assert bmt.group_id == follow_up.group_id
    assert bmt.id != follow_up.id
    assert bmt.date != follow_up.date


@pytest.fixture
def assessment_path(tmp_path):
    path = get_assessments_path(tmp_path, "2026-2027", "8A")
    assert path == tmp_path / "school-years/2026-2027/classes/8A/assessments.toml"
    path.parent.mkdir(parents=True)
    return path


def test_missing_file_and_empty_list(tmp_path, assessment_path):
    assert load_assessments(tmp_path, "2026-2027", "8A") == []
    assert not assessment_path.exists()
    save_assessments(tmp_path, "2026-2027", "8A", [])
    assert load_assessments(tmp_path, "2026-2027", "8A") == []


def test_round_trip_sorts_without_changing_input(tmp_path, assessment_path):
    entries = [
        assessment(id="late", start=time(10), group_id="sa-1", occupied_periods=(3, 4)),
        assessment(id="early", start=time(8)),
        assessment(id="previous", date=date(2026, 9, 30)),
    ]
    original = entries.copy()
    save_assessments(tmp_path, "2026-2027", "8A", entries)
    expected = [entries[2], entries[1], entries[0]]
    assert entries == original
    assert load_assessments(tmp_path, "2026-2027", "8A") == expected
    rows = load_toml(assessment_path)["assessments"]
    assert [row["id"] for row in rows] == [entry.id for entry in expected]
    assert "group_id" not in rows[0]
    assert rows[2]["group_id"] == "sa-1"


def test_duplicate_save_preserves_existing_file(tmp_path, assessment_path):
    save_assessments(tmp_path, "2026-2027", "8A", [assessment()])
    previous = assessment_path.read_bytes()
    with pytest.raises(AssessmentsFileError, match="Eintrag 2.*bmt-8"):
        save_assessments(tmp_path, "2026-2027", "8A", [assessment(), assessment()])
    assert assessment_path.read_bytes() == previous


def test_load_strings_defaults_and_unsorted_entries(tmp_path, assessment_path):
    rows = [
        dict(
            id="later",
            subject_id="mathematik",
            kind="ex",
            title="Test",
            date="2026-10-02",
            start="09:30",
            duration_minutes=20,
        ),
        dict(
            id="earlier",
            subject_id="mathematik",
            kind="sa",
            title="SA",
            date="2026-10-01",
            start="08:00",
            duration_minutes=60,
        ),
    ]
    save_toml(assessment_path, {"assessments": rows})
    entries = load_assessments(tmp_path, "2026-2027", "8A")
    assert [entry.id for entry in entries] == ["earlier", "later"]
    assert entries[0].start == time(8)
    assert entries[0].occupied_periods == ()
    assert entries[0].group_id is None


@pytest.mark.parametrize(
    "content,match",
    [
        ("invalid = [", "Ungültiges TOML"),
        ("", "Liste 'assessments'"),
        ('assessments = "wrong"', "Liste 'assessments'"),
        ("assessments = [1]", "Eintrag 1"),
        ("[[assessments]]\nid = 'test'", "Eintrag 1.*date"),
    ],
)
def test_malformed_files_report_path_and_entry(
    tmp_path, assessment_path, content, match
):
    assessment_path.write_text(content)
    with pytest.raises(AssessmentsFileError, match=match) as error:
        load_assessments(tmp_path, "2026-2027", "8A")
    assert str(assessment_path) in str(error.value)


@pytest.mark.parametrize(
    "changes",
    [
        {"kind": "unknown"},
        {"duration_minutes": True},
        {"date": "bad"},
        {"start": "bad"},
        {"occupied_periods": "12"},
        {"occupied_periods": [1, 1]},
    ],
)
def test_invalid_entry_is_identified(tmp_path, assessment_path, changes):
    save_assessments(tmp_path, "2026-2027", "8A", [assessment()])
    data = load_toml(assessment_path)
    data["assessments"][0].update(changes)
    save_toml(assessment_path, data)
    with pytest.raises(AssessmentsFileError, match="Eintrag 1"):
        load_assessments(tmp_path, "2026-2027", "8A")


def test_duplicate_ids_on_load(tmp_path, assessment_path):
    save_assessments(tmp_path, "2026-2027", "8A", [assessment()])
    data = load_toml(assessment_path)
    data["assessments"] *= 2
    save_toml(assessment_path, data)
    with pytest.raises(AssessmentsFileError, match="Eintrag 2.*bmt-8"):
        load_assessments(tmp_path, "2026-2027", "8A")
