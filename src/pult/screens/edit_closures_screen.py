from datetime import date, datetime
from typing import ClassVar
from zoneinfo import ZoneInfo

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    Button,
    OptionList,
    Static,
)
from textual.widgets.option_list import Option

from pult.presentation import format_date
from pult.school.calendar import (
    load_class_closures,
    load_school_closures,
)
from pult.school.school_class import SchoolClass, load_school_classes
from pult.screens.add_closure_screen import AddClosureScreen
from pult.screens.base_screen import (
    PultScreen,
)
from pult.screens.confirm_closure_deletion_screen import (
    ConfirmClosureDeletionScreen,
)
from pult.services.closures import (
    ScopedClosure,
    add_closure,
    delete_closure,
    get_default_closure_date,
)
from pult.widgets.footer import PultFooter


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
            closures = OptionList(id="closures")
            closures.border_title = "AUSFÄLLE"
            yield closures

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

        self.entries_by_option_id = {
            f"closure-{index}": entry for index, entry in enumerate(entries)
        }
        option_list = self.query_one("#closures", OptionList)
        option_list.clear_options()
        option_list.add_options(
            Option(self._format_entry(entry), id=option_id)
            for option_id, entry in self.entries_by_option_id.items()
        )

        self.selected_option_id = next(iter(self.entries_by_option_id), None)
        has_entries = bool(self.entries_by_option_id)
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

    @staticmethod
    def _format_entry(entry: ScopedClosure) -> str:
        closure = entry.closure
        date_text = format_date(closure.start)
        if closure.end != closure.start:
            date_text += f" – {format_date(closure.end)}"
        scope = entry.school_class_id or "Schulweit"
        return f"{date_text:<25} {scope:<12} {closure.name}"

    @on(OptionList.OptionHighlighted, "#closures")
    def closure_highlighted(
        self,
        event: OptionList.OptionHighlighted,
    ) -> None:
        self.selected_option_id = event.option_id

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
