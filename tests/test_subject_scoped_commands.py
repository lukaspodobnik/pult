import asyncio
from dataclasses import replace
from datetime import date

import pytest
from test_ui_integration import prepare_root
from textual.widgets import Input, Select

from schooltools_tui.app import SchooltoolsApp
from schooltools_tui.initialization.school_class import initialize_school_class
from schooltools_tui.progress.class_progress import (
    ActiveSequence,
    ClassProgress,
    TeachingAction,
    TeachingLogEntry,
    TeachingOrigin,
    load_class_progress,
)
from schooltools_tui.progress.commands import ProgressCommandError, undo_last_entry
from schooltools_tui.school.school_class import SchoolClass
from schooltools_tui.school.timetable import (
    TimetableEntry,
    get_timetable_path,
    save_timetable,
)
from schooltools_tui.screens.add_extra_lesson_screen import AddExtraLessonScreen
from schooltools_tui.screens.cancel_lesson_screen import CancelLessonScreen
from schooltools_tui.screens.set_active_sequence_screen import SetActiveSequenceScreen
from schooltools_tui.screens.teaching_log_screen import TeachingLogScreen
from schooltools_tui.views.school_class_view import (
    SchoolClassView,
    SubjectProgressBlock,
)
from schooltools_tui.views.teaching_log_view import TeachingLogView


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
    monkeypatch.setattr("schooltools_tui.app.load_app_config", lambda: config)
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
        app = SchooltoolsApp()
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
        app = SchooltoolsApp()
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
            await pilot.pause()
            assert {
                e.subject_id for e in app.screen.query_one(TeachingLogView).entries
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
