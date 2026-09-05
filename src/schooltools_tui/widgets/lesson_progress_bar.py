from rich.text import Text
from textual.app import RenderResult
from textual.widget import Widget


class LessonProgressBar(Widget, can_focus=False):
    """A segmented bar for completed, skipped, and open curriculum lessons."""

    COMPONENT_CLASSES = {
        "lesson-progress-bar--completed",
        "lesson-progress-bar--skipped",
        "lesson-progress-bar--open",
    }

    def __init__(
        self,
        completed: int,
        skipped: int,
        total: int,
        *,
        id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(id=id, classes=classes)
        self._completed = 0
        self._skipped = 0
        self._total = 0
        self.update_counts(completed, skipped, total, refresh=False)

    @property
    def completed(self) -> int:
        return self._completed

    @property
    def skipped(self) -> int:
        return self._skipped

    @property
    def total(self) -> int:
        return self._total

    @property
    def progressed(self) -> int:
        return self.completed + self.skipped

    def update_counts(
        self,
        completed: int,
        skipped: int,
        total: int,
        *,
        refresh: bool = True,
    ) -> None:
        self._validate_counts(completed, skipped, total)
        self._completed = completed
        self._skipped = skipped
        self._total = total
        if refresh:
            self.refresh()

    def render(self) -> RenderResult:
        width = self.content_size.width
        if width < 1:
            return Text()

        if self.total == 0:
            completed_width = skipped_width = 0
        else:
            completed_width = round(width * self.completed / self.total)
            progressed_width = round(width * self.progressed / self.total)
            skipped_width = progressed_width - completed_width

        open_width = width - completed_width - skipped_width
        bar = Text()
        bar.append(
            "━" * completed_width,
            self.get_component_rich_style("lesson-progress-bar--completed"),
        )
        bar.append(
            "━" * skipped_width,
            self.get_component_rich_style("lesson-progress-bar--skipped"),
        )
        bar.append(
            "━" * open_width,
            self.get_component_rich_style("lesson-progress-bar--open"),
        )
        return bar

    @staticmethod
    def _validate_counts(completed: int, skipped: int, total: int) -> None:
        counts = {
            "Abgeschlossene Lessons": completed,
            "Übersprungene Lessons": skipped,
            "Gesamtzahl der Lessons": total,
        }
        for description, value in counts.items():
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(f"{description} müssen eine ganze Zahl sein.")
            if value < 0:
                raise ValueError(f"{description} dürfen nicht negativ sein.")

        if completed + skipped > total:
            raise ValueError(
                "Abgeschlossene und übersprungene Lessons dürfen zusammen "
                "nicht größer als die Gesamtzahl sein."
            )
