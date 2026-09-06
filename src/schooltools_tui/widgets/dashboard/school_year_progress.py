from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import ProgressBar, Static

from schooltools_tui.presentation import format_school_year
from schooltools_tui.progress.queries import (
    SchoolYearProgressSummary,
)


class SchoolYearProgress(Horizontal):
    """Zeige den vergangenen Anteil des Schuljahres."""

    def __init__(self, progress: SchoolYearProgressSummary) -> None:
        super().__init__(id="school-year-progress")
        self.progress_summary = progress

    def compose(self) -> ComposeResult:
        progress = self.progress_summary
        yield Static(
            f"Schuljahr {format_school_year(progress.school_year)}",
            id="school-year-progress-label",
        )
        progress_bar = ProgressBar(
            total=progress.total_day_count,
            show_percentage=False,
            show_eta=False,
            id="school-year-progress-bar",
        )
        progress_bar.progress = progress.elapsed_day_count
        yield progress_bar
        yield Static(
            f"{progress.percentage} %",
            id="school-year-progress-percentage",
        )
