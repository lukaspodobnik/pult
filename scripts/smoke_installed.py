"""Prüfe ein installiertes Wheel ohne Projektimporte oder echte Nutzerdaten.

Aufruf mit dem Python der isolierten Installation, optional mit dem Pfad
zu deren pult-Startskript als Argument. Nicht mit uv run ausführen.
"""

import asyncio
import os
import runpy
import sys
from importlib.metadata import distribution
from importlib.resources import files
from pathlib import Path
from tempfile import TemporaryDirectory

from textual.widgets import Input, Select

import pult
import pult.config.app_config as config_module
import pult.services.omarchy_theme as theme_module
from pult.app import PultApp
from pult.curriculum.sequence import load_sequence_library
from pult.screens.about_screen import AboutScreen
from pult.screens.main_screen import MainScreen
from pult.screens.setup_pult_screen import SetupScreen


async def smoke(app: PultApp, root: Path) -> None:
    async with app.run_test(size=(206, 46)) as pilot:
        await pilot.pause()
        assert isinstance(app.screen, SetupScreen)
        app.screen.query_one("#root", Input).value = "data"
        app.screen.query_one("#school-year", Select).value = "2026-2027"
        assert await pilot.click("#submit-setup")
        for _ in range(80):
            await pilot.pause(0.05)
            if (
                isinstance(app.screen, MainScreen)
                and app.screen._pending_view_id is None
            ):
                break
        assert isinstance(app.screen, MainScreen)
        assert app.require_config().root == root / "data"
        assert len(load_sequence_library(root / "data")) == 116
        await app.push_screen(AboutScreen())
        await pilot.pause()
        assert app.screen.query_one("#about-content").max_scroll_y > 0
    # Ein neuer Prozess würde ebenfalls aus einem beliebigen Verzeichnis starten.
    (root / "other").mkdir()
    os.chdir(root / "other")
    second = PultApp()
    async with second.run_test(size=(206, 46)) as pilot:
        await pilot.pause(0.3)
        assert isinstance(second.screen, MainScreen)
        assert second.require_config().root == root / "data"


def main() -> None:
    checkout = Path(__file__).resolve().parents[1]
    assert pult.__file__ is not None
    assert not Path(pult.__file__).resolve().is_relative_to(checkout)
    installed = distribution("pult")
    assert installed.metadata["License-Expression"] == "GPL-3.0-or-later"
    assert (
        "GNU GENERAL PUBLIC LICENSE"
        in files("pult").joinpath("legal/GPL-3.0.txt").read_text()
    )
    old_cwd = Path.cwd()
    try:
        with TemporaryDirectory(prefix="pult-installed-smoke-") as directory:
            root = Path(directory)
            os.chdir(root)
            config_module.APP_CONFIG_PATH = root / "config.toml"
            theme_module.get_omarchy_palette_path = lambda: root / "no-theme.toml"
            if len(sys.argv) > 1:
                # Durchlaufe den echten installierten Einstiegspunkt headless.
                entry = Path(sys.argv[1]).resolve()
                PultApp.run = lambda self: asyncio.run(smoke(self, root))
                try:
                    runpy.run_path(str(entry), run_name="__main__")
                except SystemExit as error:
                    assert error.code in (None, 0)
            else:
                asyncio.run(smoke(PultApp(), root))
    finally:
        os.chdir(old_cwd)
    print(
        "Installiertes PULT: Einstiegspunkt, Setup, Neustart, Defaults und Lizenzdialog erfolgreich."
    )


if __name__ == "__main__":
    main()
