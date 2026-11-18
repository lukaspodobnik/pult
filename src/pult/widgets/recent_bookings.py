"""Compact recent bookings, limited to the space left in the class dashboard."""

from rich.text import Text
from textual.widget import Widget

from pult.presentation import UNTITLED_LESSON, format_compact_date
from pult.progress.queries.summaries import RecentTeachingEntry
from pult.views.teaching_log_view import ORIGIN_LABELS, action_label


class RecentBookings(Widget, can_focus=False):
    COMPONENT_CLASSES = {
        "recent-bookings--muted",
        "recent-bookings--title",
        "recent-bookings--action",
        "recent-bookings--separator",
    }

    def __init__(self, entries: tuple[RecentTeachingEntry, ...]) -> None:
        super().__init__(classes="class-last-entry")
        self.entries = entries
        self.border_title = "ZULETZT"
        self.border_subtitle = "u · Protokoll"

    def update_entries(self, entries: tuple[RecentTeachingEntry, ...]) -> None:
        if self.entries != entries:
            self.entries = entries
            self.refresh()

    def on_resize(self) -> None:
        self.refresh()

    def _line(self, value: str, width: int, component: str) -> Text:
        text = Text(
            " ".join(value.split()),
            style=self.get_component_rich_style(f"recent-bookings--{component}"),
            no_wrap=True,
        )
        text.truncate(max(0, width), overflow="ellipsis")
        return text

    def _entry_lines(self, recent: RecentTeachingEntry, width: int) -> list[Text]:
        entry = recent.entry
        occurrence = (
            f"{entry.period}. Stunde"
            if entry.period is not None
            else ORIGIN_LABELS[entry.origin]
        )
        action = self._line(action_label(entry), width, "action")
        date_width = max(0, width - action.cell_len - 2)
        header = self._line(
            f"{format_compact_date(entry.date)} · {occurrence}", date_width, "muted"
        )
        header.pad_right(max(0, width - header.cell_len - action.cell_len))
        header.append_text(action)
        lines = [header]
        title = recent.title or (
            UNTITLED_LESSON if entry.lesson_id else recent.sequence_label
        )
        if title:
            lines.append(self._line(title, width, "title"))
        if entry.comment.strip():
            lines.append(self._line(entry.comment, width, "muted"))
        return lines

    def render(self) -> Text:
        width, height = self.content_size
        if width < 1 or height < 1:
            return Text()
        if not self.entries:
            return self._line(
                "Noch kein Protokolleintrag für dieses Fach", width, "muted"
            )

        lines: list[Text] = []
        for entry in self.entries:
            entry_lines = self._entry_lines(entry, width)
            separator_height = 1 if lines else 0
            if len(lines) + separator_height + len(entry_lines) > height:
                break
            if lines:
                lines.append(self._line("─" * width, width, "separator"))
            lines.extend(entry_lines)
        return Text("\n").join(lines)
