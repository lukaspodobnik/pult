"""Bereite Daten für die Übersicht und die Klassenansicht ohne UI-Zugriffe auf."""

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from pult.config import AppConfig
from pult.curriculum.sequence import Sequence
from pult.progress.queries import (
    HomeDashboardSummary,
    SubjectProgressSummary,
    get_class_progress_summary,
    get_home_dashboard_summary,
)
from pult.school.assessment_requirements import load_assessment_requirements
from pult.school.period import Period, load_periods
from pult.school.school_class import SchoolClass
from pult.school.subject import Subject, load_subjects
from pult.school.timetable import TimetableEntry
from pult.services.progress import load_planning_data


@dataclass(frozen=True)
class HomeViewData:
    school_classes: list[SchoolClass]
    timetable_entries: list[TimetableEntry]
    subjects: list[Subject]
    periods: list[Period]
    sequences: list[Sequence]
    dashboard: HomeDashboardSummary


@dataclass(frozen=True)
class SchoolClassViewData:
    school_class: SchoolClass
    subject_id: str
    subjects: list[Subject]
    progress_summaries: tuple[SubjectProgressSummary, ...]


def load_home_view_data(
    config: AppConfig,
    *,
    sequences: list[Sequence] | None = None,
    current_datetime: datetime | None = None,
) -> HomeViewData:
    """Lade aktuelle Dashboarddaten; die Sequenzbibliothek kann geteilt werden."""
    data = load_planning_data(config, sequences=sequences)
    periods = load_periods(config.root)
    subjects = load_subjects(config.root)
    dashboard = get_home_dashboard_summary(
        current_datetime
        if current_datetime is not None
        else datetime.now(ZoneInfo("Europe/Berlin")),
        data.progresses_by_class_id,
        data.sequences,
        data.timetable_entries,
        periods,
        data.school_classes,
        data.school_calendar,
        data.school_closures,
        data.class_closures_by_class_id,
        data.assessments_by_class_id,
        load_assessment_requirements(config.root, config.active_school_year),
    )
    return HomeViewData(
        school_classes=data.school_classes,
        timetable_entries=data.timetable_entries,
        subjects=subjects,
        periods=periods,
        sequences=data.sequences,
        dashboard=dashboard,
    )


def load_school_class_view_data(
    config: AppConfig,
    school_class_id: str,
    subject_id: str | None = None,
    *,
    preferred_subject_id: str | None = None,
    sequences: list[Sequence] | None = None,
) -> SchoolClassViewData:
    """Lade aktuelle Klassendaten und fasse das ausgewählte Fach zusammen.

    Ohne explizite Auswahl bleibt ein gültiges bevorzugtes Fach erhalten; sonst
    wird das erste Fach gewählt. Eine ungültige explizite Auswahl wird abgewiesen.
    """
    data = load_planning_data(config, school_class_id, sequences=sequences)
    school_class = data.school_classes[0]
    if subject_id is None:
        subject_id = (
            preferred_subject_id
            if preferred_subject_id is not None
            and preferred_subject_id in school_class.subject_ids
            else school_class.subject_ids[0]
        )
    if subject_id not in school_class.subject_ids:
        raise ValueError("Das ausgewählte Fach gehört nicht zu dieser Klasse.")
    subjects = load_subjects(config.root)
    progress_summaries = get_class_progress_summary(
        data.progresses_by_class_id[school_class.id],
        data.sequences,
        data.timetable_entries,
        school_class,
        data.school_calendar,
        data.school_closures,
        data.class_closures_by_class_id[school_class.id],
        data.assessments_by_class_id[school_class.id],
    )
    return SchoolClassViewData(
        school_class=school_class,
        subject_id=subject_id,
        subjects=subjects,
        progress_summaries=tuple(
            summary
            for summary in progress_summaries
            if summary.subject_id == subject_id
        ),
    )
