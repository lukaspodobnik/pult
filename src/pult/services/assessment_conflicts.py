"""Planungskonflikte zwischen Leistungsnachweisen und Ausfällen."""

from pult.config import AppConfig
from pult.presentation import format_date
from pult.school.assessment import Assessment
from pult.school.calendar import (
    Closure,
    load_class_closures,
    load_school_calendar,
    load_school_closures,
)
from pult.services.assessments import ScopedAssessment, list_assessments
from pult.services.closures import ScopedClosure


def conflicts_with_closure(entry: ScopedAssessment, closure: ScopedClosure) -> bool:
    """Ausfälle gelten ganztägig, auch für LNWs ohne eigene Unterrichtsstunden."""
    return (
        entry.assessment.completed_on is None
        and closure.school_class_id in (None, entry.school_class_id)
        and closure.closure.start <= entry.assessment.date <= closure.closure.end
    )


def assessment_conflicts(
    config: AppConfig, class_id: str, assessment: Assessment
) -> tuple[Closure, ...]:
    if assessment.completed_on is not None:
        return ()
    calendar = load_school_calendar(config.root, config.active_school_year)
    closures = [
        *calendar.closures,
        *load_school_closures(config.root, config.active_school_year),
        *load_class_closures(config.root, config.active_school_year, class_id),
    ]
    return tuple(
        dict.fromkeys(
            closure
            for closure in closures
            if closure.start <= assessment.date <= closure.end
        )
    )


def closure_conflicts(
    config: AppConfig, closure: ScopedClosure
) -> list[ScopedAssessment]:
    return [
        entry
        for entry in list_assessments(config)
        if conflicts_with_closure(entry, closure)
    ]


def conflict_message(
    class_id: str,
    assessment: Assessment,
    closure: Closure,
    *,
    number: int | None = None,
) -> str:
    label = (
        f"{number}. {assessment.kind.label}"
        if number is not None
        else assessment.kind.label
    )
    return (
        f"{label} „{assessment.title}“ · {class_id} am {format_date(assessment.date)} "
        f"liegt im Ausfall „{closure.name}“."
    )
