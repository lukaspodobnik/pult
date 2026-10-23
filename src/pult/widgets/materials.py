"""Stets sichtbare Materialliste, mit direkt zu öffnenden Links."""

import subprocess
import sys
from pathlib import Path

from textual import on
from textual.widgets import Button, Static

from pult.curriculum.material import material_entries
from pult.services.documents.document_rendering import safe_local
from pult.widgets.scrolling import Horizontal, VerticalScroll


class MaterialsPane(VerticalScroll):
    can_focus = False
    can_focus_children = False

    DEFAULT_CSS = """
    MaterialsPane {height:12; min-height:6; border:round $primary; background:$surface; padding:0 1;}
    MaterialsPane Static {height:auto; margin:0;}
    MaterialsPane .material-row {height:auto;}
    MaterialsPane .material-bullet {width:2; height:1;}
    MaterialsPane .material-text {width:1fr;}
    """

    def __init__(self, source: str, path: Path, directory: Path, **kwargs):
        super().__init__(**kwargs)
        self.entries = material_entries(source)
        self.path, self.directory = path, directory
        self.border_title = "MATERIAL"

    def compose(self):
        if not self.entries:
            yield Static("Kein Material eingetragen.", classes="lesson-empty")
        for index, entry in enumerate(self.entries):
            with Horizontal(classes="material-row"):
                yield Static("•", classes="material-bullet", markup=False)
                if entry.target:
                    button = Button(entry.label, id=f"material-{index}", compact=True)
                    button.can_focus = False
                    # Ohne den zusätzlichen Texteinschub des Standardbuttons.
                    button.styles.line_pad = 0
                    yield button
                else:
                    yield Static(entry.label, classes="material-text", markup=False)

    @on(Button.Pressed)
    def open_material(self, event: Button.Pressed):
        event.stop()
        entry = self.entries[int((event.button.id or "").removeprefix("material-"))]
        target = entry.target
        if target is None:
            return
        if target.startswith(("https://", "http://")):
            self.app.open_url(target)
            return
        try:
            path = safe_local(target, self.path, self.directory)
            if not path.is_file():
                raise ValueError("Die verlinkte Datei existiert nicht.")
            subprocess.Popen(
                ["open" if sys.platform == "darwin" else "xdg-open", str(path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except (OSError, ValueError) as error:
            self.notify(str(error), severity="warning")
