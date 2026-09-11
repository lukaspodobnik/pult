from textual.app import ComposeResult
from textual.widgets import Static

from pult.presentation import format_school_year
from pult.progress.queries import (
    SchoolYearProgressSummary,
)
from pult.widgets.lesson_progress_bar import LessonProgressBar
from pult.widgets.scrolling import Horizontal, Vertical


class SchoolYearProgress(Vertical):
    """Zeige den vergangenen Anteil des Schuljahres."""

    def __init__(self, progress: SchoolYearProgressSummary) -> None:
        super().__init__(id="school-year-progress")
        self.progress_summary = progress
        self.border_title = f"Schuljahr {format_school_year(progress.school_year)}"

    def update_data(self, progress: SchoolYearProgressSummary) -> None:
        """Aktualisiere die Jahresanzeige und den bestehenden Balken."""
        self.progress_summary = progress
        self.border_title = f"Schuljahr {format_school_year(progress.school_year)}"
        self.query_one("#school-year-progress-label", Static).update(
            f"{progress.elapsed_day_count} von {progress.total_day_count} Tagen vergangen"
        )
        self.query_one(LessonProgressBar).update_counts(
            completed=progress.elapsed_day_count,
            skipped=0,
            total=progress.total_day_count,
        )
        self.query_one("#school-year-progress-percentage", Static).update(
            f"{progress.percentage} %"
        )

    def compose(self) -> ComposeResult:
        progress = self.progress_summary
        with Horizontal(id="school-year-progress-heading"):
            yield Static(
                f"{progress.elapsed_day_count} von {progress.total_day_count} Tagen vergangen",
                id="school-year-progress-label",
            )
            yield Static(
                f"{progress.percentage} %",
                id="school-year-progress-percentage",
            )
        yield LessonProgressBar(
            completed=progress.elapsed_day_count,
            skipped=0,
            total=progress.total_day_count,
            id="school-year-progress-bar",
        )
