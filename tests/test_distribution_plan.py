from dataclasses import replace
from datetime import date, time

import pytest

from pult.curriculum.material import Lesson
from pult.curriculum.sequence import load_sequence, save_sequence
from pult.progress.class_progress import (
    ActiveSequence,
    TeachingAction,
    TeachingLogEntry,
    TeachingOrigin,
)
from pult.progress.queries.distribution import DistributionKind as Kind
from pult.progress.queries.distribution import build_distribution_plan
from pult.school.assessment import Assessment, AssessmentKind
from pult.school.calendar import Closure, ClosureKind
from pult.services.progress import PlanningData
from pult.storage import load_toml, save_toml


@pytest.fixture
def data(sequences, empty_progress, timetable_entries, school_calendar, school_class):
    return PlanningData(
        sequences,
        [school_class],
        {school_class.id: empty_progress},
        timetable_entries,
        school_calendar,
        [],
        {school_class.id: []},
        {school_class.id: []},
    )


def plan(data):
    return build_distribution_plan(data, "5A", "mathematik")


def lessons(data):
    return [row for row in plan(data) if row.kind is Kind.LESSON]


def log(day, period, action, lesson_id="lesson-1", origin=TeachingOrigin.SCHEDULED):
    return TeachingLogEntry(
        day,
        "mathematik",
        "sequence-1",
        action,
        origin,
        lesson_id=lesson_id,
        period=period,
    )


def test_projection_follows_curriculum_and_keeps_all_remaining_dates(data):
    rows = plan(data)
    assert [row.title for row in lessons(data)] == [
        "Zahlen ordnen",
        "Zahlen runden",
        "Addieren",
    ]
    assert [row.number for row in lessons(data)] == [1, 2, 1]
    assert all(row.projected for row in lessons(data))
    assert [row.title for row in rows if row.kind is Kind.SEQUENCE] == [
        "Natürliche Zahlen · Lehrplan: 2 Std.",
        "Rechenarten · Lehrplan: 1 Std.",
    ]
    assert len([row for row in rows if row.period is not None]) == 6
    assert [row.kind for row in rows if row.date == date(2026, 9, 14)] == [
        Kind.CANCELLED
    ] * 2
    assert rows[-1].title == "Noch nicht verplant"


def test_local_closure_shifts_lessons_without_counting(data, local_closure):
    data = replace(data, class_closures_by_class_id={"5A": [local_closure]})
    assert lessons(data)[-1].date == date(2026, 9, 16)
    cancelled = [row for row in plan(data) if row.date == local_closure.start]
    assert len(cancelled) == 1
    assert cancelled[0].number is None
    assert cancelled[0].notes == "Wandertag"


def test_vacation_is_one_full_width_row_no_individual_dates(data):
    holiday = Closure(
        "Herbstferien", ClosureKind.SCHOOL_HOLIDAY, date(2026, 9, 8), date(2026, 9, 15)
    )
    data = replace(
        data,
        school_calendar=replace(
            data.school_calendar, closures=(*data.school_calendar.closures, holiday)
        ),
    )
    during = [row for row in plan(data) if holiday.start <= row.date <= holiday.end]
    assert [(row.kind, row.title) for row in during] == [(Kind.HOLIDAY, "Herbstferien")]
    assert lessons(data)[-1].date == date(2026, 9, 16)


def test_actual_continuation_cancel_and_completion_use_real_count(data):
    progress = replace(
        data.progresses_by_class_id["5A"],
        entries=(
            log(date(2026, 9, 7), 1, TeachingAction.CONTINUED),
            log(date(2026, 9, 7), 2, TeachingAction.CANCELLED, None),
            log(date(2026, 9, 9), 1, TeachingAction.COMPLETED),
        ),
    )
    data = replace(data, progresses_by_class_id={"5A": progress})
    rows = lessons(data)
    assert [(row.title, row.number) for row in rows] == [
        ("Zahlen ordnen", 1),
        ("Zahlen ordnen", 2),
        ("Zahlen runden", 3),
    ]
    assert [row.projected for row in rows] == [False, False, True]
    assert next(row for row in plan(data) if row.kind is Kind.CANCELLED).number is None


def test_skipped_lesson_does_not_add_a_date_or_number(data):
    progress = replace(
        data.progresses_by_class_id["5A"],
        entries=(
            log(
                date(2026, 9, 7),
                None,
                TeachingAction.SKIPPED,
                origin=TeachingOrigin.NONE,
            ),
        ),
    )
    data = replace(data, progresses_by_class_id={"5A": progress})
    assert [(row.title, row.number) for row in lessons(data)] == [
        ("Zahlen runden", 1),
        ("Addieren", 1),
    ]


