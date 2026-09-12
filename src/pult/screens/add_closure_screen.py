from datetime import date
from typing import ClassVar

from textual import on
from textual.app import ComposeResult
from textual.widgets import (
    Button,
    Input,
    Label,
    Select,
)

from pult.presentation import DATE_INPUT_HINT, format_date, parse_date
from pult.school.calendar import (
    Closure,
    ClosureKind,
)
from pult.school.school_class import SchoolClass
from pult.screens.base_screen import (
    PultModalScreen,
)
from pult.services.closures import ScopedClosure, validate_closure
from pult.widgets.form_dialog import FormDialog, FormFields
from pult.widgets.scrolling import Horizontal, Vertical

SCHOOL_SCOPE = "school"
CLASS_SCOPE_PREFIX = "class:"


class AddClosureScreen(PultModalScreen[ScopedClosure | None]):
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

        with FormDialog("Geplanter Ausfall", id="add-closure-dialog"):
            with FormFields(classes="form-fields"):
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
                with Horizontal(classes="date-fields"):
                    with Vertical(classes="date-field"):
                        yield Label("Startdatum", classes="field-label")
                        yield Input(
                            value=default_date,
                            placeholder=DATE_INPUT_HINT,
                            id="closure-start",
                        )
                    with Vertical(classes="date-field"):
                        yield Label("Enddatum", classes="field-label")
                        yield Input(
                            value=default_date,
                            placeholder=DATE_INPUT_HINT,
                            id="closure-end",
                        )
                yield Label(DATE_INPUT_HINT, classes="form-hint")

            with Horizontal(id="add-closure-actions", classes="form-actions"):
                yield Button("Abbrechen", id="cancel-closure")
                yield Button(
                    "Speichern",
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
