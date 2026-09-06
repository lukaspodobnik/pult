from datetime import date
from typing import ClassVar

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    Button,
    Input,
    Label,
    Select,
)

from schooltools_tui.presentation import DATE_INPUT_HINT, format_date, parse_date
from schooltools_tui.school.calendar import (
    Closure,
    ClosureKind,
)
from schooltools_tui.school.school_class import SchoolClass
from schooltools_tui.screens.base_screen import (
    SchooltoolsModalScreen,
)
from schooltools_tui.services.closures import ScopedClosure, validate_closure

SCHOOL_SCOPE = "school"
CLASS_SCOPE_PREFIX = "class:"


class AddClosureScreen(SchooltoolsModalScreen[ScopedClosure | None]):
    BINDINGS: ClassVar = [("escape", "cancel", "Abbrechen")]

    def __init__(self, school_classes: list[SchoolClass], default_date: date) -> None:
        super().__init__()
        self.school_classes = school_classes
        self.default_date = default_date

    def compose(self) -> ComposeResult:
        default_date = format_date(self.default_date)
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
            validate_closure(self.app_config, ScopedClosure(closure, school_class_id))
        except (OSError, TypeError, ValueError) as error:
            self.notify(str(error), severity="error")
            return

        self.dismiss(ScopedClosure(closure, school_class_id))

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