def test_assessments_inside_and_outside_own_lessons_and_other_subject(data):
    assessments = [
        Assessment(
            "sa",
            "mathematik",
            AssessmentKind.SCHOOL_EXAM,
            "Zahlen",
            date(2026, 9, 7),
            time(8),
            90,
            (1, 2),
        ),
        Assessment(
            "extern",
            "mathematik",
            AssessmentKind.YEAR_GROUP_TEST,
            "BMT",
            date(2026, 9, 8),
            time(10),
            45,
        ),
        Assessment(
            "deutsch",
            "deutsch",
            AssessmentKind.SCHOOL_EXAM,
            "Aufsatz",
            date(2026, 9, 10),
            time(8),
            45,
        ),
    ]
    data = replace(data, assessments_by_class_id={"5A": assessments})
    rows = plan(data)
    lnws = [row for row in rows if row.kind is Kind.ASSESSMENT]
    assert len(lnws) == 4
    assert all(row.number is None for row in lnws)
    assert lessons(data)[0].date == date(2026, 9, 9)
    assert lessons(data)[0].number == 1
    assert len([row for row in rows if row.date == date(2026, 9, 7)]) == 2
    assert "deutsch" in lnws[-1].notes


def test_unrecorded_past_is_not_invented(data):
    progress = replace(
        data.progresses_by_class_id["5A"],
        entries=(log(date(2026, 9, 9), 1, TeachingAction.COMPLETED),),
    )
    data = replace(data, progresses_by_class_id={"5A": progress})
    assert [row.title for row in plan(data) if row.date == date(2026, 9, 7)] == [
        "Nicht protokolliert"
    ] * 2
    assert lessons(data)[0].number == 1


def test_additional_lesson_preserved_and_future_not_projected_before_it(data):
    progress = replace(
        data.progresses_by_class_id["5A"],
        entries=(
            log(
                date(2026, 9, 8),
                None,
                TeachingAction.COMPLETED,
                origin=TeachingOrigin.ADDITIONAL,
            ),
        ),
    )
    data = replace(data, progresses_by_class_id={"5A": progress})
    assert [(row.date, row.number) for row in lessons(data)] == [
        (date(2026, 9, 8), 1),
        (date(2026, 9, 9), 2),
        (date(2026, 9, 16), 1),
    ]
    assert lessons(data)[0].notes == "Zusatzunterricht"


def test_active_sequence_defines_forecast_order(data):
    progress = replace(
        data.progresses_by_class_id["5A"],
        active_sequences=(ActiveSequence("mathematik", "sequence-2"),),
    )
    data = replace(data, progresses_by_class_id={"5A": progress})
    assert [row.title for row in lessons(data)] == [
        "Addieren",
        "Zahlen ordnen",
        "Zahlen runden",
    ]


def test_notes_roundtrip_metadata_assignment_and_validation(tmp_path, sequences):
    from pult.curriculum.material import save_lesson_metadata

    sequence = sequences[0]
    sequence.lessons[0].notes = "Computerraum · Übungstheke"
    save_sequence(tmp_path, sequence)
    loaded = load_sequence(tmp_path, 5, "mathematik", sequence.id)
    assert loaded.lessons[0].notes == "Computerraum · Übungstheke"
    directory = tmp_path / "sequences/5/mathematik" / sequence.id
    save_lesson_metadata(directory, loaded.lessons[0])
    assert (
        load_toml(directory / "stunden/lesson-1/stunde.toml")["hinweise"]
        == sequence.lessons[0].notes
    )
    path = directory / "stunden/lesson-1/stunde.toml"
    metadata = load_toml(path)
    metadata["hinweise"] = ["Falsch"]
    save_toml(path, metadata)
    with pytest.raises(ValueError, match="Hinweise"):
        load_sequence(tmp_path, 5, "mathematik", sequence.id)
    with pytest.raises(ValueError, match="Hinweise"):
        Lesson("test", "Test", notes=42)


def test_notes_come_from_lesson_and_log(data):
    data.sequences[0].lessons[0].notes = "Pausenhof · Freiarbeit"
    assert lessons(data)[0].notes == "Pausenhof · Freiarbeit"


@pytest.mark.parametrize("name", ["Buß- und Bettag", "Buß und Bettag"])
def test_penitence_day_shown_as_cancelled_lesson_not_vacation(data, name):
    closure = Closure(
        name, ClosureKind.SCHOOL_HOLIDAY, date(2026, 9, 9), date(2026, 9, 9)
    )
    data = replace(
        data,
        school_calendar=replace(
            data.school_calendar, closures=(*data.school_calendar.closures, closure)
        ),
    )
    rows = [row for row in plan(data) if row.date == closure.start]
    assert len(rows) == 1
    assert rows[0].kind is Kind.CANCELLED
    assert rows[0].title == "Unterricht entfällt"
    assert rows[0].notes == "Buß und Bettag"
    assert rows[0].number is None
    assert lessons(data)[-1].date == date(2026, 9, 16)
