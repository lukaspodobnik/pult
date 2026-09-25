"""Klassenbilanz mit reservierter Spalte für Leistungsnachweise."""

from rich.cells import cell_len
from textual.app import ComposeResult
from textual.widgets import Static

from pult.progress.queries.dashboard import ClassBalance
from pult.school.subject import Subject
from pult.widgets.scrolling import Horizontal, Vertical, VerticalScroll


class ClassOverviewPanel(Vertical):
    def __init__(
        self, balances: tuple[ClassBalance, ...], subjects: dict[str, Subject]
    ):
        super().__init__(id="class-overview", classes="dashboard-panel")
        self.border_title = "KLASSENÜBERSICHT"
        self.balances = balances
        self.subjects = subjects

    def rows(self):
        if not self.balances:
            yield Static("Noch keine Klassen angelegt.", classes="dashboard-empty")
        class_width = max(
            (cell_len(balance.school_class_id) for balance in self.balances), default=0
        )
        for balance in self.balances:
            class_label = balance.school_class_id + " " * (
                class_width - cell_len(balance.school_class_id)
            )
            with Horizontal(classes="class-balance-row"):
                yield Static(
                    f"{class_label} · {self.subjects[balance.subject_id].short_name}",
                    classes="balance-class",
                    markup=False,
                )
                sign = (
                    "negative"
                    if balance.difference < 0
                    else "positive"
                    if balance.difference > 0
                    else "neutral"
                )
                yield Static(
                    f"{balance.difference:+d} Std.",
                    classes=f"balance-difference {sign}",
                )
                yield Static("—", classes="balance-assessments")

    def compose(self) -> ComposeResult:
        with Horizontal(id="class-overview-headings"):
            yield Static("Klasse · Fach", classes="balance-class")
            yield Static("Differenz", classes="balance-difference")
            yield Static("Leistungsnachweise", classes="balance-assessments")
        with VerticalScroll(id="class-overview-rows", can_focus=False):
            yield from self.rows()

    async def update_data(
        self, balances: tuple[ClassBalance, ...], subjects: dict[str, Subject]
    ):
        if self.balances == balances and self.subjects == subjects:
            return
        self.balances, self.subjects = balances, subjects
        await self.recompose()
