import asyncio

from test_ui_integration import prepare_root
from textual.widgets import ContentSwitcher, DataTable

from schooltools_tui.app import SchooltoolsApp
from schooltools_tui.initialization.school_class import initialize_school_class
from schooltools_tui.school.school_class import SchoolClass
from schooltools_tui.school.timetable import (
    TimetableEntry,
    get_timetable_path,
    save_timetable,
)
from schooltools_tui.views.home_view import HomeView
from schooltools_tui.views.school_class_view import SchoolClassView
from schooltools_tui.widgets.dashboard.timetable import TimetablePanel


def test_views_are_reused_and_hidden_home_does_not_steal_selection(
    tmp_path, monkeypatch
):
    config = prepare_root(tmp_path)
    initialize_school_class(
        tmp_path, config.active_school_year, SchoolClass("5B", 5, ["mathematik"])
    )
    monkeypatch.setattr("schooltools_tui.app.load_app_config", lambda: config)

    async def run():
        app = SchooltoolsApp()
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause(0.2)
            screen = app.screen
            switcher = screen.query_one(ContentSwitcher)
            for _ in range(20):
                if isinstance(switcher.visible_content, HomeView):
                    break
                await pilot.pause(0.05)
            home = screen.query_one(HomeView)
            timetable = home.query_one(TimetablePanel)
            assert len(switcher.children) == 1
            assert switcher.visible_content is home
            await screen.show_school_class_view(screen.school_classes_by_id["5A"])
            class_view = screen.query_one(SchoolClassView)
            class_content = class_view.query_one("#school-class-content")
            assert not home.display
            assert switcher.visible_content is class_view
            await screen.show_home_view()
            assert screen.query_one(HomeView) is home
            assert home.query_one(TimetablePanel) is timetable
            await screen.show_school_class_view(screen.school_classes_by_id["5A"])
            assert class_view.query_one("#school-class-content") is class_content
            await screen.show_school_class_view(screen.school_classes_by_id["5B"])
            assert screen.query_one(SchoolClassView) is class_view
            assert class_view.school_class.id == "5B"
            assert len(switcher.children) == 2

            entries = [TimetableEntry("monday", 1, "5A", "mathematik", "101")]
            save_timetable(
                get_timetable_path(tmp_path, config.active_school_year), entries
            )
            await screen.timetable_edit_finished(None)
            assert switcher.visible_content is class_view
            assert screen.active_school_class_id == "5B"
            await screen.show_home_view()
            assert screen.query_one(HomeView) is home
            assert home.timetable_entries == entries
            assert home.query_one(TimetablePanel) is timetable
            assert "5A" in str(home.query_one(DataTable).get_cell("1", "monday"))
            assert len(switcher.children) == 2

    asyncio.run(run())
