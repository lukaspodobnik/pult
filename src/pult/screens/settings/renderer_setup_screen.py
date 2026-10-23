from contextlib import suppress
from typing import ClassVar

from textual import on, work
from textual.app import ComposeResult
from textual.widgets import Collapsible, ProgressBar, Static, TextArea
from textual.worker import Worker, WorkerCancelled

from pult.screens.base_screen import PultModalScreen
from pult.services.documents.renderer_setup import SetupResult
from pult.widgets.button import Button
from pult.widgets.form_dialog import FormDialog, FormFields
from pult.widgets.scrolling import Horizontal


class RendererSetupScreen(PultModalScreen[bool]):
    BINDINGS: ClassVar = [("escape", "close", "Schließen")]
    DEFAULT_CSS = """
    RendererSetupScreen #renderer-status, RendererSetupScreen #renderer-help {
        height: auto;
        margin-bottom: 1;
    }
    RendererSetupScreen #renderer-command {
        height: auto;
    }
    RendererSetupScreen #renderer-log { height: 8; }
    RendererSetupScreen #renderer-progress { margin-bottom: 1; }
    """

    def __init__(self, result: SetupResult | None = None, *, offered: bool = False):
        super().__init__()
        self.result = result
        self.offered = offered
        self.operation: Worker | None = None
        self.busy = False

    def compose(self) -> ComposeResult:
        with FormDialog("DOKUMENTDARSTELLUNG", id="renderer-dialog", wide=True):
            with FormFields(classes="form-fields"):
                yield Static(
                    "Dokumentdarstellung wird geprüft …",
                    id="renderer-status",
                    markup=False,
                )
                yield ProgressBar(
                    show_eta=False, show_percentage=False, id="renderer-progress"
                )
                yield Static(id="renderer-help", markup=False)
                yield Static(id="renderer-command", markup=False)
                yield Button("Befehl kopieren", id="renderer-copy")
                with Collapsible(title="Details", id="renderer-details"):
                    yield TextArea(
                        read_only=True, id="renderer-log", show_line_numbers=False
                    )
            with Horizontal(classes="form-actions"):
                yield Button(
                    "Später" if self.offered else "Schließen", id="renderer-close"
                )
                yield Button("Erneut prüfen", id="renderer-check")
                yield Button("Einrichten", id="renderer-install", variant="primary")

    def on_mount(self) -> None:
        if self.result is None:
            self.start_operation(install=False)
        else:
            self.show_result(self.result)

    def show_result(self, result: SetupResult) -> None:
        self.result = result
        self.busy = False
        self.query_one("#renderer-status", Static).update(result.message)
        self.query_one("#renderer-help", Static).update(result.help)
        self.query_one("#renderer-help").display = bool(result.help)
        self.query_one("#renderer-command", Static).update(result.command)
        self.query_one("#renderer-command").display = bool(result.command)
        self.query_one("#renderer-copy").display = bool(result.command)
        self.query_one("#renderer-progress").display = False
        self.query_one("#renderer-details").display = bool(result.details)
        self.query_one("#renderer-log", TextArea).load_text(result.details)
        self.query_one("#renderer-check", Button).disabled = False
        self.query_one("#renderer-install").display = result.state == "missing"
        self.query_one("#renderer-install", Button).disabled = False
        close = self.query_one("#renderer-close", Button)
        close.disabled = False
        close.label = (
            "Später" if self.offered and result.state != "ready" else "Schließen"
        )
        close.focus()

    def start_operation(self, *, install: bool) -> None:
        if self.busy:
            return
        self.busy = True
        self.query_one("#renderer-status", Static).update(
            "Chromium wird heruntergeladen und eingerichtet …"
            if install
            else "Dokumentdarstellung wird geprüft …"
        )
        for selector in (
            "#renderer-help",
            "#renderer-command",
            "#renderer-copy",
            "#renderer-details",
        ):
            self.query_one(selector).display = False
        self.query_one("#renderer-progress").display = True
        self.query_one("#renderer-check", Button).disabled = True
        self.query_one("#renderer-install", Button).disabled = True
        self.query_one("#renderer-close", Button).label = "Abbrechen"
        self.operation = self.run_operation(install)

    @work(group="renderer-setup", exclusive=True)
    async def run_operation(self, install: bool) -> None:
        service = self.pult_app.renderer_setup
        result = (
            await service.install(self.show_output)
            if install
            else await service.check()
        )
        if self.is_mounted:
            self.show_result(result)

    def show_output(self, log: str) -> None:
        if self.is_mounted:
            self.query_one("#renderer-details").display = True
            self.query_one("#renderer-log", TextArea).load_text(log)

    @on(Button.Pressed, "#renderer-install")
    def install(self) -> None:
        self.start_operation(install=True)

    @on(Button.Pressed, "#renderer-check")
    def check(self) -> None:
        self.start_operation(install=False)

    @on(Button.Pressed, "#renderer-copy")
    def copy_command(self) -> None:
        if self.result and self.result.command:
            self.app.copy_to_clipboard(self.result.command)
            self.notify("Befehl kopiert.")

    @on(Button.Pressed, "#renderer-close")
    async def action_close(self) -> None:
        if self.busy and self.operation is not None:
            self.query_one("#renderer-close", Button).disabled = True
            self.query_one("#renderer-status", Static).update(
                "Einrichtung wird abgebrochen …"
            )
            self.operation.cancel()
            with suppress(WorkerCancelled):
                await self.operation.wait()
        ready = (
            self.result is not None and self.result.state == "ready" and not self.busy
        )
        if self.offered and not ready:
            try:
                self.pult_app.renderer_setup.defer()
            except OSError:
                self.notify(
                    "Die Auswahl konnte nicht gespeichert werden.", severity="warning"
                )
        self.dismiss(ready)
