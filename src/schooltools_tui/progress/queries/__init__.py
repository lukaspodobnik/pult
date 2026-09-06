"""Öffentliche Abfragen; Implementierungen sind nach fachlicher Aufgabe aufgeteilt."""

from .dashboard import (
    DailyAdditionalEntry,
    DailyScheduleSummary,
    DailyTimetableEntry,
    HomeDashboardSummary,
    SchoolYearProgressSummary,
    get_daily_schedule,
    get_home_dashboard_summary,
    get_school_year_progress,
    get_time_highlighted_occurrence,
)
from .lessons import (
    get_available_next_sequences,
    get_next_lesson,
    get_suggested_next_sequence,
)
from .planning import (
    PlannedLesson,
    get_next_planned_lesson,
    get_next_planned_lesson_for_class,
    get_next_planned_lessons_for_class,
)
from .scheduling import (
    count_available_scheduled_occurrences,
    get_next_scheduled_occurrence,
)
from .summaries import (
    SequenceProgressSummary,
    SubjectProgressSummary,
    get_class_progress_summary,
)

__all__ = [
    "DailyAdditionalEntry",
    "DailyScheduleSummary",
    "DailyTimetableEntry",
    "HomeDashboardSummary",
    "SchoolYearProgressSummary",
    "get_daily_schedule",
    "get_home_dashboard_summary",
    "get_school_year_progress",
    "get_time_highlighted_occurrence",
    "get_available_next_sequences",
    "get_next_lesson",
    "get_suggested_next_sequence",
    "PlannedLesson",
    "get_next_planned_lesson",
    "get_next_planned_lesson_for_class",
    "get_next_planned_lessons_for_class",
    "count_available_scheduled_occurrences",
    "get_next_scheduled_occurrence",
    "SequenceProgressSummary",
    "SubjectProgressSummary",
    "get_class_progress_summary",
]
