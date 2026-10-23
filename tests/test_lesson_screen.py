import asyncio
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

from test_ui_integration import prepare_root

from pult.app import PultApp
from pult.curriculum.material import Task, TaskMetadata
from pult.curriculum.sequence import load_sequence, save_sequence
from pult.screens.teaching.lesson_screen import LessonScreen
from pult.screens.teaching.select_lesson_file_screen import SelectLessonFileScreen
from pult.screens.teaching.task_screen import TaskScreen
from pult.widgets.document_viewer import DocumentPane, DocumentViewer


def test_lesson_planning_task_navigation_and_editor_reload(tmp_path, monkeypatch):
    config = prepare_root(tmp_path)
    monkeypatch.setattr("pult.app.load_app_config", lambda: config)
    example = Path(__file__).parents[1] / "examples/unterricht"
    sequence = load_sequence(example, 6, "mathematik", "formatbeispiel")
    sequence.lessons[0].preparation = "# Vorbereitung\n\nEin Beispiel."
    sequence.lessons[0].tasks = [
        Task(
            "zweitens",
            "# Zugeordnete Aufgabe",
            "Lösung",
            metadata=TaskMetadata("Zugeordnete Aufgabe", ["K5"], "I"),
        )
    ]
    save_sequence(tmp_path, sequence)

    async def run():
        app = PultApp()
        async with app.run_test(size=(160, 46)) as pilot:
            await pilot.pause()
            screen = LessonScreen(sequence, sequence.lessons[0].id)
            await app.push_screen(screen)
            await pilot.pause(0.4)
            pane = screen.query_one("#lesson-preparation", DocumentPane)
            assert (
                pane.query_one(DocumentViewer).source == sequence.lessons[0].preparation
            )
            await pilot.press("space")
            assert screen.show_planning
            assert screen.query_one("#lesson-planning").display
            await pilot.press("space", "a")
            await pilot.pause()
            tasks = app.screen
            assert isinstance(tasks, TaskScreen)
            assert tasks.task_id == "zweitens"
            await pilot.press("escape")
            await pilot.pause()
            assert app.screen is screen
            assert not screen.show_planning
            monkeypatch.setattr(app, "suspend", nullcontext)

            def editor(command, *, check):
                path = Path(command[-1])
                path.write_text(
                    "- Neues Ziel\n" if path.name == "ziele.md" else "# Geändert\n"
                )
                return SimpleNamespace(returncode=0)

            monkeypatch.setattr(
                "pult.screens.teaching.lesson_screen.subprocess.run", editor
            )
            await pilot.press("space", "e")
            assert isinstance(app.screen, SelectLessonFileScreen)
            await pilot.press("enter")
            await pilot.pause()
            assert screen.lesson.goals == ["Neues Ziel"]

            # Invalid data retains the last valid model.
            def invalid(command, *, check):
                Path(command[-1]).write_text("## Ungültig")
                return SimpleNamespace(returncode=0)

            monkeypatch.setattr(
                "pult.screens.teaching.lesson_screen.subprocess.run", invalid
            )
            await screen.edit("verlauf.md")
            assert screen.lesson.goals == ["Neues Ziel"]
            await pilot.press("escape")

    asyncio.run(run())
