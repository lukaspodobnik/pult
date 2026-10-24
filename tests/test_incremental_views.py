import asyncio
from dataclasses import replace
from datetime import datetime

from textual.app import App, ComposeResult
from textual.widgets import DataTable, Static

from pult.progress.class_progress import (
    TeachingAction,
    TeachingLogEntry,
    TeachingOrigin,
)
from pult.progress.queries import (
    get_class_progress_summary,
    get_home_dashboard_summary,
)
from pult.views.home_view import HomeView
from pult.views.school_class_view import (
    SchoolClassView,
    SequenceProgressBlock,
    SubjectProgressBlock,
)
from pult.widgets.dashboard.daily_schedule import (
    DailyScheduleRow,
)
from pult.widgets.dashboard.next_lesson import NextLessonPanel
from pult.widgets.lesson_progress_bar import LessonProgressBar


def test_class_updates_progress_and_clears_optional_content(
    school_class, subject, sequences, empty_progress, school_calendar, timetable_entries
):
    summaries = get_class_progress_summary(
        empty_progress,
        sequences,
        timetable_entries,
        school_class,
        school_calendar,
        [],
        [],
    )

    class TestApp(App):
        def compose(self) -> ComposeResult:
            yield SchoolClassView(school_class, [subject], summaries)

    async def run():
        app = TestApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            view = app.query_one(SchoolClassView)
            block = view.query_one(SubjectProgressBlock)
            assert block.query_one(".next-lesson-title").display
            summary = summaries[0]
            completed = replace(
                summary.sequences[0], completed_lesson_count=1, is_active=False
            )
            changed = replace(
                summary,
                sequences=(completed,),
                completed_lesson_count=1,
                total_lesson_count=2,
                available_period_count=0,
                next_planned_lesson=None,
            )
            other_class = replace(school_class, id="5B")
            await view.update_data(other_class, [subject], (changed,))
            block = view.query_one(SubjectProgressBlock)
            first = block.query_one(SequenceProgressBlock)
            bar = first.query_one(LessonProgressBar)
            assert bar.completed == 1
            assert len(block.query(SequenceProgressBlock)) == 1
            assert block.query_one(".next-lesson-empty").display
            for name in ("sequence", "date", "title"):
                assert not block.query_one(f".next-lesson-{name}").display

            empty = replace(completed, completed_lesson_count=0, total_lesson_count=0)
            expanded = replace(
                summary, sequences=(empty, *summary.sequences), total_lesson_count=3
            )
            second_subject = replace(subject, id="anderes", name="Anderes Fach")
            second_summary = replace(changed, subject_id="anderes")
            await view.update_data(
                other_class, [subject, second_subject], (expanded, second_summary)
            )
            block = view.query(SubjectProgressBlock).first()
            first = block.query(SequenceProgressBlock).first()
            bar = first.query_one(LessonProgressBar)
            assert len(view.query(SubjectProgressBlock)) == 2
            assert len(block.query(SequenceProgressBlock)) == 3
            assert first.query_one(".empty-sequence-hint").display
            assert bar.total == 0
            await view.update_data(school_class, [subject], summaries)
            block = view.query_one(SubjectProgressBlock)
            first = block.query(SequenceProgressBlock).first()
            assert len(view.query(SubjectProgressBlock)) == 1
            assert len(block.query(SequenceProgressBlock)) == 2
            assert not first.query_one(".empty-sequence-hint").display
            assert block.query_one(".next-lesson-title").display
            assert not block.query_one(".next-lesson-empty").display

    asyncio.run(run())


def test_dashboard_updates_content_and_clears_removed_rows(
    monkeypatch,
    school_class,
    subject,
    sequences,
    empty_progress,
    school_calendar,
    timetable_entries,
    periods,
):
    class Clock:
        @classmethod
        def now(cls, tz):
            return datetime(2026, 9, 7, 8, 10, tzinfo=tz)

    monkeypatch.setattr("pult.views.home_view.datetime", Clock)
    dashboard = get_home_dashboard_summary(
        datetime(2026, 9, 7, 8, 10),
        {school_class.id: empty_progress},
        sequences,
        timetable_entries,
        periods,
        [school_class],
        school_calendar,
        [],
        {school_class.id: []},
    )

    class TestApp(App):
        def compose(self) -> ComposeResult:
            yield HomeView(timetable_entries, [subject], periods, sequences, dashboard)

    async def run():
        app = TestApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            view = app.query_one(HomeView)
            changed = replace(
                dashboard,
                next_planned_lesson=None,
                daily_schedule=replace(
                    dashboard.daily_schedule,
                    timetable_entries=(
                        replace(
                            dashboard.daily_schedule.timetable_entries[0],
                            planned_lesson=None,
                        ),
                    ),
                ),
            )
            entries = [replace(entry, room="202") for entry in timetable_entries]
            await view.update_data(entries, [subject], periods, sequences, changed)
            table = view.query_one(DataTable)
            row = view.query_one(DailyScheduleRow)
            lesson_label = row.query_one(".day-entry-lesson")
            panel = view.query_one(NextLessonPanel)
            heading = panel.query_one(".next-lesson-heading")
            assert "202" in str(table.get_cell("1", "monday"))
            assert not lesson_label.display
            assert len(view.query(DailyScheduleRow)) == 1
            assert not heading.display
            assert panel.query_one(".dashboard-empty").display
            log = TeachingLogEntry(
                dashboard.daily_schedule.date,
                subject.id,
                sequences[0].id,
                TeachingAction.CANCELLED,
                TeachingOrigin.SCHEDULED,
                period=1,
            )
            with_log = replace(
                changed,
                daily_schedule=replace(
                    changed.daily_schedule,
                    timetable_entries=(
                        replace(
                            changed.daily_schedule.timetable_entries[0], log_entry=log
                        ),
                    ),
                ),
            )
            await view.update_data(entries, [subject], periods, sequences, with_log)
            row = view.query_one(DailyScheduleRow)
            assert row.has_class("cancelled")
            assert str(row.query_one(".day-status", Static).render()) == "×"
            await view.update_data(
                timetable_entries, [subject], periods, sequences, dashboard
            )
            row = view.query(DailyScheduleRow).first()
            panel = view.query_one(NextLessonPanel)
            lesson_label = row.query_one(".day-entry-lesson")
            heading = panel.query_one(".next-lesson-heading")
            assert not row.has_class("cancelled")
            assert len(view.query(DailyScheduleRow)) == 2
            assert lesson_label.display
            assert heading.display
            assert not panel.query_one(".dashboard-empty").display
            await view.update_data(
                [],
                [subject],
                periods[:1],
                sequences,
                replace(
                    changed,
                    daily_schedule=replace(
                        changed.daily_schedule, timetable_entries=()
                    ),
                ),
            )
            assert view.query_one(DataTable).row_count == 1
            assert len(view.query(DailyScheduleRow)) == 0
            assert view.query_one("#daily-schedule .dashboard-empty").display

    asyncio.run(run())
