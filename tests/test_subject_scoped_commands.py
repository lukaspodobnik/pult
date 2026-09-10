import asyncio
from dataclasses import replace
from datetime import date

import pytest
from test_ui_integration import prepare_root
from textual.widgets import Input, Select

from pult.app import PultApp
from pult.initialization.school_class import initialize_school_class
from pult.progress.class_progress import (
    ActiveSequence,
    ClassProgress,
    TeachingAction,
    TeachingLogEntry,
    TeachingOrigin,
    load_class_progress,
)
from pult.progress.commands import ProgressCommandError, undo_last_entry
from pult.school.school_class import SchoolClass
from pult.school.timetable import (
    TimetableEntry,
    get_timetable_path,
    save_timetable,
)
from pult.screens.add_extra_lesson_screen import AddExtraLessonScreen
from pult.screens.cancel_lesson_screen import CancelLessonScreen
from pult.screens.set_active_sequence_screen import SetActiveSequenceScreen
from pult.screens.teaching_log_screen import TeachingLogScreen
from pult.views.school_class_view import (
    SchoolClassView,
    SubjectProgressBlock,
)
from pult.views.teaching_log_view import TeachingLogView
from pult.widgets.navigation import ManagementPicker, ViewPicker


@pytest.mark.parametrize("management_focused", [False, True])
def test_home_key_selects_home_and_focuses_view_picker(
    multi_class_config, management_focused
):
    async def run():
        app = PultApp()
        async with app.run_test(size=(140, 42)) as pilot:
            main = await ready(app, pilot)
            picker = main.query_one(ViewPicker)
            picker.highlighted = 1
            await ready(app, pilot)
            assert main.active_school_class_id is not None
            if management_focused:
                main.query_one(ManagementPicker).focus()
            await pilot.press("f2")
            await ready(app, pilot)
            assert app.focused is picker
            assert picker.highlighted == picker.get_option_index("home")
            assert main.active_school_class_id is None
            # Auch bei bereits ausgewähltem Home den Fokus zurückholen.
            main.query_one(ManagementPicker).focus()
            await pilot.press("f2")
            assert app.focused is picker

    asyncio.run(run())


def test_management_focus_blocks_progress_commands(multi_class_config, monkeypatch):
    async def run():
        app = PultApp()
        async with app.run_test(size=(140, 42)) as pilot:
            main = await ready(app, pilot)
            await main.show_school_class_view(
                main.school_classes_by_id["9B"], "mathematik"
            )
            calls = []
            actions = {
                "n": "complete_next_lesson",
                "s": "skip_next_lesson",
                "c": "continue_next_lesson",
                "a": "cancel_next_lesson",
                "z": "add_extra_lesson",
                "p": "undo_last_entry",
                "w": "change_active_sequence",
                "u": "show_teaching_log",
            }
            for action in actions.values():
                monkeypatch.setattr(
                    main, f"action_{action}", lambda: calls.append(True)
                )
            main.query_one(ManagementPicker).focus()
            await pilot.pause()
            for key, action in actions.items():
                assert main.check_action(action, ()) is False
                assert key not in app.active_bindings
                await pilot.press(key)
            assert not calls
            main.query_one(ViewPicker).focus()
            await pilot.pause()
            await pilot.press("n")
            assert calls == [True]

    asyncio.run(run())


@pytest.fixture
def multi_class_config(tmp_path, monkeypatch):
    config = prepare_root(tmp_path)
    initialize_school_class(
        tmp_path,
        config.active_school_year,
        SchoolClass("9B", 9, ["mathematik", "informatik-ntg"]),
    )
    save_timetable(
        get_timetable_path(tmp_path, config.active_school_year),
        [
            TimetableEntry("monday", 1, "9B", "mathematik", "101"),
            TimetableEntry("monday", 2, "9B", "informatik-ntg", "102"),
        ],
    )
    monkeypatch.setattr("pult.app.load_app_config", lambda: config)
    return config


async def ready(app, pilot):
    await pilot.pause(0.3)
    for _ in range(40):
        if app.screen._pending_view_id is None:
            return app.screen
        await pilot.pause(0.05)
    raise AssertionError("Ansichtswechsel nicht abgeschlossen")


