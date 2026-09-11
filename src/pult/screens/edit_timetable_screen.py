from dataclasses import replace
from typing import ClassVar

from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import Button, Static

from pult.presentation import WEEKDAYS
from pult.school.period import Period, load_periods
from pult.school.school_class import SchoolClass, load_school_classes
from pult.school.subject import Subject, load_subjects
from pult.school.timetable import (
    TimetableEntry,
    get_timetable_path,
    load_timetable,
    save_timetable,
)
from pult.screens.base_screen import PultScreen
from pult.screens.confirmation_screen import ConfirmationScreen
from pult.screens.edit_timetable_entry_screen import (
    EditTimetabelEntryScreen,
    TimetableEditAction,
    TimetableEditResult,
)
from pult.widgets.footer import PultFooter
from pult.widgets.scrolling import DataTable, Horizontal, Vertical


class EditableTimetable(DataTable):
    BINDINGS: ClassVar = [Binding("enter", "select_cursor", "Stunde bearbeiten")]

    def on_focus(self) -> None:
        self.show_cursor = True

    def on_blur(self) -> None:
        self.show_cursor = False


class EditTimetableScreen(PultScreen[None]):
    BINDINGS: ClassVar = [
        ("escape", "cancel", "Abbrechen"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.entries_by_slot: dict[tuple[str, int], TimetableEntry] = {}
        self._initial_entries: dict[tuple[str, int], TimetableEntry] = {}
        self.school_classes: list[SchoolClass] = []
        self.subjects: list[Subject] = []
        self.subjects_by_id: dict[str, Subject] = {}
        self.periods: list[Period] = []
        self._last_entry: TimetableEntry | None = None
        self._column_width = 12
        self._row_heights: dict[int, int] = {}

    def compose(self) -> ComposeResult:
        with Vertical(id="edit-timetable-screen"):
            table = EditableTimetable(
                id="edit-schedule", cursor_type="cell", cell_padding=0, header_height=3
            )
            table.border_title = "STUNDENPLAN"
            yield table

            with Horizontal(
                id="edit-timetable-screen-actions", classes="management-actions"
            ):
                yield Static(classes="action-spacer")
                yield Button("Abbrechen", id="cancel-timetable-edit")
                yield Button(
                    "Speichern",
                    variant="primary",
                    id="save-timetable",
                )

        yield PultFooter()

    def on_mount(self) -> None:
        config = self.app_config
        path = get_timetable_path(config.root, config.active_school_year)
        self.entries_by_slot = {
            (entry.weekday, entry.period): entry for entry in load_timetable(path)
        }
        self._initial_entries = {
            slot: replace(entry) for slot, entry in self.entries_by_slot.items()
        }
        self.school_classes = load_school_classes(
            config.root, config.active_school_year
        )
        self.subjects = load_subjects(config.root)
        self.subjects_by_id = {subject.id: subject for subject in self.subjects}
        self.periods = load_periods(config.root)
        self.populate_timetable()
        self.query_one("#edit-schedule", DataTable).focus()

    def populate_timetable(self) -> None:
        table = self.query_one("#edit-schedule", DataTable)
        if not self.periods:
            return
        # 13 Zellen für Stundenlabel; Reserve für die Scrollbar.
        self._column_width = max(14, (table.content_size.width - 15) // 5)
        height, extra = divmod(max(0, table.content_size.height - 3), len(self.periods))
        self._row_heights = {
            period.number: max(3, height + (index < extra))
            for index, period in enumerate(self.periods)
        }
        cursor = table.cursor_coordinate
        table.clear(columns=True)

        for weekday, label in WEEKDAYS:
            first = weekday == WEEKDAYS[0][0]
            inner = self._column_width - 1 - first
            header = Text(no_wrap=True)
            header.append("\n" + ("│" if first else ""), style="dim")
            header.append(label.center(inner))
            header.append("│", style="dim")
            header.append(
                "\n" + ("┼" if first else "") + "─" * inner + "┼",
                style="dim",
            )
            table.add_column(header, key=weekday, width=self._column_width)

        for period in self.periods:
            cells = []
            for weekday, _ in WEEKDAYS:
                entry = self.entries_by_slot.get((weekday, period.number))
                cells.append(self._format_cell(entry, weekday, period.number))

            table.add_row(
                *cells,
                key=str(period.number),
                label=self._format_period(period),
                height=self._row_heights[period.number],
            )

        table.move_cursor(row=cursor.row, column=cursor.column)

    def on_resize(self) -> None:
        if self.is_mounted:
            self.call_after_refresh(self.populate_timetable)

    def _format_entry(self, entry: TimetableEntry | None) -> str:
        if entry is None:
            return ""
        subject = self.subjects_by_id[entry.subject_id]
        return f"{entry.school_class_id} · {subject.short_name}\n{entry.room}"

    def _format_period(self, period: Period) -> Text:
        height = self._row_heights[period.number]
        result = Text("\n" * ((height - 3) // 2), no_wrap=True)
        result.append(f"{period.number}. Stunde".center(13), style="bold")
        result.append("\n")
        result.append(
            f"{period.start:%H:%M}–{period.end:%H:%M}".center(13), style="dim"
        )
        return result

    def _format_cell(
        self, entry: TimetableEntry | None, weekday: str, period: int
    ) -> Text:
        """Zeichne Zellinhalt und Trennlinien ohne zusätzliche auswählbare Spalten."""
        height = self._row_heights[period]
        width = self._column_width
        first = weekday == WEEKDAYS[0][0]
        inner = width - 1 - first
        lines = self._format_entry(entry).split("\n") if entry else []
        offset = max(0, (height - len(lines)) // 2)
        result = Text(no_wrap=True)
        for index in range(height):
            content_index = index - offset
            content = lines[content_index] if 0 <= content_index < len(lines) else ""
            line = Text(content, style="bold" if content_index == 0 else "dim")
            line.truncate(inner, overflow="ellipsis")
            line.align("center", inner)
            if first:
                result.append("│", style="dim")
            result.append_text(line)
            result.append("│", style="dim")
            if index < height - 1:
                result.append("\n")
        return result

    @on(DataTable.CellSelected, "#edit-schedule")
    def edit_timetable_slot(self, event: DataTable.CellSelected) -> None:
        if not self.school_classes:
            self.notify("Lege zuerst mindestens eine Klasse an.", severity="warning")
            return

        weekday = event.cell_key.column_key.value
        period = event.cell_key.row_key.value
        assert weekday is not None
        assert period is not None

        slot = (str(weekday), int(period))
        self.app.push_screen(
            EditTimetabelEntryScreen(
                weekday=slot[0],
                period=slot[1],
                entry=self.entries_by_slot.get(slot),
                school_classes=self.school_classes,
                subjects=self.subjects,
                suggested_entry=self._last_entry,
            ),
            self.timetable_entry_edited,
        )

    def timetable_entry_edited(self, result: TimetableEditResult | None) -> None:
        if result is None:
            return

        slot = (result.entry.weekday, result.entry.period)
        if result.action is TimetableEditAction.SAVE:
            self.entries_by_slot[slot] = result.entry
            self._last_entry = result.entry
        else:
            self.entries_by_slot.pop(slot, None)

        table = self.query_one("#edit-schedule", DataTable)
        table.update_cell(
            str(slot[1]),
            slot[0],
            self._format_cell(self.entries_by_slot.get(slot), slot[0], slot[1]),
        )
        table.focus()

    @on(Button.Pressed, "#save-timetable")
    def save_changes(self) -> None:
        self.action_save()

    @on(Button.Pressed, "#cancel-timetable-edit")
    def cancel_changes(self) -> None:
        self.action_cancel()

    def action_save(self) -> None:
        config = self.app_config
        path = get_timetable_path(config.root, config.active_school_year)
        try:
            save_timetable(path, list(self.entries_by_slot.values()))
        except (OSError, ValueError) as error:
            self.notify(
                f"Stundenplan konnte nicht gespeichert werden: {error}",
                severity="error",
            )
            return
        self.dismiss()

    def action_cancel(self) -> None:
        if self.entries_by_slot == self._initial_entries:
            self.dismiss()
            return

        def discard_confirmed(confirmed: bool | None) -> None:
            if confirmed:
                self.dismiss()

        self.app.push_screen(
            ConfirmationScreen(
                "Änderungen verwerfen?",
                "Der Stundenplan enthält ungespeicherte Änderungen.\n"
                "Wenn du sie verwirfst, bleibt der zuletzt gespeicherte Plan erhalten.",
                confirm_id="confirm-discard-timetable",
                cancel_id="cancel-discard-timetable",
            ),
            discard_confirmed,
        )
