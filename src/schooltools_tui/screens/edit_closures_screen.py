from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import ClassVar
from zoneinfo import ZoneInfo

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    OptionList,
    Select,
)
from textual.widgets.option_list import Option

from schooltools_tui.presentation import DATE_INPUT_HINT, format_date, parse_date
from schooltools_tui.school.calendar import (
    Closure,
    ClosureKind,
    has_school_day,
    is_school_day,
    load_class_closures,
    load_school_calendar,
    load_school_closures,
    save_class_closures,
    save_school_closures,
)
from schooltools_tui.school.school_class import SchoolClass, load_school_classes
from schooltools_tui.screens.base_screen import (
    SchooltoolsModalScreen,
    SchooltoolsScreen,
)

SCHOOL_SCOPE = "school"
CLASS_SCOPE_PREFIX = "class:"


@dataclass(frozen=True)
class ClosureFormResult:
    closure: Closure
    school_class_id: str | None


@dataclass(frozen=True)
class ClosureListEntry:
    closure: Closure
    school_class_id: str | None


class AddClosureScreen(SchooltoolsModalScreen[ClosureFormResult | None]):
    BINDINGS: ClassVar = [("escape", "cancel", "Abbrechen")]

    def __init__(self, school_classes: list[SchoolClass]) -> None:
        super().__init__()
        self.school_classes = school_classes

    def compose(self) -> ComposeResult:
        default_date = format_date(self._get_default_date())
        scope_options = [("Gesamte Schule", SCHOOL_SCOPE)]
        scope_options.extend(
            (school_class.id, CLASS_SCOPE_PREFIX + school_class.id)
            for school_class in self.school_classes
        )

        with Vertical(id="add-closure-dialog"):
            yield Label("Ausfall anlegen", id="add-closure-title")
            yield Label("Bezeichnung", classes="closure-field-label")
            yield Input(
                placeholder="z. B. Wandertag",
                id="closure-name",
            )
            yield Label("Reichweite", classes="closure-field-label")
            yield Select(
                scope_options,
                value=SCHOOL_SCOPE,
                allow_blank=False,
                id="closure-scope",
            )
            yield Label("Startdatum", classes="closure-field-label")
            yield Input(
                value=default_date,
                placeholder=DATE_INPUT_HINT,
                id="closure-start",
            )
            yield Label("Enddatum", classes="closure-field-label")
            yield Input(
                value=default_date,
                placeholder=DATE_INPUT_HINT,
                id="closure-end",
            )

            with Horizontal(id="add-closure-actions"):
                yield Button("Abbrechen", id="cancel-closure")
                yield Button(
                    "Anlegen",
                    variant="primary",
                    id="submit-closure",
                )

    @on(Button.Pressed, "#submit-closure")
    def submit_closure(self) -> None:
        try:
            scope = str(self.query_one("#closure-scope", Select).value)
            school_class_id = self._get_school_class_id(scope)
            closure = Closure(
                name=self.query_one("#closure-name", Input).value,
                kind=ClosureKind.LOCAL,
                start=parse_date(
                    self.query_one("#closure-start", Input).value,
                    "Das Startdatum",
                ),
                end=parse_date(
                    self.query_one("#closure-end", Input).value,
                    "Das Enddatum",
                ),
            )
            self._validate_has_school_day(closure, school_class_id)
        except (OSError, TypeError, ValueError) as error:
            self.notify(str(error), severity="error")
            return

        self.dismiss(ClosureFormResult(closure, school_class_id))

    def _validate_has_school_day(
        self,
        closure: Closure,
        school_class_id: str | None,
    ) -> None:
        config = self.app_config
        year = config.active_school_year
        calendar = load_school_calendar(config.root, year)
        if (
            closure.start < calendar.first_school_day
            or closure.end > calendar.last_school_day
        ):
            raise ValueError(
                "Der Ausfall muss vollständig innerhalb des "
                "Unterrichtszeitraums liegen."
            )

        local_closures = load_school_closures(config.root, year)
        if school_class_id is not None:
            local_closures.extend(
                load_class_closures(config.root, year, school_class_id)
            )

        if not has_school_day(
            calendar,
            closure.start,
            closure.end,
            local_closures,
        ):
            raise ValueError("Der Zeitraum enthält keinen verfügbaren Unterrichtstag.")

    def _get_default_date(self) -> date:
        config = self.app_config
        year = config.active_school_year
        calendar = load_school_calendar(config.root, year)
        school_closures = load_school_closures(config.root, year)
        today = datetime.now(ZoneInfo("Europe/Berlin")).date()
        candidate = min(
            max(today, calendar.first_school_day),
            calendar.last_school_day,
        )

        while candidate <= calendar.last_school_day:
            if is_school_day(calendar, candidate, school_closures):
                return candidate
            candidate += timedelta(days=1)

        candidate = calendar.last_school_day
        while candidate >= calendar.first_school_day:
            if is_school_day(calendar, candidate, school_closures):
                return candidate
            candidate -= timedelta(days=1)

        raise ValueError("Das Schuljahr enthält keinen verfügbaren Unterrichtstag.")

    @staticmethod
    def _get_school_class_id(scope: str) -> str | None:
        if scope == SCHOOL_SCOPE:
            return None
        if scope.startswith(CLASS_SCOPE_PREFIX):
            return scope.removeprefix(CLASS_SCOPE_PREFIX)
        raise ValueError("Die Reichweite des Ausfalls ist ungültig.")

    @on(Button.Pressed, "#cancel-closure")
    def cancel_closure(self) -> None:
        self.action_cancel()

    def action_cancel(self) -> None:
        self.dismiss(None)


