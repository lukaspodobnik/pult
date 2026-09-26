"""Klassenübergreifende Terminverwaltung und Prüfung der Unterrichtszuordnung."""

from collections import defaultdict
from dataclasses import dataclass, replace
from datetime import date

from pult.config import AppConfig
from pult.presentation import WEEKDAYS
from pult.school.assessment import Assessment, load_assessments, save_assessments
from pult.school.calendar import load_school_calendar
from pult.school.school_class import load_school_class, load_school_classes
from pult.school.timetable import get_timetable_path, load_timetable


@dataclass(frozen=True)
class ScopedAssessment:
    school_class_id: str
    assessment: Assessment
    number: int


def list_assessments(config: AppConfig) -> list[ScopedAssessment]:
    result = []
    for school_class in load_school_classes(config.root, config.active_school_year):
        counters = defaultdict(int)
        for entry in load_assessments(
            config.root, config.active_school_year, school_class.id
        ):
            key = (entry.subject_id, entry.kind)
            counters[key] += 1
            result.append(ScopedAssessment(school_class.id, entry, counters[key]))
    return sorted(
        result,
        key=lambda item: (
            item.assessment.date,
            item.assessment.start,
            item.school_class_id,
            item.assessment.id,
        ),
    )


def validate_assessment(config: AppConfig, class_id: str, entry: Assessment) -> None:
    school_class = load_school_class(config.root, config.active_school_year, class_id)
    if entry.subject_id not in school_class.subject_ids:
        raise ValueError("Das Fach ist dieser Klasse nicht zugeordnet.")
    calendar = load_school_calendar(config.root, config.active_school_year)
    if not calendar.first_school_day <= entry.date <= calendar.last_school_day:
        raise ValueError(
            "Der Termin muss im Unterrichtszeitraum des Schuljahres liegen."
        )
    available = available_periods(config, class_id, entry.subject_id, entry.date)
    if not set(entry.occupied_periods) <= set(available):
        raise ValueError(
            "Die belegten Stunden passen nicht zu Klasse, Fach und Wochentag im Stundenplan."
        )


def available_periods(
    config: AppConfig, class_id: str, subject_id: str, day: date
) -> list[int]:
    weekday = dict(enumerate(key for key, _ in WEEKDAYS)).get(day.weekday())
    timetable = load_timetable(
        get_timetable_path(config.root, config.active_school_year)
    )
    return sorted(
        {
            item.period
            for item in timetable
            if item.weekday == weekday
            and item.school_class_id == class_id
            and item.subject_id == subject_id
        }
    )


def store_assessment(
    config: AppConfig, class_id: str, entry: Assessment, *, creating: bool
) -> None:
    validate_assessment(config, class_id, entry)
    entries = load_assessments(config.root, config.active_school_year, class_id)
    exists = any(item.id == entry.id for item in entries)
    if creating and exists:
        raise ValueError("Diese Leistungsnachweis-ID existiert bereits.")
    if not creating and not exists:
        raise ValueError("Der zu bearbeitende Leistungsnachweis existiert nicht mehr.")
    for item in entries:
        if (
            item.id != entry.id
            and item.date == entry.date
            and set(item.occupied_periods) & set(entry.occupied_periods)
        ):
            raise ValueError(
                "Eine belegte Stunde ist bereits einem anderen Leistungsnachweis zugeordnet."
            )
    # Eine ausgewählte Einzelprüfung erhält dieselbe Gruppe wie der neue Termin.
    if entry.group_id:
        partners = [
            item
            for item in entries
            if item.id != entry.id
            and (item.group_id == entry.group_id or item.id == entry.group_id)
        ]
        if any(item.subject_id != entry.subject_id for item in partners):
            raise ValueError("Verknüpfte Termine müssen zum selben Fach gehören.")
        entries = [
            replace(item, group_id=entry.group_id) if item in partners else item
            for item in entries
        ]
    entries = [item for item in entries if item.id != entry.id]
    entries.append(entry)
    save_assessments(config.root, config.active_school_year, class_id, entries)


def delete_assessment(config: AppConfig, class_id: str, entry_id: str) -> None:
    entries = load_assessments(config.root, config.active_school_year, class_id)
    remaining = [item for item in entries if item.id != entry_id]
    if len(entries) == len(remaining):
        raise ValueError("Der Leistungsnachweis existiert nicht mehr.")
    save_assessments(config.root, config.active_school_year, class_id, remaining)
