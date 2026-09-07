import asyncio
from dataclasses import replace
from datetime import date, timedelta

import pytest
from test_ui_integration import prepare_root
from textual.widgets import DataTable, OptionList

from schooltools_tui.app import SchooltoolsApp
from schooltools_tui.initialization.school_class import initialize_school_class
from schooltools_tui.progress.class_progress import (
    TeachingAction,
    TeachingLogEntry,
    TeachingOrigin,
    load_class_progress,
    save_class_progress,
)
from schooltools_tui.school.school_class import SchoolClass
from schooltools_tui.school.timetable import TimetableEntry
from schooltools_tui.screens.edit_timetable_entry_screen import (
    TimetableEditAction,
    TimetableEditResult,
)
from schooltools_tui.screens.edit_timetable_screen import EditTimetableScreen
from schooltools_tui.screens.teaching_log_screen import TeachingLogScreen
from schooltools_tui.views.teaching_log_view import TeachingLogView


def test_cell_updates_preserve_table_and_fixed_columns(tmp_path, monkeypatch):
    config = prepare_root(tmp_path)
    monkeypatch.setattr("schooltools_tui.app.load_app_config", lambda: config)

    async def run():
        app = SchooltoolsApp()
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            await app.push_screen(EditTimetableScreen())
            await pilot.pause()
            screen = app.screen
            table = screen.query_one(DataTable)
            table.move_cursor(row=2, column=1)
            cursor = table.cursor_coordinate
            columns = list(table.ordered_columns)
            rows = list(table.ordered_rows)
            widths = []
            for room, action in [
                ("12345678901234567890", TimetableEditAction.SAVE),
                ("1", TimetableEditAction.SAVE),
                ("1", TimetableEditAction.DELETE),
            ]:
                entry = TimetableEntry("tuesday", 3, "5A", "mathematik", room)
                screen.timetable_entry_edited(TimetableEditResult(action, entry))
                await pilot.pause()
                cell = str(table.get_cell("3", "tuesday"))
                assert ("5A · Ma" in cell) == (action is TimetableEditAction.SAVE)
                assert "--" not in str(table.get_cell("1", "monday"))
                assert table.cursor_coordinate == cursor
                assert table.has_focus
                assert all(a is b for a, b in zip(columns, table.ordered_columns))
                assert all(a is b for a, b in zip(rows, table.ordered_rows))
                widths.append(table.ordered_columns[1].content_width)
            assert widths[0] == widths[1] == widths[2]
            await pilot.resize_terminal(206, 46)
            await pilot.pause()
            assert table.cursor_coordinate == cursor
            assert len({column.width for column in table.ordered_columns}) == 1
            assert table.ordered_columns[1].width > widths[0]
            assert (
                sum(row.height for row in table.ordered_rows)
                == table.content_size.height - table.header_height
            )
            assert all(row.height >= 3 for row in table.ordered_rows)
            for size in [(180, 42), (241, 70), (80, 24)]:
                await pilot.resize_terminal(*size)
                await pilot.pause()
                assert table.cursor_coordinate == cursor
                assert len(table.columns) == 5
                assert len({column.width for column in table.ordered_columns}) == 1
                assert all(row.height >= 3 for row in table.ordered_rows)
            assert table.max_scroll_y > 0

    asyncio.run(run())


@pytest.mark.parametrize("initial_class", [None, "5B"])
def test_log_initial_build_once_and_scrolls_to_latest(
    tmp_path, monkeypatch, initial_class
):
    config = prepare_root(tmp_path)
    initialize_school_class(
        tmp_path, config.active_school_year, SchoolClass("5B", 5, ["mathematik"])
    )
    for class_id in ("5A", "5B"):
        progress = load_class_progress(tmp_path, config.active_school_year, class_id)
        entries = tuple(
            TeachingLogEntry(
                date(2026, 9, 15) + timedelta(days=i),
                "mathematik",
                progress.active_sequences[0].sequence_id,
                TeachingAction.OTHER,
                TeachingOrigin.ADDITIONAL,
                comment="Langer Kommentar " * 20,
            )
            for i in range(30)
        )
        save_class_progress(
            tmp_path,
            config.active_school_year,
            class_id,
            replace(progress, entries=entries),
        )
    monkeypatch.setattr("schooltools_tui.app.load_app_config", lambda: config)
    calls = []
    original = TeachingLogScreen.show_teaching_log

    async def track(self, school_class):
        calls.append(school_class.id)
        await original(self, school_class)

    monkeypatch.setattr(TeachingLogScreen, "show_teaching_log", track)

    async def run():
        app = SchooltoolsApp()
        async with app.run_test(size=(100, 30)) as pilot:
            await pilot.pause()
            await app.push_screen(TeachingLogScreen(initial_class))
            await pilot.pause()
            assert calls == [initial_class or "5A"]
            view = app.screen.query_one(TeachingLogView)
            assert view.scroll_y == view.max_scroll_y > 0
            picker = app.screen.query_one("#teaching-log-class-picker", OptionList)
            picker.highlighted = 0 if initial_class == "5B" else 1
            await pilot.pause()
            assert calls == [
                initial_class or "5A",
                "5A" if initial_class == "5B" else "5B",
            ]
            view = app.screen.query_one(TeachingLogView)
            assert view.scroll_y == view.max_scroll_y > 0

    asyncio.run(run())
