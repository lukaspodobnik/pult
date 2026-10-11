import asyncio
from datetime import date
from pathlib import Path

from test_ui_integration import prepare_root
from textual.app import App
from textual.events import MouseScrollDown

from pult.app import PultApp
from pult.initialization.school_class import initialize_school_class
from pult.progress.queries.distribution import DistributionKind, DistributionRow
from pult.school.school_class import SchoolClass
from pult.school.timetable import TimetableEntry, get_timetable_path, save_timetable
from pult.screens.distribution_screen import DistributionScreen
from pult.screens.main_screen import MainScreen
from pult.services.themes import standard_theme
from pult.views.distribution_view import (
    DistributionTable,
    DistributionTableRow,
    DistributionView,
)
from pult.widgets.navigation import TeachingPicker, ViewPicker
from pult.widgets.scrolling import VerticalScroll


def test_menu_initial_selection_class_switch_scroll_and_escape(tmp_path, monkeypatch):
    config = prepare_root(tmp_path)
    initialize_school_class(
        tmp_path, config.active_school_year, SchoolClass("5B", 5, ["mathematik"])
    )
    save_timetable(
        get_timetable_path(tmp_path, config.active_school_year),
        [
            TimetableEntry("monday", 1, "5A", "mathematik", "101"),
            TimetableEntry("wednesday", 1, "5B", "mathematik", "102"),
        ],
    )
    monkeypatch.setattr("pult.app.load_app_config", lambda: config)

    exports = []

    async def fake_export(renderer, export_config, **kwargs):
        exports.append(kwargs)
        await asyncio.sleep(0.1)
        return tmp_path / "exports/test.pdf"

    monkeypatch.setattr(
        "pult.screens.distribution_screen.export_distribution_plan", fake_export
    )

    async def run():
        app = PultApp()
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause(0.3)
            await pilot.wait_for_scheduled_animations()
            await pilot.pause()
            main = app.screen
            assert isinstance(main, MainScreen)
            classes = main.query_one(ViewPicker)
            classes.highlighted = 2
            await pilot.pause(0.3)
            assert main.active_school_class_id == "5B"
            teaching = main.query_one(TeachingPicker)
            teaching.highlighted = teaching.get_option_index("distribution")
            teaching.focus()
            await pilot.press("enter")
            await pilot.pause(0.3)
            screen = app.screen
            assert isinstance(screen, DistributionScreen)
            assert screen.subject_id == "mathematik"
            picker = screen.query_one(ViewPicker)
            assert picker.highlighted == 1
            assert "5B" in str(screen.query_one("#distribution-content").border_title)
            assert screen.query_one("#distribution-navigation").region.width == 40
            displayed_rows = screen._views[("5B", "mathematik")].rows
            await pilot.press("x")
            screen.action_export_pdf()  # Ein laufender Export wird nicht doppelt gestartet.
            picker.highlighted = 0
            await pilot.pause(0.3)
            assert len(exports) == 1
            assert exports[0]["school_class_id"] == "5B"
            assert exports[0]["rows"] is displayed_rows
            assert not screen._exporting
            assert "5A" in str(screen.query_one("#distribution-content").border_title)
            view = next(view for view in screen.query(DistributionView) if view.display)
            assert all(
                row.date.weekday() == 0 for row in view.rows if row.period is not None
            )
            body = view.query_one(VerticalScroll)
            picker.focus()
            await pilot.press("tab", "shift+tab")
            assert app.focused is picker
            body.focus()
            assert app.focused is picker
            body.post_message(MouseScrollDown(body, 1, 1, 0, 1, 0, False, False, False))
            await pilot.pause()
            assert body.scroll_y > 0
            assert app.focused is picker
            app.save_screenshot(filename="pult-stoff-screen.svg", path="/private/tmp")
            await pilot.press("escape")
            assert app.screen is main

    asyncio.run(run())


def test_full_width_sections_fixed_header_and_theme():
    styles = Path(__file__).parents[1] / "src/pult/styles/distribution.tcss"
    rows = (
        DistributionRow(
            DistributionKind.SEQUENCE, date(2026, 9, 7), "Terme (ca. 12 Std.)"
        ),
        DistributionRow(
            DistributionKind.LESSON,
            date(2026, 9, 7),
            "Terme aufstellen",
            "Computerraum",
            1,
        ),
        DistributionRow(DistributionKind.HOLIDAY, date(2026, 10, 26), "Herbstferien"),
        DistributionRow(
            DistributionKind.ASSESSMENT, date(2026, 11, 9), "SA · Terme", "08:00"
        ),
    )

    class TestApp(App):
        CSS_PATH = [styles]

        def compose(self):
            yield DistributionView(rows * 25)

    async def run():
        app = TestApp()
        app.register_theme(standard_theme())
        async with app.run_test(size=(95, 30)) as pilot:
            for theme in ("pult", "textual-light"):
                app.theme = theme
                await pilot.pause()
                view = app.query_one(DistributionView)
                body = view.query_one(VerticalScroll)
                section = body.query_one(".sequence", DistributionTableRow)
                assert section.region.width == body.scrollable_content_region.width
                assert not section.children
                tables = list(view.query(DistributionTable))
                assert all(table.render().box is not None for table in tables)
                assert (
                    len(
                        {
                            tuple(column.width for column in table.render().columns)
                            for table in tables
                        }
                    )
                    == 1
                )
                header = view.query_one(".heading")
                header_y = header.region.y
                body.scroll_to(y=20, animate=False)
                await pilot.pause()
                assert header.region.y == header_y
                assert body.scroll_y > 0
                assert (
                    body.query_one(".holiday").styles.color.rich_color
                    != tables[-1]
                    .get_component_rich_style("distribution-table--assessment")
                    .color
                )
            old_widths = view.column_widths
            await pilot.resize_terminal(75, 30)
            await pilot.pause()
            assert view.column_widths != old_widths
            assert (
                len(
                    {
                        tuple(column.width for column in table.render().columns)
                        for table in view.query(DistributionTable)
                    }
                )
                == 1
            )
            app.save_screenshot(
                filename="pult-stoffverteilungsplan.svg", path="/private/tmp"
            )

    asyncio.run(run())
