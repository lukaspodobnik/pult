import asyncio
from dataclasses import replace
from datetime import date, time

import pytest
from test_ui_integration import prepare_root
from textual.widgets import Static

from pult.app import PultApp
from pult.progress.class_progress import (
    TeachingAction,
    TeachingLogEntry,
    TeachingOrigin,
)
from pult.progress.queries import get_class_progress_summary
from pult.school.assessment import Assessment, AssessmentKind
from pult.views.school_class_view import SchoolClassView, SequenceProgressBlock
from pult.widgets.navigation import ViewPicker


def test_held_hours_count_occurrences_and_exclude_skips_cancellations_and_assessments(
    empty_progress, sequences, timetable_entries, school_class, school_calendar
):
    def entry(action, day, period=None, lesson=None, sequence="sequence-1"):
        origin = (
            TeachingOrigin.NONE
            if action is TeachingAction.SKIPPED
            else TeachingOrigin.SCHEDULED
            if period
            else TeachingOrigin.ADDITIONAL
        )
        return TeachingLogEntry(
            date(2026, 9, day),
            "mathematik",
            sequence,
            action,
            origin,
            comment="Übung",
            period=period,
            lesson_id=lesson,
        )

    assessment = Assessment(
        "sa",
        "mathematik",
        AssessmentKind.SCHOOL_EXAM,
        "Zahlen",
        date(2026, 9, 18),
        time(8),
        45,
        (1,),
        completed_on=date(2026, 9, 18),
    )
    entries = (
        entry(TeachingAction.COMPLETED, 7, 1, "lesson-1"),
        entry(TeachingAction.CONTINUED, 7, 2, "lesson-2"),
        entry(TeachingAction.OTHER, 9, 1),
        entry(TeachingAction.OTHER, 8),
        entry(TeachingAction.CANCELLED, 16, 1, "lesson-2"),
        entry(TeachingAction.SKIPPED, 16, lesson="lesson-2"),
        entry(TeachingAction.COMPLETED, 10, 1, "lesson-3", "sequence-2"),
        TeachingLogEntry(
            date(2026, 9, 18),
            "mathematik",
            "",
            TeachingAction.ASSESSMENT_COMPLETED,
            TeachingOrigin.ASSESSMENT,
            assessment_id="sa",
            assessment_periods=(1,),
        ),
    )
    progress = replace(empty_progress, entries=entries)
    summary = get_class_progress_summary(
        progress,
        sequences,
        timetable_entries,
        school_class,
        school_calendar,
        [],
        [],
        [assessment],
    )[0]
    first, second = summary.sequences
    assert (first.held_lesson_count, second.held_lesson_count) == (4, 1)
    assert (first.completed_lesson_count, first.skipped_lesson_count) == (1, 1)
    assert summary.last_entry.entry == entries[-1]
    assert summary.last_entry.title == "1. Schulaufgabe · Zahlen"
    assert summary.last_entry.sequence_label == ""
    assert summary.next_assessment is None


def test_last_entry_uses_log_order_and_selected_subject(
    empty_progress, sequences, timetable_entries, school_class, school_calendar
):
    first = TeachingLogEntry(
        date(2026, 9, 9),
        "mathematik",
        "sequence-1",
        TeachingAction.OTHER,
        TeachingOrigin.ADDITIONAL,
        "Erster Eintrag",
    )
    latest = replace(first, comment="Zweiter Eintrag")
    entries = (
        first,
        latest,
        replace(
            first, date=date(2026, 9, 8), comment="Später erfasst, früher gehalten"
        ),
        replace(first, date=date(2026, 9, 16), subject_id="anderes"),
    )
    summary = get_class_progress_summary(
        replace(empty_progress, entries=entries),
        sequences,
        timetable_entries,
        school_class,
        school_calendar,
        [],
        [],
    )[0]
    assert summary.last_entry.entry == latest
    assert summary.sequences[0].held_lesson_count == 3


