from importlib.metadata import version
from importlib.resources import files
from typing import ClassVar

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Button, Static

from pult.screens.base_screen import PultModalScreen
from pult.widgets.form_dialog import FormDialog


class AboutScreen(PultModalScreen[None]):
    """Zeige Programm- und Quellenhinweise sowie den vollständigen Lizenztext offline."""

    BINDINGS: ClassVar = [("escape", "close", "Zurück")]
    DEFAULT_CSS = """
    AboutScreen #about-dialog { width: 90; height: 85%; }
    AboutScreen #about-content { height: 1fr; }
    AboutScreen #about-text { height: auto; }
    """

    def compose(self) -> ComposeResult:
        with FormDialog("ÜBER PULT / LIZENZ", id="about-dialog"):
            with VerticalScroll(id="about-content"):
                yield Static(
                    f"PULT {version('pult')}\n"
                    "Copyright © 2026 Lukas Podobnik\n\n"
                    "GNU General Public License, Version 3 oder später (GPL-3.0-or-later).\n"
                    "Du darfst den Programmcode nach den Bedingungen dieser Lizenz "
                    "verwenden, verändern und weitergeben.\n"
                    "Ohne Gewährleistung, soweit gesetzlich zulässig.\n\n"
                    "Projekt und Quellcode: https://github.com/lukaspodobnik/pult\n\n"
                    "QUELLEN\n"
                    "Lehrplanvorlagen: ISB, LehrplanPLUS Bayern (Gymnasium). "
                    "Die Originaltexte der Lehrpläne sind laut ISB nicht urheberrechtlich geschützt.\n"
                    "https://www.lehrplanplus.bayern.de/seite/impressum\n"
                    "Ferientermine: Bayerisches Kultusministerium, Ferienordnung "
                    "2024/25–2029/30 (BayMBl. 2022 Nr. 747).\n"
                    "https://www.verkuendung-bayern.de/baymbl/2022-747/\n"
                    "Feiertage: Bayerisches Feiertagsgesetz, Art. 1.\n"
                    "https://www.gesetze-bayern.de/Content/Document/BayFTG-1\n"
                    "Logo-Schriftzug: Calvin von Shmuel Ross, erzeugt mit TAAG (patorjk.com).\n\n"
                    "BIBLIOTHEKEN\n"
                    "Textual, Rich, tomli-w, markdown-it-py, mdit-py-plugins, "
                    "linkify-it-py, mdurl und platformdirs: MIT.\n"
                    "Pygments: BSD-2-Clause. typing_extensions: PSF-2.0.\n"
                    "Fremde Bestandteile behalten ihre jeweiligen Rechte und Lizenzen.\n\n"
                    "VOLLSTÄNDIGER LIZENZTEXT\n\n"
                    + files("pult")
                    .joinpath("legal/GPL-3.0.txt")
                    .read_text(encoding="utf-8"),
                    id="about-text",
                    markup=False,
                )
            with Horizontal(classes="form-actions"):
                yield Button("Zurück", id="close-about")

    @on(Button.Pressed, "#close-about")
    def action_close(self) -> None:
        self.dismiss(None)
