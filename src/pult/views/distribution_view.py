"""Rich-Tabellen mit gemeinsamen Spalten und durchgehenden Abschnittszeilen."""

from rich import box
from rich.console import Console, ConsoleOptions, RenderResult
from rich.table import Table
from rich.text import Text
from textual.app import ComposeResult
from textual.widgets import Static

from pult.presentation import format_compact_date
from pult.progress.queries.distribution import DistributionKind, DistributionRow
from pult.widgets.scrolling import Vertical, VerticalScroll

HEADINGS = ("Nr.", "Datum", "Stundenthema", "Anmerkungen")
SECTION_KINDS = {DistributionKind.SEQUENCE, DistributionKind.HOLIDAY}
HEADER_BOX = box.Box(str(box.MINIMAL).replace("│", " ").replace("┼", "─"))


class ClosedSectionTable(Table):
    """Schließe die inneren Spaltentrenner ab, ohne einen Außenrahmen hinzuzufügen."""

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        widths = [column.width or 0 for column in self.columns]
        segments = [
            "─" * (width + (1 if index in {0, len(widths) - 1} else 2))
            for index, width in enumerate(widths)
        ]
        yield Text("┬".join(segments), style=self.border_style or "")
        yield from super().__rich_console__(console, options)
        yield Text("┴".join(segments), style=self.border_style or "")


class DistributionTable(Static):
    COMPONENT_CLASSES = {
        "distribution-table--border",
        "distribution-table--muted",
        "distribution-table--assessment",
        "distribution-table--notes",
    }

    def __init__(
        self,
        view: "DistributionView",
        rows: tuple[DistributionRow, ...] = (),
        *,
        heading: bool = False,
    ) -> None:
        super().__init__(
            classes="distribution-table heading" if heading else "distribution-table"
        )
        self.view = view
        self.rows = rows
        self.heading = heading

    def render(self) -> Table:
        table_class = Table if self.heading else ClosedSectionTable
        table = table_class(
            box=HEADER_BOX if self.heading else box.MINIMAL,
            show_edge=False,
            show_header=self.heading,
            pad_edge=False,
            padding=(0, 1),
            border_style=self.get_component_rich_style("distribution-table--border"),
            header_style=self.get_component_rich_style("distribution-table--muted"),
        )
        for heading, width in zip(HEADINGS, self.view.column_widths):
            table.add_column(
                Text(heading, no_wrap=True, overflow="ellipsis"),
                width=width,
                overflow="fold",
            )
        for row in self.rows:
            style = self.rich_style
            if row.kind in {DistributionKind.CANCELLED, DistributionKind.UNRECORDED}:
                style += self.get_component_rich_style("distribution-table--muted")
            notes_style = self.get_component_rich_style("distribution-table--notes")
            values = (
                str(row.number) if row.number is not None else "—",
                format_compact_date(row.date),
                row.title,
                row.notes,
            )
            table.add_row(
                *(
                    Text(
                        " ".join(value.split()),
                        style=(
                            self.get_component_rich_style(
                                "distribution-table--assessment"
                            )
                            if index == 2 and row.kind is DistributionKind.ASSESSMENT
                            else notes_style
                            if index == 3
                            else ""
                        ),
                        justify="left",
                    )
                    for index, value in enumerate(values)
                ),
                style=style,
            )
        return table


class DistributionTableRow(Static):
    """Eine Abschnittszeile ohne Spaltengrenzen."""

    def __init__(self, row: DistributionRow) -> None:
        super().__init__(
            Text(
                row.title.upper() if row.kind is DistributionKind.HOLIDAY else row.title
            ),
            classes=f"distribution-section {row.kind.value}",
        )
        self.row = row


class DistributionView(Vertical):
    def __init__(self, rows: tuple[DistributionRow, ...]) -> None:
        super().__init__()
        self.rows = rows
        self.column_widths = (3, 11, 24, 20)

    def compose(self) -> ComposeResult:
        yield DistributionTable(self, heading=True)
        body = VerticalScroll(classes="distribution-body")
        body.can_focus = False
        with body:
            if not self.rows:
                yield Static(
                    "Noch keine Unterrichtstermine vorhanden.",
                    classes="distribution-empty",
                )
            pending = []
            for row in self.rows:
                if row.kind in SECTION_KINDS:
                    if pending:
                        yield DistributionTable(self, tuple(pending))
                        pending = []
                    yield DistributionTableRow(row)
                else:
                    pending.append(row)
            if pending:
                yield DistributionTable(self, tuple(pending))

    def on_mount(self) -> None:
        self.call_after_refresh(self.update_column_widths)

    def on_resize(self) -> None:
        self.call_after_refresh(self.update_column_widths)

    def update_column_widths(self) -> None:
        body = self.query_one(".distribution-body", VerticalScroll)
        # Innenpadding: 2; drei Trennlinien und Zellabstände: 9.
        available = max(34, body.scrollable_content_region.width - 2)
        flexible = available - 9 - 3 - 11
        # Die vier gewonnenen Zeichen kommen vollständig den Anmerkungen zugute.
        title = max(4, (flexible - 4) * 3 // 5)
        widths = (3, 11, title, flexible - title)
        if widths != self.column_widths:
            self.column_widths = widths
            for table in self.query(DistributionTable):
                table.refresh(layout=True)
        # Zwei vorhergehende Zellen, deren Abstände und Trennlinien sowie
        # das linke Padding der Themenspalte; den Abschnittsrand ausgleichen.
        title_offset = 1 + sum(self.column_widths[:2]) + 6
        for section in self.query(DistributionTableRow):
            section.styles.padding = (
                0,
                1,
                0,
                title_offset - section.styles.margin.left,
            )
