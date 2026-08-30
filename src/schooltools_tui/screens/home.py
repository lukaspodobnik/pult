from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Static

from schooltools_tui.screens.base import SchooltoolsScreen


class HomeScreen(SchooltoolsScreen[None]):
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

