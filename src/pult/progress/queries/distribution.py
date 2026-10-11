"""Stoffverteilung als gemeinsame Datengrundlage für Bildschirm und Export."""

from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import date, timedelta
from enum import StrEnum
from typing import TYPE_CHECKING

from pult.curriculum.sequence import sequence_sort_key
from pult.progress.class_progress import (
    TeachingAction,
    TeachingLogEntry,
    TeachingOrigin,
)
from pult.progress.queries.scheduling import WEEKDAYS, _get_last_scheduled_occurrence
from pult.school.calendar import Closure, ClosureKind

if TYPE_CHECKING:
    from pult.services.progress import PlanningData


def _is_penitence_day(closure: Closure) -> bool:
    # Im Kalender ein schulfreier Tag; in der Tabelle kein Ferienabschnitt.
    return (
        " ".join(closure.name.casefold().replace("-", " ").split()) == "buss und bettag"
    )


class DistributionKind(StrEnum):
    LESSON = "lesson"
    SEQUENCE = "sequence"
    HOLIDAY = "holiday"
    ASSESSMENT = "assessment"
    CANCELLED = "cancelled"
    UNRECORDED = "unrecorded"


@dataclass(frozen=True)
class DistributionRow:
    kind: DistributionKind
    date: date
    title: str
    notes: str = ""
    number: int | None = None
    period: int | None = None
    sequence_id: str | None = None
    lesson_id: str | None = None
    projected: bool = False


