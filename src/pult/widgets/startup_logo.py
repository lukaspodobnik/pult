"""Kurze, deckende Startblende ohne zusätzlichen Ladehinweis."""

from textual.widgets import Static

from pult.widgets.app_logo import LOGO


def triple_logo(logo: str) -> str:
    """Vergrößere das Linienlogo auf 3×, mit symmetrischen, verbundenen Strichen."""
    connections = {
        " ": "",
        "═": "ew",
        "║": "ns",
        "╔": "es",
        "╗": "ws",
        "╚": "ne",
        "╝": "nw",
        "╠": "nes",
        "╦": "ews",
        "╩": "new",
    }
    tiles = {
        character: (
            " " + ("║" if "n" in directions else " ") + " ",
            ("═" if "w" in directions else " ")
            + character
            + ("═" if "e" in directions else " "),
            " " + ("║" if "s" in directions else " ") + " ",
        )
        for character, directions in connections.items()
    }
    return "\n".join(
        "".join(tiles[character][row] for character in line)
        for line in logo.strip("\n").splitlines()
        for row in range(3)
    )


LARGE_LOGO = triple_logo(LOGO)


class StartupLogo(Static):
    DEFAULT_CSS = """
    StartupLogo {
        overlay: screen;
        position: absolute;
        width: 100vw;
        height: 100vh;
        background: $background;
        color: $text-accent;
        content-align: center middle;
    }
    """

    def __init__(self) -> None:
        super().__init__(LARGE_LOGO, id="startup-logo", markup=False)
