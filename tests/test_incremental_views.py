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
    DailyAdditionalEntry,
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
    DailyAdditionalRow,
    DailyScheduleRow,
)
from pult.widgets.dashboard.next_lesson import NextLessonPanel
from pult.widgets.lesson_progress_bar import LessonProgressBar


def test_class_updates_keep_blocks_and_clear_optional_content(
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
            first = block.query_one(SequenceProgressBlock)
            bar = first.query_one(LessonProgressBar)
            title = first.query_one(".progress-title", Static)
            assert block.query_one(".next-lesson-tasks").display
            assert not block.query_one(".next-lesson-notes").display
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
            assert view.query_one(SubjectProgressBlock) is block
            assert block.query_one(SequenceProgressBlock) is first
            assert first.query_one(LessonProgressBar) is bar
            assert first.query_one(".progress-title") is title
            assert bar.completed == 1
            assert not first.has_class("active")
            assert len(block.query(SequenceProgressBlock)) == 1
            assert block.query_one(".next-lesson-empty").display
            for name in ("title", "date", "tasks", "notes"):
                assert not block.query_one(f".next-lesson-{name}").display
            assert block.query_one(".lesson-balance").has_class("negative")

            empty = replace(completed, completed_lesson_count=0, total_lesson_count=0)
            expanded = replace(
                summary, sequences=(empty, *summary.sequences), total_lesson_count=3
            )
            second_subject = replace(subject, id="anderes", name="Anderes Fach")
            second_summary = replace(changed, subject_id="anderes")
            await view.update_data(
                other_class, [subject, second_subject], (expanded, second_summary)
            )
            assert len(view.query(SubjectProgressBlock)) == 2
            assert len(block.query(SequenceProgressBlock)) == 3
            assert first.query_one(".empty-sequence-hint").display
            assert first.query_one(LessonProgressBar) is bar
            assert bar.total == 0
            await view.update_data(school_class, [subject], summaries)
            assert len(view.query(SubjectProgressBlock)) == 1
            assert len(block.query(SequenceProgressBlock)) == 2
            assert not first.query_one(".empty-sequence-hint").display
            assert block.query_one(".next-lesson-tasks").display
            assert not block.query_one(".next-lesson-empty").display
            assert not block.query_one(".lesson-balance").has_class("negative")

    asyncio.run(run())


def test_dashboard_updates_preserve_widgets_and_resize_rows(
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
            table = view.query_one(DataTable)
            row = view.query_one(DailyScheduleRow)
            lesson_label = row.query_one(".day-entry-lesson")
            panel = view.query_one(NextLessonPanel)
            heading = panel.query_one(".next-lesson-heading")
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
            assert view.query_one(DataTable) is table
            assert "202" in str(table.get_cell("1", "monday"))
            assert view.query_one(DailyScheduleRow) is row
            assert row.query_one(".day-entry-lesson") is lesson_label
            assert not lesson_label.display
            assert len(view.query(DailyScheduleRow)) == 1
            assert panel.query_one(".next-lesson-heading") is heading
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
            extra = DailyAdditionalEntry(
                school_class.id,
                replace(
                    log,
                    action=TeachingAction.OTHER,
                    origin=TeachingOrigin.ADDITIONAL,
                    period=None,
                    comment="Übung",
                ),
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
                    additional_entries=(extra,),
                ),
            )
            await view.update_data(entries, [subject], periods, sequences, with_log)
            assert row.has_class("cancelled")
            assert str(row.query_one(".day-status", Static).render()) == "×"
            additional = view.query_one(DailyAdditionalRow)
            assert additional.query_one(".day-entry-lesson").display
            no_comment = replace(
                with_log,
                daily_schedule=replace(
                    with_log.daily_schedule,
                    additional_entries=(
                        replace(extra, log_entry=replace(extra.log_entry, comment="")),
                    ),
                ),
            )
            await view.update_data(entries, [subject], periods, sequences, no_comment)
            assert view.query_one(DailyAdditionalRow) is additional
            assert not additional.query_one(".day-entry-lesson").display
            await view.update_data(
                timetable_entries, [subject], periods, sequences, dashboard
            )
            assert not row.has_class("cancelled")
            assert len(view.query(DailyAdditionalRow)) == 0
            assert view.query_one(DailyScheduleRow) is row
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
            assert table.row_count == 1
            assert len(view.query(DailyScheduleRow)) == 0
            assert view.query_one("#daily-schedule .dashboard-empty").display

    asyncio.run(run())
