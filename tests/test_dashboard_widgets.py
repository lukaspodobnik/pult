import asyncio
from datetime import datetime

from textual.app import App, ComposeResult

from pult.progress.queries import get_home_dashboard_summary
from pult.views.home_view import HomeView


def test_dashboard_refreshes_once_when_the_day_changes(
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
        current = datetime(2026, 9, 7, 8, 10)

        @classmethod
        def now(cls, tz):
            return cls.current.replace(tzinfo=tz)

    monkeypatch.setattr("pult.views.home_view.datetime", Clock)
    dashboard = get_home_dashboard_summary(
        Clock.current,
        {school_class.id: empty_progress},
        sequences,
        timetable_entries,
        periods,
        [school_class],
        school_calendar,
        [],
        {school_class.id: []},
    )

    class DashboardApp(App):
        refresh_requests = 0

        def compose(self) -> ComposeResult:
            yield HomeView(timetable_entries, [subject], periods, sequences, dashboard)

        def on_home_view_dashboard_refresh_requested(self):
            self.refresh_requests += 1

    async def run():
        app = DashboardApp()
        async with app.run_test() as pilot:
            await pilot.pause()
            view = app.query_one(HomeView)
            view.refresh_time_highlight()
            await pilot.pause()
            assert app.refresh_requests == 0
            Clock.current = datetime(2026, 9, 8, 0, 1)
            view.refresh_time_highlight()
            view.refresh_time_highlight()
            await pilot.pause()
            assert app.refresh_requests == 1

    asyncio.run(run())


def test_class_overview_updates_balances_and_removes_old_rows(subject):
    from pult.progress.queries.dashboard import ClassBalance
    from pult.widgets.dashboard.class_overview import ClassOverviewPanel

    class OverviewApp(App):
        CSS_PATH = "../src/pult/styles/home.tcss"

        def compose(self):
            yield ClassOverviewPanel((), {subject.id: subject})

    async def run():
        app = OverviewApp()
        async with app.run_test(size=(90, 20)) as pilot:
            panel = app.query_one(ClassOverviewPanel)
            balances = tuple(
                ClassBalance(f"{i}A", subject.id, i - 6) for i in range(1, 20)
            )
            await panel.update_data(balances, {subject.id: subject})
            await pilot.pause()
            assert len(panel.query(".class-balance-row")) == 19
            assert (
                panel.query(".class-balance-row .balance-difference").first().content
                == "-5 Std."
            )
            assert all(
                w.content == "—"
                for w in panel.query(".class-balance-row .balance-assessments")
            )
            await panel.update_data(
                (ClassBalance("5A", subject.id, 2),), {subject.id: subject}
            )
            await pilot.pause()
            assert len(panel.query(".class-balance-row")) == 1
            assert (
                panel.query(".class-balance-row .balance-difference").first().content
                == "+2 Std."
            )

    asyncio.run(run())
