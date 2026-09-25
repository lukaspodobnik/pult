"""Zurückhaltende Spaltenköpfe für kompakte Terminlisten."""

from rich.style import Style
from rich.text import Text


def format_detail_table(text: str, width: int) -> Text:
    # Die Leerzeile zwischen Kontext und Kopf wird für die Trennlinie genutzt:
    # Sechs Termine passen weiterhin in den elfzeiligen Rahmen.
    lines = text.split("\n")
    context, _, heading, *rows = lines
    result = Text(context + "\n")
    muted = Style(dim=True, bold=False)
    result.append(heading + "\n", style=muted)
    result.append("─" * max(1, width) + "\n", style=muted)
    result.append("\n".join(rows))
    return result