def build_distribution_plan(
    data: "PlanningData",
    school_class_id: str,
    subject_id: str,
    *,
    subject_labels: Mapping[str, str] | None = None,
) -> tuple[DistributionRow, ...]:
    """Protokollierte Termine bewahren; offene Stunden ab der aktiven Sequenz planen.

    Die Prognose setzt nach dem letzten verbuchten Unterrichtstermin an,
    unabhängig vom heutigen Datum. Zusatzunterricht wird dabei berücksichtigt.
    """
    school_class = next(c for c in data.school_classes if c.id == school_class_id)
    progress = data.progresses_by_class_id[school_class_id]
    calendar = data.school_calendar
    sequences = sorted(
        (
            s
            for s in data.sequences
            if s.grade_level == school_class.grade_level and s.subject_id == subject_id
        ),
        key=sequence_sort_key,
    )
    by_id = {s.id: s for s in sequences}
    active_id = next(
        a.sequence_id for a in progress.active_sequences if a.subject_id == subject_id
    )
    active_index = next(i for i, s in enumerate(sequences) if s.id == active_id)
    ordered = [*sequences[active_index:], *sequences[:active_index]]
    consumed = {
        (e.sequence_id, e.lesson_id)
        for e in progress.entries
        if e.subject_id == subject_id
        and e.action in {TeachingAction.COMPLETED, TeachingAction.SKIPPED}
    }
    pending = deque(
        (s, lesson)
        for s in ordered
        for lesson in s.lessons
        if (s.id, lesson.id) not in consumed
    )
    after = _get_last_scheduled_occurrence(progress, subject_id, calendar)
    after = max(
        [
            after,
            *(
                (entry.date, 99)
                for entry in progress.entries
                if entry.subject_id == subject_id
                and entry.origin is TeachingOrigin.ADDITIONAL
            ),
        ]
    )
    timetable = [
        t
        for t in data.timetable_entries
        if t.school_class_id == school_class_id and t.subject_id == subject_id
    ]
    closures = [
        *calendar.closures,
        *data.school_closures,
        *data.class_closures_by_class_id[school_class_id],
    ]
    holidays = [
        c
        for c in calendar.closures
        if c.kind is ClosureKind.SCHOOL_HOLIDAY and not _is_penitence_day(c)
    ]
    assessments = data.assessments_by_class_id.get(school_class_id, [])
    reserved = {
        (a.date, p)
        for a in assessments
        if a.subject_id == subject_id
        for p in a.occupied_periods
    }
    reserved.update(
        (e.date, p)
        for e in progress.entries
        if e.subject_id == subject_id
        for p in e.assessment_periods
    )
    recorded = {
        (e.date, e.period): e
        for e in progress.entries
        if e.subject_id == subject_id and e.origin is TeachingOrigin.SCHEDULED
    }
    events: list[tuple[date, int, int, DistributionRow]] = []
    for holiday in holidays:
        if (
            holiday.end >= calendar.first_school_day
            and holiday.start <= calendar.last_school_day
        ):
            day = max(holiday.start, calendar.first_school_day)
            events.append(
                (
                    day,
                    0,
                    0,
                    DistributionRow(DistributionKind.HOLIDAY, day, holiday.name),
                )
            )
    # Alle LNWs der Klasse erscheinen, auch außerhalb des ausgewählten Fachs.
    for assessment in assessments:
        periods = (
            assessment.occupied_periods if assessment.subject_id == subject_id else ()
        )
        notes = assessment.start.strftime("%H:%M")
        if assessment.subject_id != subject_id:
            label = (subject_labels or {}).get(
                assessment.subject_id, assessment.subject_id
            )
            notes += f" · {label}"
        for period in sorted(periods) or [0]:
            events.append(
                (
                    assessment.date,
                    period,
                    1,
                    DistributionRow(
                        DistributionKind.ASSESSMENT,
                        assessment.date,
                        f"{assessment.kind.abbreviation} · {assessment.title}",
                        notes,
                        period=period or None,
                    ),
                )
            )

    def log_row(entry: TeachingLogEntry) -> DistributionRow:
        sequence = by_id[entry.sequence_id]
        lesson = next(
            (lesson for lesson in sequence.lessons if lesson.id == entry.lesson_id),
            None,
        )
        if entry.action is TeachingAction.CANCELLED:
            return DistributionRow(
                DistributionKind.CANCELLED,
                entry.date,
                "Unterricht entfällt",
                entry.comment,
                period=entry.period,
            )
        notes = [lesson.notes if lesson else "", entry.comment]
        if entry.origin is TeachingOrigin.ADDITIONAL:
            notes.append("Zusatzunterricht")
        return DistributionRow(
            DistributionKind.LESSON,
            entry.date,
            lesson.title if lesson else "Anderer Unterrichtsinhalt",
            " · ".join(dict.fromkeys(n for n in notes if n)),
            period=entry.period,
            sequence_id=sequence.id,
            lesson_id=entry.lesson_id,
        )

    day = calendar.first_school_day
    while day <= calendar.last_school_day:
        if not any(h.start <= day <= h.end for h in holidays):
            periods = {
                t.period for t in timetable if t.weekday == WEEKDAYS[day.weekday()]
            }
            periods.update(
                e.period
                for e in progress.entries
                if e.date == day and e.subject_id == subject_id and e.period is not None
            )
            for period in sorted(periods):
                occurrence = (day, period)
                if occurrence in recorded:
                    row = log_row(recorded[occurrence])
                elif occurrence in reserved:
                    continue  # Der LNW steht als eigene Zeile an diesem Termin.
                elif reasons := [
                    "Buß und Bettag" if _is_penitence_day(c) else c.name
                    for c in closures
                    if c.start <= day <= c.end
                ]:
                    row = DistributionRow(
                        DistributionKind.CANCELLED,
                        day,
                        "Unterricht entfällt",
                        " · ".join(dict.fromkeys(reasons)),
                        period=period,
                    )
                elif occurrence <= after:
                    row = DistributionRow(
                        DistributionKind.UNRECORDED,
                        day,
                        "Nicht protokolliert",
                        period=period,
                    )
                elif pending:
                    sequence, lesson = pending.popleft()
                    row = DistributionRow(
                        DistributionKind.LESSON,
                        day,
                        lesson.title,
                        lesson.notes,
                        period=period,
                        sequence_id=sequence.id,
                        lesson_id=lesson.id,
                        projected=True,
                    )
                else:
                    row = DistributionRow(
                        DistributionKind.UNRECORDED,
                        day,
                        "Noch nicht verplant",
                        period=period,
                        projected=True,
                    )
                events.append((day, period, 2, row))
        day += timedelta(days=1)
    for index, entry in enumerate(progress.entries):
        if entry.subject_id == subject_id and entry.origin is TeachingOrigin.ADDITIONAL:
            events.append((entry.date, 99, index + 3, log_row(entry)))
    rows = []
    current_sequence = None
    number = 0
    for _, _, _, row in sorted(events, key=lambda event: event[:3]):
        if row.kind is DistributionKind.LESSON:
            assert row.sequence_id is not None
            if current_sequence != row.sequence_id:
                sequence = by_id[row.sequence_id]
                title = sequence.title
                if sequence.recommended_lesson_count is not None:
                    title += f" (ca. {sequence.recommended_lesson_count} Std.)"
                rows.append(
                    DistributionRow(
                        DistributionKind.SEQUENCE,
                        row.date,
                        title,
                        sequence_id=sequence.id,
                        projected=row.projected,
                    )
                )
                current_sequence = sequence.id
                number = 0
            number += 1
            row = replace(row, number=number)
        rows.append(row)
    return tuple(rows)
