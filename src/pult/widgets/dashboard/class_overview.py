"""Klassenbilanz mit nächstem Leistungsnachweis und Abschlusszahlen."""

from textual.app import ComposeResult
from textual.widgets import Static

from pult.presentation import format_date
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
        for balance in self.balances:
            with Horizontal(classes="class-balance-row"):
                yield Static(
                    balance.school_class_id,
                    classes="balance-class",
                    markup=False,
                )
                yield Static(
                    self.subjects[balance.subject_id].short_name,
                    classes="balance-subject",
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
                yield Static(
                    f"{format_date(balance.next_assessment.assessment.date)} · {balance.next_assessment.number}. {balance.next_assessment.assessment.kind.abbreviation}"
                    if balance.next_assessment
                    else "—",
                    classes="balance-assessments",
                    markup=False,
                )

                yield Static(balance.large_assessments.label, classes="balance-large")
                yield Static(balance.small_assessments.label, classes="balance-small")

    def compose(self) -> ComposeResult:
        with Horizontal(id="class-overview-headings"):
            yield Static("Klasse", classes="balance-class")
            yield Static("Fach", classes="balance-subject")
            yield Static("Differenz", classes="balance-difference")
            yield Static("Leistungsnachweise", classes="balance-assessments")
            yield Static("Groß", classes="balance-large")
            yield Static("Klein", classes="balance-small")
        with VerticalScroll(id="class-overview-rows", can_focus=False):
            yield from self.rows()

    async def update_data(
        self, balances: tuple[ClassBalance, ...], subjects: dict[str, Subject]
    ):
        if self.balances == balances and self.subjects == subjects:
            return
        self.balances, self.subjects = balances, subjects
        await self.recompose()
