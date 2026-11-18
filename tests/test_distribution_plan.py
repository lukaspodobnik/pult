from dataclasses import replace
from datetime import date, datetime, time

import pytest

from pult.curriculum.material import Lesson
from pult.curriculum.sequence import load_sequence, save_sequence
from pult.progress.class_progress import (
    ActiveSequence,
    TeachingAction,
    TeachingLogEntry,
    TeachingOrigin,
    get_class_progress_path,
    load_class_progress,
    save_class_progress,
    validate_class_progress,
)
from pult.progress.commands import (
    LessonCompletionState,
    complete_lesson,
    complete_lesson_remainder,
    continue_lesson,
    set_active_sequence,
    undo_last_entry,
)
from pult.progress.queries import (
    PlannedLesson,
    get_class_progress_summary,
    get_next_scheduled_occurrence,
)
from pult.progress.queries.distribution import DistributionKind as Kind
from pult.progress.queries.distribution import build_distribution_plan
from pult.school.assessment import Assessment, AssessmentKind
from pult.school.calendar import Closure, ClosureKind
from pult.services.exports.distribution_export import distribution_html
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
    assert all(row.action is None for row in rows)
    assert [row.title for row in rows if row.kind is Kind.SEQUENCE] == [
        "Natürliche Zahlen (ca. 2 Std.)",
        "Rechenarten (ca. 1 Std.)",
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
            replace(
                log(date(2026, 9, 7), 1, TeachingAction.CONTINUED),
                comment="Sicherung noch offen",
            ),
            replace(
                log(date(2026, 9, 7), 2, TeachingAction.CANCELLED, None),
                comment="Klassenversammlung",
            ),
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
    assert [row.action for row in rows] == [
        TeachingAction.CONTINUED,
        TeachingAction.COMPLETED,
        None,
    ]
    assert rows[0].notes == "Sicherung noch offen"
    cancelled = next(row for row in plan(data) if row.kind is Kind.CANCELLED)
    assert cancelled.number is None
    assert cancelled.action is TeachingAction.CANCELLED
    assert cancelled.notes == "Klassenversammlung"


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


@pytest.mark.parametrize("at_sequence_end", [False, True])
def test_remainder_shares_period_note_and_count_and_survives_save_and_undo(
    data, planned_lesson, tmp_path, at_sequence_end
):
    progress = data.progresses_by_class_id["5A"]
    if at_sequence_end:
        progress = complete_lesson(progress, planned_lesson, data.sequences).progress
        planned_lesson = replace(
            planned_lesson, lesson=data.sequences[0].lessons[1], period=2
        )
    continued = continue_lesson(progress, planned_lesson, data.sequences, "Rest offen")

    def next_occurrence(progress):
        return get_next_scheduled_occurrence(
            progress,
            data.timetable_entries,
            "5A",
            "mathematik",
            data.school_calendar,
            [],
        )

    def summary(progress):
        return get_class_progress_summary(
            progress,
            data.sequences,
            data.timetable_entries,
            data.school_classes[0],
            data.school_calendar,
            [],
            [],
        )[0]

    occurrence = next_occurrence(continued)
    remainder_plan = replace(planned_lesson, date=occurrence[0], period=occurrence[1])
    result = complete_lesson_remainder(continued, remainder_plan, data.sequences)
    finished = result.progress
    if at_sequence_end:
        assert result.state is LessonCompletionState.NEEDS_NEXT_SEQUENCE
        finished = set_active_sequence(
            finished, "mathematik", "sequence-2", 5, data.sequences
        )
    else:
        assert result.state is LessonCompletionState.CONTINUES_SEQUENCE
    validate_class_progress(finished, data.school_classes[0], data.sequences)
    assert next_occurrence(finished) == occurrence
    before, after = summary(continued), summary(finished)
    assert after.completed_lesson_count == before.completed_lesson_count + 1
    assert after.skipped_lesson_count == before.skipped_lesson_count
    assert after.available_period_count == before.available_period_count
    assert sum(s.held_lesson_count for s in after.sequences) == sum(
        s.held_lesson_count for s in before.sequences
    )
    assert finished.entries[:-1] == continued.entries
    assert finished.entries[-1].origin is TeachingOrigin.SHARED

    path = get_class_progress_path(tmp_path, "2026-2027", "5A")
    path.parent.mkdir(parents=True)
    save_class_progress(tmp_path, "2026-2027", "5A", finished)
    assert load_class_progress(tmp_path, "2026-2027", "5A") == finished

    next_plan = after.next_planned_lesson
    assert isinstance(next_plan, PlannedLesson)
    assert (next_plan.date, next_plan.period) == occurrence
    booked = complete_lesson(finished, next_plan, data.sequences).progress
    assert next_occurrence(booked) != occurrence
    assert summary(booked).available_period_count == after.available_period_count - 1
    assert (
        sum(s.held_lesson_count for s in summary(booked).sequences)
        == sum(s.held_lesson_count for s in after.sequences) + 1
    )

    note = f"Rest von „{planned_lesson.lesson.title}“ abgeschlossen"
    original_row_count = len([row for row in plan(data) if row.period is not None])
    for current_progress in (finished, booked, undo_last_entry(booked)):
        rows = plan(replace(data, progresses_by_class_id={"5A": current_progress}))
        assert (
            len([row for row in rows if row.period is not None]) == original_row_count
        )
        matching = [row for row in rows if (row.date, row.period) == occurrence]
        assert len(matching) == 1
        row = matching[0]
        assert row.title == next_plan.lesson.title
        assert row.number == (1 if at_sequence_end else 2)
        assert row.notes == " · ".join(filter(None, [next_plan.lesson.notes, note]))
        assert row.projected == (current_progress != booked)
        html = distribution_html(
            tuple(rows),
            school_class_id="5A",
            subject_name="Mathematik",
            school_year="2026-2027",
            generated_at=datetime(2026, 9, 7),
        )
        assert html.count(note) == 1

    assert undo_last_entry(booked, subject_id="mathematik") == finished
    restored = undo_last_entry(finished, subject_id="mathematik")
    assert restored == continued
    rows = plan(replace(data, progresses_by_class_id={"5A": restored}))
    assert not any(note in row.notes for row in rows)


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
    assert all(row.action is None for row in lnws)
    assert lessons(data)[0].date == date(2026, 9, 9)
    assert lessons(data)[0].number == 1
    assert len([row for row in rows if row.date == date(2026, 9, 7)]) == 2
    assert "deutsch" in lnws[-1].notes

    completed = [replace(a, completed_on=a.date) for a in assessments]
    completed_data = replace(data, assessments_by_class_id={"5A": completed})
    completed_rows = [r for r in plan(completed_data) if r.kind is Kind.ASSESSMENT]
    assert len(completed_rows) == 4
    assert all(r.action is TeachingAction.ASSESSMENT_COMPLETED for r in completed_rows)


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
    assert all(row.action is None for row in plan(data) if row.kind is Kind.UNRECORDED)


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
    assert lessons(data)[0].notes == "Zusätzlicher Termin"
    assert lessons(data)[0].action is TeachingAction.COMPLETED
    assert all(row.action is None for row in lessons(data)[1:])


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
    progress = replace(
        data.progresses_by_class_id["5A"],
        entries=(
            replace(
                log(date(2026, 9, 7), 1, TeachingAction.CONTINUED),
                comment="Sicherung noch offen",
            ),
        ),
    )
    data = replace(data, progresses_by_class_id={"5A": progress})
    assert lessons(data)[0].notes == "Pausenhof · Freiarbeit · Sicherung noch offen"


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


def test_spontaneous_title_real_number_and_unchanged_next_plan_lesson(
    data, planned_lesson
):
    from pult.progress.commands import complete_lesson, record_spontaneous_lesson

    progress = complete_lesson(
        data.progresses_by_class_id["5A"], planned_lesson, data.sequences
    ).progress
    spontaneous_slot = replace(
        planned_lesson, period=2, lesson=data.sequences[0].lessons[1]
    )
    progress = record_spontaneous_lesson(
        progress, spontaneous_slot, data.sequences, "Übung vor der Schulaufgabe"
    )
    data = replace(data, progresses_by_class_id={"5A": progress})
    rows = lessons(data)
    assert [(row.title, row.number) for row in rows[:3]] == [
        ("Zahlen ordnen", 1),
        ("Übung vor der Schulaufgabe", 2),
        ("Zahlen runden", 3),
    ]
    assert (rows[1].date, rows[1].period, rows[1].lesson_id, rows[1].projected) == (
        date(2026, 9, 7),
        2,
        None,
        False,
    )
    assert rows[1].notes == ""
    assert rows[1].action is TeachingAction.OTHER
    assert rows[2].action is None
    assert (rows[2].date, rows[2].period, rows[2].projected) == (
        date(2026, 9, 9),
        1,
        True,
    )
