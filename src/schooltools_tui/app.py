from typing import ClassVar

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Static


class SchooltoolsApp(App):
    CSS_PATH = "schooltools.tcss"
    
    TITLE = "Schooltools"
    SUB_TITLE = "Schulalltag im Blick"

    BINDINGS: ClassVar = [
        ("q", "quit", "Beenden"),
        ("h", "show_home", "Home"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()

        with Horizontal(id="main"):
            with Vertical(id="picker"):
                yield Static("Home", classes="picker-entry")
                yield Static("7A", classes="picker-entry")
                yield Static("8B", classes="picker-entry")

            with Vertical(id="content"):
                yield Static("Stundenplan", id="page-title")
                yield Static("Hier erscheint dann der Stundenplan", id="schedule")
                yield Static("Nächste Stunde", id="next-lesson")
                yield Static("Schuljahr", id="school-year")

        yield Footer()

    def on_mount(self) -> None:
        self.theme = "gruvbox"

    def action_show_home(self) -> None:
        page_title = self.query_one("#page-title", Static)
        page_title.update("Stundenplan")
