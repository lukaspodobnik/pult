import asyncio
from dataclasses import replace
from unittest.mock import AsyncMock

from test_ui_integration import prepare_root
from textual.widgets import Select

from pult.app import PultApp
from pult.screens.common.confirmation_screen import ConfirmationScreen
from pult.screens.main_screen import MainScreen
from pult.screens.settings.renderer_setup_screen import RendererSetupScreen
from pult.screens.settings.settings_screen import SettingsScreen
from pult.services.documents.renderer_setup import setup_failure


async def wait_for_screen(app, pilot, screen_type):
    for _ in range(60):
        await pilot.pause(0.05)
        if isinstance(app.screen, screen_type):
            return app.screen
    raise AssertionError(f"{screen_type.__name__} wurde nicht geöffnet")


def test_startup_offer_follows_year_dialog_and_later_persists(tmp_path, monkeypatch):
    config = prepare_root(tmp_path)
    monkeypatch.setattr("pult.app.load_app_config", lambda: config)
    monkeypatch.setattr("pult.app.get_suggested_school_year", lambda *_: "2027-2028")

    async def run():
        app = PultApp()
        app.document_renderer.check_available = AsyncMock(
            side_effect=RuntimeError("Executable doesn't exist")
        )
        app.renderer_setup.install = AsyncMock()
        async with app.run_test(size=(160, 46)) as pilot:
            await wait_for_screen(app, pilot, ConfirmationScreen)
            assert not any(isinstance(s, RendererSetupScreen) for s in app.screen_stack)
            await pilot.press("escape")
            dialog = await wait_for_screen(app, pilot, RendererSetupScreen)
            assert dialog.result.state == "missing"
            app.renderer_setup.install.assert_not_called()
            await pilot.click("#renderer-close")
            await pilot.pause()
            assert isinstance(app.screen, MainScreen)
            assert not app.renderer_setup.should_offer()
        # Auch ein neuer Prozess würde dieselbe Entscheidung laden.
        assert not PultApp().renderer_setup.should_offer()

    asyncio.run(run())


def test_slow_font_check_does_not_block_other_settings_or_lose_saved_font(
    tmp_path, monkeypatch
):
    config = replace(prepare_root(tmp_path), document_font="avenir-next")
    monkeypatch.setattr("pult.app.load_app_config", lambda: config)
    monkeypatch.setattr("pult.app.get_suggested_school_year", lambda *_: None)

    async def pending(_):
        await asyncio.Future()

    monkeypatch.setattr(
        "pult.services.documents.document_rendering.DocumentRenderer.avenir_available",
        pending,
    )

    async def run():
        app = PultApp()
        async with app.run_test(size=(160, 46)) as pilot:
            await pilot.pause(0.3)
            main = app.screen
            settings = SettingsScreen()
            await app.push_screen(settings, main.settings_changed)
            await pilot.pause()
            assert settings.query_one("#settings-document-font", Select).disabled
            settings.query_one("#settings-editor", Select).value = "nano"
            await pilot.click("#save-settings")
            await pilot.pause()
            assert isinstance(app.screen, MainScreen)
            assert app.require_config().editor == "nano"
            assert app.require_config().document_font == "avenir-next"

    asyncio.run(run())


def test_cancel_waits_for_download_cleanup(tmp_path, monkeypatch):
    config = prepare_root(tmp_path)
    monkeypatch.setattr("pult.app.load_app_config", lambda: config)
    monkeypatch.setattr("pult.app.get_suggested_school_year", lambda *_: None)

    async def run():
        app = PultApp()
        app.renderer_setup.defer()
        started, stopped = asyncio.Event(), asyncio.Event()

        async def install(output):
            started.set()
            try:
                await asyncio.Future()
            finally:
                await asyncio.sleep(0.05)
                stopped.set()

        app.renderer_setup.install = install
        async with app.run_test(size=(160, 46)) as pilot:
            await pilot.pause(0.3)
            await app.push_screen(
                RendererSetupScreen(
                    setup_failure(RuntimeError("Executable doesn't exist"))
                )
            )
            await pilot.pause()
            await pilot.click("#renderer-install")
            await asyncio.wait_for(started.wait(), 1)
            await pilot.press("escape")
            await pilot.pause()
            assert stopped.is_set()
            assert isinstance(app.screen, MainScreen)

    asyncio.run(run())


def test_open_document_recovers_from_text_fallback_after_setup(tmp_path, monkeypatch):
    from PIL import Image
    from textual.app import App
    from textual.widgets import Markdown, Static

    from pult.services.documents import material_rendering as graphics
    from pult.widgets.document_viewer import DocumentPane, DocumentViewer

    class Tile(Static):
        def __init__(self, image, **kwargs):
            super().__init__("", **kwargs)

    class Renderer:
        generation = 0

        async def render(
            self, source, path, directory, width, font_size, *colors, **kwargs
        ):
            if not self.generation:
                raise RuntimeError("Executable doesn't exist")
            path = tmp_path / "document.png"
            Image.new("RGB", (width, 100), colors[0]).save(path)
            return path

    class ViewerApp(App):
        def compose(self):
            with DocumentPane():
                yield DocumentViewer("# Inhalt", tmp_path / "text.md", tmp_path)

    monkeypatch.setattr(graphics, "GRAPHICS", Tile)
    monkeypatch.setattr(graphics, "CELL", (10, 20))

    async def run():
        app = ViewerApp()
        app.document_renderer = Renderer()
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause(0.8)
            await app.workers.wait_for_complete()
            assert app.query(Markdown) and not app.query(Tile)
            app.document_renderer.generation += 1
            await pilot.pause(0.8)
            await app.workers.wait_for_complete()
            assert app.query(Tile) and not app.query(Markdown)

    asyncio.run(run())
