from typing import ClassVar

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, DataTable, Footer, Static

from schooltools_tui.presentation import WEEKDAYS
from schooltools_tui.school.period import Period, load_periods
from schooltools_tui.school.school_class import SchoolClass, load_school_classes
from schooltools_tui.school.subject import Subject, load_subjects
from schooltools_tui.school.timetable import (
    TimetableEntry,
    get_timetable_path,
    load_timetable,
    save_timetable,
)
from schooltools_tui.screens.base_screen import SchooltoolsScreen
from schooltools_tui.screens.edit_timetable_entry_screen import (
    EditTimetabelEntryScreen,
    TimetableEditAction,
    TimetableEditResult,
)


class EditTimetableScreen(SchooltoolsScreen[None]):
    BINDINGS: ClassVar = [
        ("ctrl+s", "save", "Speichern"),
        ("escape", "cancel", "Abbrechen"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.entries_by_slot: dict[tuple[str, int], TimetableEntry] = {}
        self.school_classes: list[SchoolClass] = []
        self.subjects: list[Subject] = []
        self.subjects_by_id: dict[str, Subject] = {}
        self.periods: list[Period] = []

    def compose(self) -> ComposeResult:
        with Vertical(id="edit-timetable-screen"):
            table = DataTable(id="edit-schedule", cursor_type="cell")
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

        yield Footer()

    def on_mount(self) -> None:
        config = self.app_config
        path = get_timetable_path(config.root, config.active_school_year)
        self.entries_by_slot = {
            (entry.weekday, entry.period): entry for entry in load_timetable(path)
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
        cursor = table.cursor_coordinate
        table.clear(columns=True)

        for weekday, label in WEEKDAYS:
            table.add_column(label, key=weekday)

        for period in self.periods:
            cells = []
            for weekday, _ in WEEKDAYS:
                entry = self.entries_by_slot.get((weekday, period.number))
                cells.append(self._format_entry(entry))

            table.add_row(*cells, key=str(period.number), label=str(period.number))

        table.move_cursor(row=cursor.row, column=cursor.column)

    def _format_entry(self, entry: TimetableEntry | None) -> str:
        if entry is None:
            return "--"
        subject = self.subjects_by_id[entry.subject_id]
        return f"{entry.school_class_id}-{subject.short_name} {entry.room}"

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
            ),
            self.timetable_entry_edited,
        )

    def timetable_entry_edited(self, result: TimetableEditResult | None) -> None:
        if result is None:
            return

        slot = (result.entry.weekday, result.entry.period)
        if result.action is TimetableEditAction.SAVE:
            self.entries_by_slot[slot] = result.entry
        else:
            self.entries_by_slot.pop(slot, None)

        table = self.query_one("#edit-schedule", DataTable)
        table.update_cell(
            str(slot[1]),
            slot[0],
            self._format_entry(self.entries_by_slot.get(slot)),
            update_width=True,
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
        save_timetable(path, list(self.entries_by_slot.values()))
        self.dismiss()

    def action_cancel(self) -> None:
        self.dismiss()