@pytest.mark.parametrize(
    "command, action",
    [
        ("complete_next_lesson", TeachingAction.COMPLETED),
        ("skip_next_lesson", TeachingAction.SKIPPED),
        ("continue_next_lesson", TeachingAction.CONTINUED),
        ("cancel_next_lesson", TeachingAction.CANCELLED),
    ],
)
def test_planned_commands_use_selected_subject(multi_class_config, command, action):
    config = multi_class_config

    async def run():
        app = PultApp()
        async with app.run_test(size=(140, 42)) as pilot:
            main = await ready(app, pilot)
            assert (
                main.load_planned_lesson_context().planned_lesson.subject_id
                == "mathematik"
            )
            await main.show_school_class_view(
                main.school_classes_by_id["9B"], "informatik-ntg"
            )
            view = main.query_one(SchoolClassView)
            assert [b.summary.subject_id for b in view.query(SubjectProgressBlock)] == [
                "informatik-ntg"
            ]
            assert (
                main.load_planned_lesson_context().planned_lesson.subject_id
                == "informatik-ntg"
            )
            await app.run_action(command, default_namespace=main)
            if command == "cancel_next_lesson":
                await pilot.pause()
                assert isinstance(app.screen, CancelLessonScreen)
                app.screen.query_one(Input).value = "Feueralarm"
                await pilot.click("#save-cancelled-lesson")
            await pilot.pause()
            progress = load_class_progress(config.root, config.active_school_year, "9B")
            assert len(progress.entries) == 1
            assert progress.entries[0].subject_id == "informatik-ntg"
            assert progress.entries[0].action is action
            assert main.active_subject_id == "informatik-ntg"
            # Ohne Termin für das ausgewählte Fach nicht auf Mathematik ausweichen.
            save_timetable(
                get_timetable_path(config.root, config.active_school_year),
                [TimetableEntry("monday", 1, "9B", "mathematik", "101")],
            )
            assert main.load_planned_lesson_context() is None

    asyncio.run(run())


def test_modals_and_log_keep_subject_scope(multi_class_config):
    config = multi_class_config

    async def run():
        app = PultApp()
        async with app.run_test(size=(140, 42)) as pilot:
            main = await ready(app, pilot)
            await main.show_school_class_view(
                main.school_classes_by_id["9B"], "informatik-ntg"
            )
            main.action_add_extra_lesson()
            await pilot.pause()
            assert isinstance(app.screen, AddExtraLessonScreen)
            assert app.screen.fixed_subject_id == "informatik-ntg"
            assert not app.screen.query("#extra-subject")
            app.screen.query_one("#extra-comment", Input).value = "Übung"
            await pilot.click("#save-extra-lesson")
            await pilot.pause()
            progress = load_class_progress(config.root, config.active_school_year, "9B")
            assert progress.entries[-1].subject_id == "informatik-ntg"

            main.action_change_active_sequence()
            await pilot.pause()
            assert isinstance(app.screen, SetActiveSequenceScreen)
            assert app.screen.available_subject_ids == ["informatik-ntg"]
            assert not app.screen.query("#active-sequence-subject")
            value = app.screen.query_one("#active-sequence", Select).value
            await pilot.click("#save-active-sequence")
            await pilot.pause()
            progress = load_class_progress(config.root, config.active_school_year, "9B")
            assert (
                next(
                    s
                    for s in progress.active_sequences
                    if s.subject_id == "informatik-ntg"
                ).sequence_id
                == value
            )
            await main.show_school_class_view(
                main.school_classes_by_id["9B"], "mathematik"
            )
            main.action_add_extra_lesson()
            await pilot.pause()
            app.screen.query_one("#extra-comment", Input).value = "Mathe"
            await pilot.click("#save-extra-lesson")
            await pilot.pause()
            await main.show_school_class_view(
                main.school_classes_by_id["9B"], "informatik-ntg"
            )
            main.action_show_teaching_log()
            await pilot.pause()
            assert isinstance(app.screen, TeachingLogScreen)
            assert {
                e.subject_id for e in app.screen.query_one(TeachingLogView).entries
            } == {"informatik-ntg"}
            picker = app.screen.query_one("#teaching-log-class-picker")
            content = app.screen.query_one("#teaching-log-content")
            assert not app.screen.query("Header")
            assert app.screen.query_one("#teaching-log-navigation").region.width == 28
            assert (picker.region.y, picker.region.bottom) == (
                content.region.y,
                content.region.bottom,
            )
            targets = list(picker.class_subjects_by_option_id.values())
            assert targets[picker.highlighted] == ("9B", "informatik-ntg")
            picker.highlighted = targets.index(("9B", "mathematik"))
            await pilot.pause(0.2)
            assert {
                e.subject_id
                for v in app.screen.query(TeachingLogView)
                if v.display
                for e in v.entries
            } == {"mathematik"}
            assert content.border_title == "Unterrichtsprotokoll · 9B · Mathematik"
            await pilot.press("escape")
            await main.action_undo_last_entry()
            await pilot.pause()
            await pilot.click("#confirm-undo")
            await pilot.pause()
            progress = load_class_progress(config.root, config.active_school_year, "9B")
            assert [e.subject_id for e in progress.entries] == ["mathematik"]

    asyncio.run(run())


