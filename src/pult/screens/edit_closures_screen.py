from datetime import date, datetime
from typing import ClassVar
from zoneinfo import ZoneInfo

from rich.text import Text
from textual import on
from textual.app import ComposeResult
from textual.widgets import Static
from textual.widgets.option_list import Option

from pult.presentation import format_date
from pult.school.calendar import (
    load_class_closures,
    load_school_calendar,
    load_school_closures,
)
from pult.school.school_class import SchoolClass, load_school_classes
from pult.school.subject import load_subjects
from pult.school.timetable import get_timetable_path, load_timetable
from pult.screens.add_closure_screen import AddClosureScreen
from pult.screens.base_screen import (
    PultScreen,
)
from pult.screens.confirm_closure_deletion_screen import (
    ConfirmClosureDeletionScreen,
)
from pult.services.assessment_conflicts import closure_conflicts, conflict_message
from pult.services.closures import (
    ScopedClosure,
    add_closure,
    delete_closure,
    get_affected_lessons,
    get_default_closure_date,
)
from pult.widgets.button import Button
from pult.widgets.detail_table import format_detail_table
from pult.widgets.footer import PultFooter
from pult.widgets.scrolling import Horizontal, OptionList, Vertical, VerticalScroll


class EditClosuresScreen(PultScreen[None]):
    BINDINGS: ClassVar = [
        ("a", "create_closure", "Anlegen"),
        ("d", "delete_closure", "Löschen"),
        ("escape", "cancel", "Zurück"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.school_classes: list[SchoolClass] = []
        self.entries_by_option_id: dict[str, ScopedClosure] = {}
        self.selected_option_id: str | None = None

    def compose(self) -> ComposeResult:
        with Vertical(id="edit-closures-screen"):
            with Vertical(id="closures-frame") as frame:
                frame.border_title = "AUSFÄLLE"
                yield Static(id="closures-headings")
                yield Static("Noch keine Ausfälle eingetragen.", id="closures-empty")
                yield OptionList(id="closures")
            with VerticalScroll(id="closure-details", can_focus=False) as details:
                details.border_title = "BETROFFENE UNTERRICHTSTERMINE"
                yield Static(
                    "Wähle einen Ausfall aus.", id="closure-details-text", markup=False
                )

            with Horizontal(id="edit-closures-actions", classes="management-actions"):
                yield Button("Anlegen", variant="primary", id="create-closure")
                yield Button(
                    "Löschen",
                    variant="error",
                    id="delete-closure",
                    disabled=True,
                )
                yield Static(classes="action-spacer")
                yield Button("Zurück", id="close-closure-management")

        yield PultFooter()

    def on_mount(self) -> None:
        self.refresh_closures()

    def refresh_closures(self) -> None:
        config = self.app_config
        year = config.active_school_year
        self.school_classes = load_school_classes(config.root, year)

        entries = [
            ScopedClosure(closure, None)
            for closure in load_school_closures(config.root, year)
        ]
        for school_class in self.school_classes:
            entries.extend(
                ScopedClosure(closure, school_class.id)
                for closure in load_class_closures(
                    config.root,
                    year,
                    school_class.id,
                )
            )
        entries.sort(key=self._entry_sort_key)
        calendar = load_school_calendar(config.root, year)
        timetable = load_timetable(get_timetable_path(config.root, year))
        self.subjects = {subject.id: subject for subject in load_subjects(config.root)}
        self.affected = {
            entry: get_affected_lessons(entry, timetable, calendar) for entry in entries
        }

        self.entries_by_option_id = {
            f"closure-{index}": entry for index, entry in enumerate(entries)
        }
        option_list = self.query_one("#closures", OptionList)
        self.query_one("#closures-headings", Static).update(self._headings())
        option_list.clear_options()
        option_list.add_options(
            Option(self._format_entry(entry), id=option_id)
            for option_id, entry in self.entries_by_option_id.items()
        )

        self.selected_option_id = next(iter(self.entries_by_option_id), None)
        has_entries = bool(self.entries_by_option_id)
        self.query_one("#closures-empty").display = not has_entries
        self.update_details()
        self.query_one("#delete-closure", Button).disabled = not has_entries
        if has_entries:
            option_list.highlighted = 0
            option_list.focus()

    @staticmethod
    def _entry_sort_key(
        entry: ScopedClosure,
    ) -> tuple[date, date, str, str]:
        return (
            entry.closure.start,
            entry.closure.end,
            entry.school_class_id or "",
            entry.closure.name,
        )

    def _columns(self, values: tuple[str, str, str, str]) -> Text:
        width = max(74, self.query_one("#closures", OptionList).content_size.width)
        widths = (25, max(12, width - 25 - 15 - 21 - 6), 15, 21)
        result = Text(no_wrap=True, overflow="ellipsis")
        for index, (value, size) in enumerate(zip(values, widths)):
            part = Text(value)
            part.truncate(size, overflow="ellipsis")
            part.align("left", size)
            if index:
                result.append("  ")
            result.append_text(part)
        return result

    def _headings(self) -> Text:
        return self._columns(("Zeitraum", "Anlass", "Gilt für", "Entfallende Stunden"))

    def _format_entry(self, entry: ScopedClosure) -> Text:
        closure = entry.closure
        date_text = format_date(closure.start)
        if closure.end != closure.start:
            date_text += f" – {format_date(closure.end)}"
        return self._columns(
            (
                date_text,
                closure.name,
                entry.school_class_id or "Alle Klassen",
                str(len(self.affected[entry])),
            )
        )

    def on_resize(self) -> None:
        if self.is_mounted:
            self.call_after_refresh(self.refresh_columns)

    def refresh_columns(self) -> None:
        self.update_details()
        listing = self.query_one("#closures", OptionList)
        self.query_one("#closures-headings", Static).update(self._headings())
        for key, entry in self.entries_by_option_id.items():
            listing.replace_option_prompt(key, self._format_entry(entry))

    def update_details(self) -> None:
        entry = self.entries_by_option_id.get(self.selected_option_id or "")
        if entry is None:
            text = (
                "Wähle einen Ausfall aus."
                if self.entries_by_option_id
                else "Noch keine Ausfälle eingetragen."
            )
        else:
            lessons = self.affected[entry]
            text = f"{entry.closure.name} · {entry.school_class_id or 'Alle Klassen'}\n"
            text += "\n"
            if not lessons:
                text += (
                    "Keine Unterrichtstermine im hinterlegten Stundenplan betroffen."
                )
            else:
                text += f"{'Datum':<16} {'Stunde':<8} {'Klasse':<10} Fach\n"
                text += "\n".join(
                    f"{format_date(day):<16} {lesson.period:<8} {lesson.school_class_id:<10} {self.subjects[lesson.subject_id].name}"
                    for day, lesson in lessons
                )
        widget = self.query_one("#closure-details-text", Static)
        widget.update(
            format_detail_table(text, widget.content_size.width)
            if entry is not None and self.affected[entry]
            else text
        )
        self.query_one("#closure-details", VerticalScroll).scroll_home(animate=False)

    @on(OptionList.OptionHighlighted, "#closures")
    def closure_highlighted(
        self,
        event: OptionList.OptionHighlighted,
    ) -> None:
        self.selected_option_id = event.option_id
        self.update_details()

    @on(Button.Pressed, "#create-closure")
    def create_closure_pressed(self) -> None:
        self.action_create_closure()

    def action_create_closure(self) -> None:
        try:
            default_date = get_default_closure_date(
                self.app_config, datetime.now(ZoneInfo("Europe/Berlin")).date()
            )
        except (OSError, TypeError, ValueError) as error:
            self.notify(str(error), severity="error")
            return
        self.app.push_screen(
            AddClosureScreen(self.school_classes, default_date),
            self.closure_created,
        )

    def closure_created(self, result: ScopedClosure | None) -> None:
        if result is None:
            return

        try:
            add_closure(self.app_config, result)
        except (OSError, TypeError, ValueError) as error:
            self.notify(str(error), severity="error")
            return

        self.refresh_closures()
        self.notify(
            "Geplanter Ausfall gespeichert. Die Terminplanung berücksichtigt ihn ab sofort."
        )
        try:
            conflicts = closure_conflicts(self.app_config, result)
        except (OSError, ValueError) as error:
            self.notify(
                f"Ausfall gespeichert. Kollisionsprüfung nicht möglich: {error}",
                severity="warning",
            )
        else:
            if conflicts:
                self.notify(
                    "\n".join(
                        conflict_message(
                            item.school_class_id,
                            item.assessment,
                            result.closure,
                            number=item.number,
                        )
                        for item in conflicts
                    ),
                    title="Ausfall gespeichert · Terminkonflikt",
                    severity="warning",
                    timeout=12,
                )

    @on(Button.Pressed, "#delete-closure")
    def delete_closure_pressed(self) -> None:
        self.action_delete_closure()

    def action_delete_closure(self) -> None:
        if self.selected_option_id is None:
            return

        entry = self.entries_by_option_id[self.selected_option_id]

        def deletion_confirmed(confirmed: bool | None) -> None:
            if confirmed:
                self._delete_closure(entry)

        self.app.push_screen(
            ConfirmClosureDeletionScreen(entry),
            deletion_confirmed,
        )

    def _delete_closure(self, entry: ScopedClosure) -> None:
        try:
            delete_closure(self.app_config, entry)
        except (OSError, TypeError, ValueError) as error:
            self.notify(str(error), severity="error")
            return

        self.refresh_closures()
        self.notify("Geplanter Ausfall gelöscht. Die Terminplanung wurde aktualisiert.")

    @on(Button.Pressed, "#close-closure-management")
    def close_closure_management(self) -> None:
        self.action_cancel()

    def action_cancel(self) -> None:
        self.dismiss()
