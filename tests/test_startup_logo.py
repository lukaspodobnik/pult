import asyncio
import threading

from test_ui_integration import prepare_root

from pult.app import PultApp
from pult.screens.main_screen import MainScreen
from pult.views.home_view import HomeView
from pult.widgets.startup_logo import StartupLogo


def test_startup_waits_for_dashboard_without_blocking_fade(tmp_path, monkeypatch):
    from pult.screens import main_screen

    config = prepare_root(tmp_path)
    monkeypatch.setattr("pult.app.load_app_config", lambda: config)
    original = main_screen.load_planning_data
    release = threading.Event()

    def delayed_load(*args, **kwargs):
        assert release.wait(5)
        return original(*args, **kwargs)

    monkeypatch.setattr(main_screen, "load_planning_data", delayed_load)

    async def run():
        app = PultApp()
        try:
            async with app.run_test(size=(140, 42)) as pilot:
                screen = app.screen
                assert isinstance(screen, MainScreen)
                assert screen.startup_active
                logo = screen.query_one(StartupLogo)
                assert logo.region.width == screen.size.width
                assert logo.region.height == screen.size.height
                assert screen.get_widget_at(0, screen.size.height - 1)[0] is logo
                assert screen.query_one("#main").styles.opacity == 0
                await asyncio.sleep(0.1)
                assert logo.styles.text_opacity == 1
                await asyncio.sleep(0.4)
                assert not screen._startup_faded
                await asyncio.sleep(0.85)
                assert screen._startup_faded
                assert screen.startup_active
                assert logo.styles.text_opacity == 0
                release.set()
                await pilot.pause(0.3)
                assert not screen.startup_active
                assert screen.query_one("#main").styles.opacity == 1
                assert not screen.query(StartupLogo)
                assert screen.query(HomeView)
                await app.push_screen(MainScreen())
                await pilot.pause()
                assert not app.screen.query(StartupLogo)
        finally:
            release.set()

    asyncio.run(run())