def test_class_panels_refresh_content_and_keep_long_comments_compact(
    tmp_path,
    monkeypatch,
    empty_progress,
    sequences,
    timetable_entries,
    school_class,
    subject,
    school_calendar,
):
    config = prepare_root(tmp_path)
    monkeypatch.setattr("pult.app.load_app_config", lambda: config)
    sequences[0].lessons[0].goals = ["Geheimes Ziel $x^2$"]
    sequences[0].lessons[0].material = [
        "Papierstreifen",
        "[Arbeitsblatt Zahlenstrahl](https://example.com/arbeitsblatt.pdf)",
    ]

    def summary(entries=(), assessments=None):
        return get_class_progress_summary(
            replace(empty_progress, entries=entries),
            sequences,
            timetable_entries,
            school_class,
            school_calendar,
            [],
            [],
            assessments,
        )

    async def run():
        app = PultApp()
        async with app.run_test(size=(160, 45)) as pilot:
            await pilot.pause()
            await pilot.wait_for_scheduled_animations()
            screen = app.screen
            await screen.show_school_class_view(screen.school_classes_by_id["5A"])
            view = screen.query_one(SchoolClassView)
            await view.update_data(school_class, [subject], summary())
            await pilot.pause()
            assert view.query_one(".class-next-lesson").border_title == "NÄCHSTE STUNDE"
            assert view.query_one(".lesson-capacity").border_title == "AUSBLICK"
            assert view.query_one(".class-last-entry").border_title == "ZULETZT"
            assert view.query_one(".last-entry-empty").display
            assert "Kein Leistungsnachweis" in str(
                view.query_one(".class-assessment").content
            )
            preview = " ".join(
                str(widget.content)
                for widget in view.query_one(".class-next-lesson").query(Static)
            )
            assert "Zahlen ordnen" in preview
            assert "Geheimes Ziel" not in preview
            assert view.query_one(".next-lesson-materials").display
            with app.console.capture() as capture:
                app.console.print(view.query_one(".next-lesson-material").content)
            materials = capture.get()
            assert "Papierstreifen" in materials
            assert "Arbeitsblatt Zahlenstrahl" in materials
            assert "https://" not in materials
            assert not view.query(".remaining-lessons, .available-periods")

            log = TeachingLogEntry(
                date(2026, 9, 7),
                "mathematik",
                "sequence-1",
                TeachingAction.CONTINUED,
                TeachingOrigin.SCHEDULED,
                "[bold]Wörtlicher Kommentar[/bold] " + "Langer Kommentar. " * 60,
                "lesson-1",
                1,
            )
            assessment = Assessment(
                "sa",
                "mathematik",
                AssessmentKind.SCHOOL_EXAM,
                "Zahlen",
                date(2026, 9, 7),
                time(8, 50),
                45,
                (2,),
            )
            await view.update_data(
                school_class, [subject], summary((log,), [assessment])
            )
            await pilot.pause()
            assert not view.query_one(".last-entry-empty").display
            assert view.query_one(".last-entry-action").content == "Fortgesetzt"
            assert view.query_one(".last-entry-title").content == "Zahlen ordnen"
            comment = view.query_one(".last-entry-comment")
            assert comment.content == log.comment
            assert comment.render().plain.endswith("…")
            assert comment.render().plain.startswith("[bold]")
            assert comment.size.height <= 3
            assert (
                view.query_one(".class-last-entry").region.bottom <= view.region.bottom
            )
            assert view.query_one(SequenceProgressBlock).summary.held_lesson_count == 1
            assert view.query_one(".next-lesson-title").content == "1. Schulaufgabe"
            assert view.query_one(".next-lesson-assessment-topic").content == "Zahlen"
            assert view.query_one(".class-assessment").content == "1. Schulaufgabe"
            assert view.query_one(".class-assessment-topic").content == "Zahlen"
            assert not view.query_one(".next-lesson-sequence").display
            assert not view.query_one(".next-lesson-materials").display
            assert view.query_one(".next-lesson-material").content == ""
            assert "2. Stunde" in str(view.query_one(".class-assessment-date").content)

            # Switching subject/class or undoing must clear the previous entry.
            sequences[0].lessons[0].material = []
            await view.update_data(school_class, [subject], summary())
            await pilot.pause()
            assert view.query_one(".last-entry-empty").display
            for name in ("date", "action", "title", "sequence", "comment"):
                assert not view.query_one(f".last-entry-{name}").display
            assert "Kein Leistungsnachweis" in str(
                view.query_one(".class-assessment").content
            )
            assert view.query_one(SequenceProgressBlock).summary.held_lesson_count == 0
            assert view.query_one(".next-lesson-sequence").display
            assert not view.query_one(".next-lesson-assessment-topic").display
            assert not view.query_one(".class-assessment-topic").display
            assert view.query_one(".next-lesson-materials").display
            assert (
                view.query_one(".next-lesson-material").content
                == "Keine Materialien vorgesehen"
            )

            without_lesson = replace(summary()[0], next_planned_lesson=None)
            await view.update_data(school_class, [subject], [without_lesson])
            await pilot.pause()
            assert view.query_one(".next-lesson-empty").display
            assert not view.query_one(".next-lesson-materials").display
            assert view.query_one(".next-lesson-material").content == ""

    asyncio.run(run())


@pytest.mark.parametrize("size", [(160, 45), (200, 60)])
def test_navigation_keeps_geometry_on_view_switches(tmp_path, monkeypatch, size):
    config = prepare_root(tmp_path)
    monkeypatch.setattr("pult.app.load_app_config", lambda: config)

    async def run():
        app = PultApp()
        async with app.run_test(size=size) as pilot:
            await pilot.pause()
            await pilot.wait_for_scheduled_animations()
            screen = app.screen
            picker = screen.query_one(ViewPicker)

            def regions():
                return tuple(
                    screen.query_one(selector).region
                    for selector in (
                        "#navigation",
                        "#app-logo",
                        "#view-picker",
                        "#teaching-picker",
                        "#management-picker",
                    )
                )

            original = regions()
            for target in (1, 0, 1, 0):
                picker.highlighted = target
                for _ in range(60):
                    await pilot.pause(0.02)
                    if screen._pending_view_id is None:
                        break
                assert screen._pending_view_id is None
                assert (screen.active_school_class_id is not None) == bool(target)
                assert regions() == original
                assert app.focused is picker

    asyncio.run(run())