def test_subject_undo_preserves_other_entries_and_active_sequences():
    entry = TeachingLogEntry(
        date(2026, 9, 7),
        "mathematik",
        "old",
        TeachingAction.COMPLETED,
        TeachingOrigin.SCHEDULED,
        lesson_id="lesson",
        period=1,
    )
    other = replace(entry, subject_id="informatik", sequence_id="inf", period=2)
    progress = ClassProgress(
        (ActiveSequence("mathematik", "new"), ActiveSequence("informatik", "inf")),
        (entry, other),
    )
    result = undo_last_entry(progress, subject_id="mathematik")
    assert result.entries == (other,)
    assert result.active_sequences == (
        ActiveSequence("mathematik", "old"),
        ActiveSequence("informatik", "inf"),
    )
    with pytest.raises(ProgressCommandError):
        undo_last_entry(result, subject_id="mathematik")


def test_open_next_lesson_uses_visible_lesson_and_returns(multi_class_config, monkeypatch):
    from datetime import datetime

    from pult.screens.lesson_screen import LessonScreen
    from pult.views.home_view import HomeView

    class Clock:
        @classmethod
        def now(cls, tz):
            return datetime(2026, 9, 16, 8, 0, tzinfo=tz)

    monkeypatch.setattr("pult.screens.main_screen.datetime", Clock)
    monkeypatch.setattr("pult.views.home_view.datetime", Clock)

    async def run():
        app = PultApp()
        async with app.run_test(size=(180, 52)) as pilot:
            main = await ready(app, pilot)
            picker = main.query_one(ViewPicker)
            for target in ("home", '["9B", "informatik-ntg"]', '["9B", "mathematik"]'):
                picker.highlighted = picker.get_option_index(target)
                await ready(app, pilot)
                expected = main.displayed_next_lesson()
                assert expected is not None
                assert main.check_action("open_next_lesson", ())
                await pilot.press("o")
                await pilot.pause()
                viewer = app.screen
                assert isinstance(viewer, LessonScreen)
                assert viewer.lesson_id == expected.lesson.id
                assert viewer.sequence.id == expected.sequence_id
                assert viewer.sequence.subject_id == expected.subject_id
                await pilot.press("escape")
                await ready(app, pilot)
                assert app.screen is main
                assert picker.get_option_at_index(picker.highlighted).id == target
                assert app.focused is picker
            picker.highlighted = picker.get_option_index("home")
            await ready(app, pilot)
            home = main.query_one(HomeView)
            home.dashboard = replace(home.dashboard, next_planned_lesson=None)
            assert main.check_action("open_next_lesson", ()) is False
            await pilot.press("o")
            assert app.screen is main
            main._pending_view_id = "home"
            assert main.check_action("open_next_lesson", ()) is None
            main._pending_view_id = None

    asyncio.run(run())