class ConfirmClosureDeletionScreen(SchooltoolsModalScreen[bool]):
    BINDINGS: ClassVar = [("escape", "cancel", "Abbrechen")]

    def __init__(self, entry: ClosureListEntry) -> None:
        super().__init__()
        self.entry = entry

    def compose(self) -> ComposeResult:
        scope = self.entry.school_class_id or "gesamte Schule"
        with Vertical(id="confirm-closure-deletion-dialog"):
            yield Label("Ausfall löschen", id="confirm-closure-deletion-title")
            yield Label(
                f"Soll '{self.entry.closure.name}' für {scope} wirklich "
                "gelöscht werden?",
                id="confirm-closure-deletion-message",
            )
            with Horizontal(id="confirm-closure-deletion-actions"):
                yield Button("Abbrechen", id="cancel-closure-deletion")
                yield Button(
                    "Löschen",
                    variant="error",
                    id="confirm-closure-deletion",
                )

    @on(Button.Pressed, "#confirm-closure-deletion")
    def confirm_deletion(self) -> None:
        self.dismiss(True)

    @on(Button.Pressed, "#cancel-closure-deletion")
    def cancel_deletion(self) -> None:
        self.action_cancel()

    def action_cancel(self) -> None:
        self.dismiss(False)


class EditClosuresScreen(SchooltoolsScreen[None]):
    BINDINGS: ClassVar = [
        ("a", "create_closure", "Anlegen"),
        ("d", "delete_closure", "Löschen"),
        ("escape", "cancel", "Zurück"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.school_classes: list[SchoolClass] = []
        self.entries_by_option_id: dict[str, ClosureListEntry] = {}
        self.selected_option_id: str | None = None

    def compose(self) -> ComposeResult:
        yield Header()

        with Vertical(id="edit-closures-screen"):
            yield Label("Ausfälle verwalten", id="edit-closures-title")
            yield OptionList(id="closures")

            with Horizontal(id="edit-closures-actions"):
                yield Button("Zurück", id="close-closure-management")
                yield Button(
                    "Löschen",
                    variant="error",
                    id="delete-closure",
                    disabled=True,
                )
                yield Button(
                    "Anlegen",
                    variant="primary",
                    id="create-closure",
                )

        yield Footer()

    def on_mount(self) -> None:
        self.refresh_closures()

    def refresh_closures(self) -> None:
        config = self.app_config
        year = config.active_school_year
        self.school_classes = load_school_classes(config.root, year)

        entries = [
            ClosureListEntry(closure, None)
            for closure in load_school_closures(config.root, year)
        ]
        for school_class in self.school_classes:
            entries.extend(
                ClosureListEntry(closure, school_class.id)
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
        entry: ClosureListEntry,
    ) -> tuple[date, date, str, str]:
        return (
            entry.closure.start,
            entry.closure.end,
            entry.school_class_id or "",
            entry.closure.name,
        )

    @staticmethod
    def _format_entry(entry: ClosureListEntry) -> str:
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
        self.app.push_screen(
            AddClosureScreen(self.school_classes),
            self.closure_created,
        )

    def closure_created(self, result: ClosureFormResult | None) -> None:
        if result is None:
            return

        config = self.app_config
        year = config.active_school_year
        try:
            if result.school_class_id is None:
                closures = load_school_closures(config.root, year)
                closures.append(result.closure)
                save_school_closures(config.root, year, closures)
            else:
                closures = load_class_closures(
                    config.root,
                    year,
                    result.school_class_id,
                )
                closures.append(result.closure)
                save_class_closures(
                    config.root,
                    year,
                    result.school_class_id,
                    closures,
                )
        except (OSError, TypeError, ValueError) as error:
            self.notify(str(error), severity="error")
            return

        self.refresh_closures()
        self.notify("Ausfall angelegt.")

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

    def _delete_closure(self, entry: ClosureListEntry) -> None:
        config = self.app_config
        year = config.active_school_year
        try:
            if entry.school_class_id is None:
                closures = load_school_closures(config.root, year)
                closures.remove(entry.closure)
                save_school_closures(config.root, year, closures)
            else:
                closures = load_class_closures(
                    config.root,
                    year,
                    entry.school_class_id,
                )
                closures.remove(entry.closure)
                save_class_closures(
                    config.root,
                    year,
                    entry.school_class_id,
                    closures,
                )
        except (OSError, TypeError, ValueError) as error:
            self.notify(str(error), severity="error")
            return

        self.refresh_closures()
        self.notify("Ausfall gelöscht.")

    @on(Button.Pressed, "#close-closure-management")
    def close_closure_management(self) -> None:
        self.action_cancel()

    def action_cancel(self) -> None:
        self.dismiss()
