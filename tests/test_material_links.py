import asyncio
import threading
from pathlib import Path
from unittest.mock import Mock

import pytest
from textual.app import App

from pult.services.geogebra import GeoGebraOpenError
from pult.widgets.materials import MaterialsPane


def test_named_material_links_open_correct_targets(tmp_path, monkeypatch):
    folder = tmp_path / "stunden/test"
    folder.mkdir(parents=True)
    files = tmp_path / "dateien"
    files.mkdir()
    presentation = files / "präsentation.key"
    presentation.write_text("Testdatei")
    opened = Mock()
    monkeypatch.setattr("pult.widgets.materials.subprocess.Popen", opened)

    class MaterialsApp(App):
        def compose(self):
            yield MaterialsPane(
                "- Schere\n- [Keynote](../../dateien/pr%C3%A4sentation.key)\n- [Webseite](https://example.org/unterricht)",
                folder / "material.md",
                tmp_path,
            )

    async def run():
        app = MaterialsApp()
        browser = Mock()
        monkeypatch.setattr(app, "open_url", browser)
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.click("#material-1")
            assert Path(opened.call_args.args[0][-1]) == presentation
            await pilot.click("#material-2")
            browser.assert_called_once_with("https://example.org/unterricht")

    asyncio.run(run())


def test_geogebra_launch_keeps_material_view_responsive(tmp_path, monkeypatch):
    path = tmp_path / "Funktion ä.GGB"
    path.write_bytes(b"construction")
    started, release = threading.Event(), threading.Event()
    launched = []

    def launch(file):
        launched.append(file)
        started.set()
        assert release.wait(10)

    generic_open = Mock()
    monkeypatch.setattr("pult.widgets.materials.sys.platform", "darwin")
    monkeypatch.setattr("pult.widgets.materials.open_geogebra", launch)
    monkeypatch.setattr("pult.widgets.materials.subprocess.Popen", generic_open)

    class MaterialsApp(App):
        def compose(self):
            yield MaterialsPane(
                "- [GeoGebra](Funktion%20%C3%A4.GGB)\n- [Web](https://example.org)",
                tmp_path / "material.md",
                tmp_path,
            )

    async def run():
        app = MaterialsApp()
        browser = Mock()
        monkeypatch.setattr(app, "open_url", browser)
        async with app.run_test(size=(80, 24)) as pilot:
            try:
                await pilot.click("#material-0")
                assert await asyncio.to_thread(started.wait, 3)
                # Der GeoGebra-Start wartet noch, andere Links bleiben bedienbar.
                await pilot.click("#material-1")
                browser.assert_called_once_with("https://example.org")
                assert launched == [path]
                generic_open.assert_not_called()
            finally:
                release.set()
                await app.workers.wait_for_complete()

    asyncio.run(run())


def test_geogebra_launch_error_is_visible(tmp_path, monkeypatch):
    (tmp_path / "test.ggb").write_bytes(b"construction")
    message = "GeoGebra Calculator Suite konnte nicht gestartet werden."
    launch = Mock(side_effect=GeoGebraOpenError(message))
    monkeypatch.setattr("pult.widgets.materials.sys.platform", "darwin")
    monkeypatch.setattr("pult.widgets.materials.open_geogebra", launch)

    class MaterialsApp(App):
        def compose(self):
            yield MaterialsPane(
                "- [GeoGebra](test.ggb)", tmp_path / "material.md", tmp_path
            )

    async def run():
        app = MaterialsApp()
        notify = Mock()
        async with app.run_test(size=(80, 24)) as pilot:
            monkeypatch.setattr(app.query_one(MaterialsPane), "notify", notify)
            await pilot.click("#material-0")
            await app.workers.wait_for_complete()
            launch.assert_called_once_with(tmp_path / "test.ggb")
            notify.assert_called_once_with(message, severity="error")

    asyncio.run(run())


@pytest.mark.parametrize(
    ("platform", "extension", "opener"),
    [("linux", ".ggb", "xdg-open"), ("darwin", ".pdf", "open")],
)
def test_other_materials_keep_default_opener(
    tmp_path, monkeypatch, platform, extension, opener
):
    path = tmp_path / f"material{extension}"
    path.write_bytes(b"material")
    launch, generic_open = Mock(), Mock()
    monkeypatch.setattr("pult.widgets.materials.sys.platform", platform)
    monkeypatch.setattr("pult.widgets.materials.open_geogebra", launch)
    monkeypatch.setattr("pult.widgets.materials.subprocess.Popen", generic_open)

    class MaterialsApp(App):
        def compose(self):
            yield MaterialsPane(
                f"- [Material]({path.name})", tmp_path / "material.md", tmp_path
            )

    async def run():
        app = MaterialsApp()
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.click("#material-0")
            assert generic_open.call_args.args[0] == [opener, str(path)]
            launch.assert_not_called()

    asyncio.run(run())
