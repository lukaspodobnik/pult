"""Lade frische Fortschrittsdaten mit optional geteilter Sequenzbibliothek."""

from dataclasses import dataclass

from schooltools_tui.config import AppConfig
from schooltools_tui.curriculum.sequence import Sequence, load_sequence_library
from schooltools_tui.progress.class_progress import (
    ClassProgress,
    load_class_progress,
    validate_class_progress,
)
from schooltools_tui.school.calendar import (
    Closure,
    SchoolCalendar,
    load_class_closures,
    load_school_calendar,
    load_school_closures,
)
from schooltools_tui.school.school_class import SchoolClass, load_school_classes
from schooltools_tui.school.timetable import (
    TimetableEntry,
    get_timetable_path,
    load_timetable,
)


@dataclass(frozen=True)
class ClassProgressData:
    school_class: SchoolClass
    sequences: list[Sequence]
    progress: ClassProgress


@dataclass(frozen=True)
class PlanningData:
    sequences: list[Sequence]
    school_classes: list[SchoolClass]
    progresses_by_class_id: dict[str, ClassProgress]
    timetable_entries: list[TimetableEntry]
    school_calendar: SchoolCalendar
    school_closures: list[Closure]
    class_closures_by_class_id: dict[str, list[Closure]]


def load_class_progress_data(
    config: AppConfig,
    school_class: SchoolClass,
    *,
    sequences: list[Sequence] | None = None,
) -> ClassProgressData:
    """Lade und validiere den Fortschritt einer Klasse gegen die Bibliothek.

    Bereits geladene Sequenzen, etwa aus dem App-Cache, können übergeben werden.
    Datei- und Validierungsfehler werden an den Aufrufer weitergegeben.
    """
    if sequences is None:
        sequences = load_sequence_library(config.root)
    progress = load_class_progress(
        config.root, config.active_school_year, school_class.id
    )
    validate_class_progress(progress, school_class, sequences)
    return ClassProgressData(school_class, sequences, progress)


def load_planning_data(
    config: AppConfig,
    school_class_id: str | None = None,
    *,
    sequences: list[Sequence] | None = None,
) -> PlanningData:
    """Lade Planungsdaten für alle Klassen oder nur für die angegebene Klasse.

    Bei Klassenwahl werden nur deren Protokoll und lokale Ausfälle geladen.
    Übergebene Sequenzen werden wiederverwendet, sonst wird die Bibliothek geladen.
    """
    classes = load_school_classes(config.root, config.active_school_year)
    if school_class_id is not None:
        classes_by_id = {school_class.id: school_class for school_class in classes}
        classes = [classes_by_id[school_class_id]]
    if sequences is None:
        sequences = load_sequence_library(config.root)
    progresses = {
        school_class.id: load_class_progress_data(
            config, school_class, sequences=sequences
        ).progress
        for school_class in classes
    }
    return PlanningData(
        sequences=sequences,
        school_classes=classes,
        progresses_by_class_id=progresses,
        timetable_entries=load_timetable(
            get_timetable_path(config.root, config.active_school_year)
        ),
        school_calendar=load_school_calendar(config.root, config.active_school_year),
        school_closures=load_school_closures(config.root, config.active_school_year),
        class_closures_by_class_id={
            school_class.id: load_class_closures(
                config.root, config.active_school_year, school_class.id
            )
            for school_class in classes
        },
    )
