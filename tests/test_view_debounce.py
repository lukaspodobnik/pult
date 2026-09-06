import asyncio

from test_ui_integration import prepare_root
from textual.screen import Screen

from schooltools_tui.app import SchooltoolsApp
from schooltools_tui.initialization.school_class import initialize_school_class
from schooltools_tui.school.school_class import SchoolClass
from schooltools_tui.screens.main_screen import MainScreen
from schooltools_tui.views.home_view import HomeView
from schooltools_tui.views.school_class_view import SchoolClassView
from schooltools_tui.widgets.navigation import ViewPicker


def test_burst_builds_only_last_view_and_defers_hidden_screen(tmp_path, monkeypatch):
    config = prepare_root(tmp_path)
    initialize_school_class(
        tmp_path, config.active_school_year, SchoolClass("5B", 5, ["mathematik"])
    )
    monkeypatch.setattr("schooltools_tui.app.load_app_config", lambda: config)
    # Genug Abstand für die Prüfung des Zustands vor Ablauf des Timers.
    monkeypatch.setattr(MainScreen, "VIEW_DEBOUNCE_SECONDS", 0.2)
    builds = []
    original = MainScreen.switch_view

    async def track(self, view):
        builds.append(
            view.school_class.id if isinstance(view, SchoolClassView) else "home"
        )
        await original(self, view)

    monkeypatch.setattr(MainScreen, "switch_view", track)

    async def run():
        app = SchooltoolsApp()
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause(0.3)
            screen = app.screen
            picker = screen.query_one(ViewPicker)
            home = screen.query_one(HomeView)
            assert builds == ["home"]
            for i in range(20):
                picker.highlighted = 1 if i % 2 == 0 else 2
            await pilot.pause(0.02)
            assert picker.highlighted == 2
            assert screen.query_one(HomeView) is home
            assert builds == ["home"]
            assert screen.check_action("complete_next_lesson", ()) is None
            await pilot.pause(0.3)
            assert builds == ["home", "5B"]
            assert screen.active_school_class_id == "5B"
            assert screen._pending_view_id is None

            picker.highlighted = 1
            await pilot.pause(0.02)
            await app.push_screen(Screen())
            await pilot.pause(0.3)
            assert builds == ["home", "5B"]
            app.pop_screen()
            await pilot.pause(0.3)
            assert builds == ["home", "5B", "5A"]
            picker.highlighted = 0
            await pilot.pause(0.3)
            assert builds == ["home", "5B", "5A", "home"]

    asyncio.run(run())
