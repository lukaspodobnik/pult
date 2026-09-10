import re
from datetime import time
from typing import ClassVar

from textual import on
from textual.app import ComposeResult
from textual.widgets import Button, Input, Label, Static

from pult.school.period import Period, save_periods
from pult.screens.base_screen import PultModalScreen
from pult.widgets.form_dialog import FormDialog, FormFields
from pult.widgets.scrolling import Horizontal


class EditPeriodsScreen(PultModalScreen[bool]):
    """Bearbeite globale Uhrzeiten, ohne Stundennummern oder Anzahl zu ändern."""

    BINDINGS: ClassVar = [("escape", "cancel", "Abbrechen")]
    DEFAULT_CSS = """
    EditPeriodsScreen .period-row { height: 3; }
    EditPeriodsScreen .period-number { width: 12; padding-top: 1; }
    EditPeriodsScreen Input { width: 1fr; }
    EditPeriodsScreen .period-heading { height: 1; margin-top: 1; }
    """

    def __init__(self, periods: list[Period]) -> None:
        super().__init__()
        self.periods = periods

    def compose(self) -> ComposeResult:
        with FormDialog("STUNDENZEITEN", id="periods-dialog"):
            with FormFields(classes="form-fields"):
                yield Static(
                    "Gilt für alle Schuljahre. Zeiten im Format HH:MM. "
                    "Speichern übernimmt die Zeiten direkt; Stundennummern bleiben erhalten.",
                    classes="form-hint",
                )
                yield Static(
                    "Stunde      Beginn             Ende", classes="period-heading"
                )
                for period in self.periods:
                    with Horizontal(classes="period-row"):
                        yield Label(f"{period.number}. Std.", classes="period-number")
                        yield Input(
                            f"{period.start:%H:%M}", id=f"start-{period.number}"
                        )
                        yield Input(f"{period.end:%H:%M}", id=f"end-{period.number}")
            with Horizontal(classes="form-actions"):
                yield Button("Abbrechen", id="cancel-periods")
                yield Button("Speichern", id="save-periods", variant="primary")

    @on(Button.Pressed, "#cancel-periods")
    def action_cancel(self) -> None:
        self.dismiss(False)

    def read_time(self, field_id: str) -> time:
        value = self.query_one(f"#{field_id}", Input).value.strip()
        if not re.fullmatch(r"[0-9]{2}:[0-9]{2}", value):
            raise ValueError("Bitte gib alle Uhrzeiten im Format HH:MM ein.")
        try:
            return time.fromisoformat(value)
        except ValueError as error:
            raise ValueError(f"Die Uhrzeit {value} ist ungültig.") from error

    @on(Button.Pressed, "#save-periods")
    def save(self) -> None:
        try:
            periods = [
                Period(
                    p.number,
                    self.read_time(f"start-{p.number}"),
                    self.read_time(f"end-{p.number}"),
                )
                for p in self.periods
            ]
            save_periods(self.app_config.root, periods)
        except (OSError, ValueError) as error:
            self.notify(f"Stundenzeiten nicht gespeichert: {error}", severity="error")
            return
        self.notify("Stundenzeiten für alle Schuljahre gespeichert.")
        self.dismiss(True)
