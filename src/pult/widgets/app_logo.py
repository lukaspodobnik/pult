from textual.widgets import Static

# Lettering generated with TAAG / Calvin (TheDraw), by Stevonnie Ross.
# See SOURCES.md for attribution. No font files are bundled.
LOGO = r"""
╔══╗ ╦  ╦ ╦  ╔═╦═╗
║  ║ ║  ║ ║    ║  
╠══╝ ║  ║ ║    ║  
║    ║  ║ ║    ║  
╩    ╚══╝ ╚══╝ ╩  
"""


class AppLogo(Static):
    """Zeige den Logo-Schriftzug zentriert und in der aktuellen Theme-Akzentfarbe."""

    DEFAULT_CSS = """
    AppLogo {
        height: 5;
        content-align: center middle;
        color: $text-accent;
    }
    """

    def __init__(self, *, id: str | None = None) -> None:
        super().__init__(LOGO.strip("\n"), markup=False, id=id)
