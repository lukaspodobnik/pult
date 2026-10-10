"""Native Tabelle mit festen Überschriften und durchgehenden Abschnittszeilen."""

from rich.text import Text
from textual.app import ComposeResult
from textual.widgets import Static

from pult.progress.queries.distribution import DistributionKind, DistributionRow
from pult.widgets.scrolling import Horizontal, Vertical, VerticalScroll

WEEKDAY_LABELS = ("Mo", "Di", "Mi", "Do", "Fr", "Sa", "So")


class DistributionTableRow(Horizontal):
    def __init__(self, row: DistributionRow | None = None) -> None:
        super().__init__(
            classes="distribution-row" + (f" {row.kind.value}" if row else " heading")
        )
        self.row = row

    def compose(self) -> ComposeResult:
        row = self.row
        if row and row.kind in {DistributionKind.SEQUENCE, DistributionKind.HOLIDAY}:
            yield Static(Text(row.title), classes="distribution-section")
            return
        values = (
            ("Nr.", "WT", "Datum", "Stundenthema", "Anmerkungen")
            if row is None
            else (
                str(row.number) if row.number is not None else "—",
                WEEKDAY_LABELS[row.date.weekday()],
                row.date.strftime("%d.%m.%Y"),
                row.title,
                row.notes,
            )
        )
        for name, value in zip(("number", "weekday", "date", "title", "notes"), values):
            yield Static(Text(" ".join(value.split())), classes=f"distribution-{name}")


class DistributionView(Vertical):
    def __init__(self, rows: tuple[DistributionRow, ...]) -> None:
        super().__init__()
        self.rows = rows

    def compose(self) -> ComposeResult:
        yield DistributionTableRow()
        with VerticalScroll(classes="distribution-body"):
            if not self.rows:
                yield Static(
                    "Noch keine Unterrichtstermine vorhanden.",
                    classes="distribution-empty",
                )
            for row in self.rows:
                yield DistributionTableRow(row)
