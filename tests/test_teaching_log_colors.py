import asyncio
from datetime import date
from pathlib import Path

from textual.app import App
from textual.color import Color

from pult.progress.class_progress import (
    TeachingAction,
    TeachingLogEntry,
    TeachingOrigin,
)
from pult.views.teaching_log_view import TeachingLogView
from pult.widgets.lesson_progress_bar import LessonProgressBar


def test_log_colors_match_progress_and_follow_theme(school_class, subject, sequences):
    styles = Path(__file__).parents[1] / "src/pult/styles"
    entries = tuple(
        TeachingLogEntry(
            date(2026, 9, 7),
            subject.id,
            sequences[0].id,
            action,
            TeachingOrigin.NONE
            if action is TeachingAction.SKIPPED
            else TeachingOrigin.SCHEDULED,
            lesson_id="lesson-1"
            if action
            in {
                TeachingAction.COMPLETED,
                TeachingAction.SKIPPED,
                TeachingAction.CONTINUED,
            }
            else None,
            period=None if action is TeachingAction.SKIPPED else 1,
        )
        for action in TeachingAction
    )

    class ColorApp(App):
        CSS_PATH = [styles / "progress.tcss", styles / "teaching_log.tcss"]

        def compose(self):
            yield TeachingLogView(school_class, entries, [subject], sequences)
            yield LessonProgressBar(1, 1, 3)

    async def run():
        app = ColorApp()
        async with app.run_test() as pilot:
            colors = []
            for theme in ("gruvbox", "textual-light"):
                app.theme = theme
                await pilot.pause()
                bar = app.query_one(LessonProgressBar)
                for action in ("completed", "skipped"):
                    border = app.query_one(
                        f".teaching-log-entry.{action}"
                    ).styles.border.left[1]
                    assert (
                        border.rich_color
                        == bar.get_component_rich_style(
                            f"lesson-progress-bar--{action}"
                        ).color
                    )
                for action, variable in (
                    ("continued", "secondary"),
                    ("cancelled", "error"),
                ):
                    border = app.query_one(
                        f".teaching-log-entry.{action}"
                    ).styles.border.left[1]
                    assert border == Color.parse(app.get_css_variables()[variable])
                colors.append(
                    app.query_one(".teaching-log-entry.completed").styles.border.left[1]
                )
            assert colors[0] != colors[1]

    asyncio.run(run())
