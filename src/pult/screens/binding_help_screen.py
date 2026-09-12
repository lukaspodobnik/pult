"""Tastaturhilfe als Momentaufnahme der aufrufenden Ansicht und ihres Fokus."""

from typing import ClassVar

from rich.table import Table
from rich.text import Text
from textual import on
from textual.binding import Binding
from textual.widgets import Button, Input, Static, TextArea

from pult.screens.base_screen import PultModalScreen
from pult.widgets.form_dialog import FormDialog
from pult.widgets.scrolling import Horizontal, VerticalScroll


def binding_help_rows(screen) -> list[tuple[str, str, bool]]:
    active = screen.active_bindings
    rows = []
    seen = set()
    # Aktive Widget-Bindings enthalten auch Navigation, die der Footer ausblendet.
    candidates = [item.binding for item in active.values() if item.binding.description]
    candidates += list(Binding.make_bindings(screen.BINDINGS))
    candidates += list(Binding.make_bindings(screen.app.BINDINGS))
    navigation_aliases = {
        "left": ("←", "h"),
        "down": ("↓", "j"),
        "up": ("↑", "k"),
        "right": ("→", "l"),
    }
    text_input = isinstance(screen.focused, (Input, TextArea))
    for binding in candidates:
        if binding.key in {"home", "end", "pageup", "pagedown", "f1"}:
            continue
        if not binding.description or (
            not binding.show
            and binding.key
            not in {
                "up",
                "down",
                "left",
                "right",
                "tab",
                "shift+tab",
                "enter",
            }
        ):
            continue
        identity = (binding.key, binding.action)
        if identity in seen:
            continue
        seen.add(identity)
        current = active.get(binding.key)
        enabled = (
            current is not None
            and current.binding.action == binding.action
            and current.enabled
        )
        key_display = screen.app.get_key_display(binding)
        if binding.key in navigation_aliases:
            arrow, alias = navigation_aliases[binding.key]
            key_display = arrow if text_input else f"{arrow}, {alias}"
        rows.append((key_display, binding.description, enabled))
    return rows


def group_help_rows(
    rows: list[tuple[str, str, bool]],
) -> dict[str, list[tuple[str, str, bool]]]:
    groups: dict[str, list[tuple[str, str, bool]]] = {
        "Navigation": [],
        "Aktionen der Ansicht": [],
        "Allgemein": [],
    }
    for row in rows:
        key = row[0].lower()
        if key.startswith(("←", "↓", "↑", "→")) or key in {
            "tab",
            "shift+tab",
            "enter",
            "f2",
            "⇥",
            "shift+⇥",
            "↵",
        }:
            group = "Navigation"
        elif key in {"q", "escape", "esc"}:
            group = "Allgemein"
        else:
            group = "Aktionen der Ansicht"
        groups[group].append(row)
    return {title: entries for title, entries in groups.items() if entries}


class BindingHelpScreen(PultModalScreen[None]):
    BINDINGS: ClassVar = [
        ("escape", "close", "Zurück"),
        ("f1", "close", "Hilfe schließen"),
    ]
    DEFAULT_CSS = """
    BindingHelpScreen #binding-help-dialog { width: 80; max-width: 95%; height: 85%; }
    BindingHelpScreen #binding-help-content { height: 1fr; }
    BindingHelpScreen Static { height: auto; }
    BindingHelpScreen #binding-help-note { margin-bottom: 1; color: $text-muted; }
    """

    def __init__(self, rows: list[tuple[str, str, bool]], context: str):
        super().__init__()
        self.rows = rows
        self.context = context

    def compose(self):
        with FormDialog("TASTATURHILFE", id="binding-help-dialog"):
            with VerticalScroll(id="binding-help-content"):
                yield Static(self.context, markup=False)
                yield Static(
                    "Gilt für die Ansicht und den Fokus vor dem Öffnen der Hilfe. "
                    "Gedämpfte Befehle sind dort derzeit nicht verfügbar.\n"
                    "Außerhalb von Textfeldern entsprechen h/j/k/l den Pfeiltasten.",
                    id="binding-help-note",
                    markup=False,
                )
                table = Table.grid(padding=(0, 2))
                table.add_column(no_wrap=True)
                table.add_column()
                for index, (heading, rows) in enumerate(
                    group_help_rows(self.rows).items()
                ):
                    if index:
                        table.add_row("", "")
                    table.add_row("", Text(heading, style="bold underline"))
                    for key, description, enabled in rows:
                        table.add_row(
                            Text(key, style="bold" if enabled else "dim"),
                            Text(
                                description
                                if enabled
                                else description + " (derzeit nicht verfügbar)",
                                style="" if enabled else "dim",
                            ),
                        )
                yield Static(table, id="binding-help-keys")
            with Horizontal(classes="form-actions"):
                yield Button("Zurück", id="close-binding-help")

    def on_mount(self):
        self.query_one("#binding-help-content").focus()

    @on(Button.Pressed, "#close-binding-help")
    def action_close(self):
        self.dismiss(None)
