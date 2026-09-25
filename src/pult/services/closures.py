"""Laden, Prüfen und Speichern lokaler Ausfälle ohne UI-Abhängigkeiten."""

from dataclasses import dataclass
from datetime import date, timedelta

from pult.config import AppConfig
from pult.school.calendar import (
    Closure,
    SchoolCalendar,
    has_school_day,
    is_school_day,
    load_class_closures,
    load_school_calendar,
    load_school_closures,
    save_class_closures,
    save_school_closures,
)
from pult.school.timetable import TimetableEntry


@dataclass(frozen=True)
class ScopedClosure:
    """Ein lokaler Ausfall für eine Klasse oder die gesamte Schule (None)."""

    closure: Closure
    school_class_id: str | None


def validate_closure(config: AppConfig, entry: ScopedClosure) -> None:
    """Prüfe Schuljahresgrenzen und mindestens einen noch verfügbaren Schultag."""
    calendar = load_school_calendar(config.root, config.active_school_year)
    closure = entry.closure
    if (
        closure.start < calendar.first_school_day
        or closure.end > calendar.last_school_day
    ):
        raise ValueError(
            "Der Ausfall muss vollständig innerhalb des Unterrichtszeitraums liegen."
        )
    closures = load_school_closures(config.root, config.active_school_year)
    if entry.school_class_id is not None:
        closures.extend(
            load_class_closures(
                config.root, config.active_school_year, entry.school_class_id
            )
        )
    if not has_school_day(calendar, closure.start, closure.end, closures):
        raise ValueError("Der Zeitraum enthält keinen verfügbaren Unterrichtstag.")


def get_default_closure_date(config: AppConfig, today: date) -> date:
    """Suche ab heute einen freien Schultag, ersatzweise rückwärts ab Jahresende."""
    calendar = load_school_calendar(config.root, config.active_school_year)
    closures = load_school_closures(config.root, config.active_school_year)
    candidate = min(max(today, calendar.first_school_day), calendar.last_school_day)
    while candidate <= calendar.last_school_day:
        if is_school_day(calendar, candidate, closures):
            return candidate
        candidate += timedelta(days=1)
    candidate = calendar.last_school_day
    while candidate >= calendar.first_school_day:
        if is_school_day(calendar, candidate, closures):
            return candidate
        candidate -= timedelta(days=1)
    raise ValueError("Das Schuljahr enthält keinen verfügbaren Unterrichtstag.")


def _load_scoped_closures(
    config: AppConfig, school_class_id: str | None
) -> list[Closure]:
    if school_class_id is None:
        return load_school_closures(config.root, config.active_school_year)
    return load_class_closures(config.root, config.active_school_year, school_class_id)


def _save_scoped_closures(
    config: AppConfig, school_class_id: str | None, closures: list[Closure]
) -> None:
    if school_class_id is None:
        save_school_closures(config.root, config.active_school_year, closures)
    else:
        save_class_closures(
            config.root, config.active_school_year, school_class_id, closures
        )


def add_closure(config: AppConfig, entry: ScopedClosure) -> None:
    """Prüfe den Ausfall erneut und speichere ihn in der passenden Reichweite."""
    validate_closure(config, entry)
    closures = _load_scoped_closures(config, entry.school_class_id)
    closures.append(entry.closure)
    _save_scoped_closures(config, entry.school_class_id, closures)


def delete_closure(config: AppConfig, entry: ScopedClosure) -> None:
    """Entferne genau einen vorhandenen Ausfall aus der passenden Reichweite."""
    closures = _load_scoped_closures(config, entry.school_class_id)
    closures.remove(entry.closure)
    _save_scoped_closures(config, entry.school_class_id, closures)


def get_affected_lessons(
    entry: ScopedClosure,
    timetable: list[TimetableEntry],
    calendar: SchoolCalendar,
) -> tuple[tuple[date, TimetableEntry], ...]:
    """Stundenplantermine im Ausfallzeitraum, ohne Wochenenden und Ferien.

    Jeder Ausfall wird einzeln betrachtet; überlappende Ausfälle dürfen daher
    denselben Termin ausweisen. Es handelt sich nicht um zusätzliche Ausfälle.
    """
    weekdays = ("monday", "tuesday", "wednesday", "thursday", "friday")
    candidate = max(entry.closure.start, calendar.first_school_day)
    end = min(entry.closure.end, calendar.last_school_day)
    result = []
    while candidate <= end:
        if is_school_day(calendar, candidate):
            result.extend(
                (candidate, lesson)
                for lesson in timetable
                if lesson.weekday == weekdays[candidate.weekday()]
                and (
                    entry.school_class_id is None
                    or lesson.school_class_id == entry.school_class_id
                )
            )
        candidate += timedelta(days=1)
    return tuple(
        sorted(
            result,
            key=lambda item: (
                item[0],
                item[1].period,
                item[1].school_class_id,
                item[1].subject_id,
            ),
        )
    )
