import asyncio
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

from test_ui_integration import prepare_root
from textual.widgets import OptionList

from pult.app import PultApp
from pult.curriculum.material import Task, TaskMetadata, save_task
from pult.curriculum.sequence import load_sequence, save_sequence
from pult.screens.lesson_screen import LessonScreen
from pult.screens.select_lesson_file_screen import SelectLessonFileScreen
from pult.screens.task_screen import TaskScreen
from pult.storage import load_toml
from pult.widgets.document_viewer import DocumentPane, DocumentViewer
from pult.widgets.materials import MaterialsPane


def test_lesson_modes_material_tasks_and_editing(tmp_path, monkeypatch):
    config = prepare_root(tmp_path)
    monkeypatch.setattr("pult.app.load_app_config", lambda: config)
    example = Path(__file__).parents[1] / "examples/unterricht"
    sequence = load_sequence(example, 6, "mathematik", "formatbeispiel")
    sequence.lessons[0].preparation = "# Test\n\n" + "Langer Text.\n\n" * 100
    sequence.lessons[0].tasks = [
        Task(
            "zweitens",
            "# Zugeordnete Aufgabe",
            "Lösung",
            metadata=TaskMetadata("Zugeordnete Aufgabe", ["K5"], "I"),
        )
    ]
    save_sequence(tmp_path, sequence)
    directory = tmp_path / "sequences/6/mathematik/formatbeispiel"
    save_task(
        directory,
        Task(
            "erstens",
            "# Andere Aufgabe",
            metadata=TaskMetadata("Andere Aufgabe", ["K1"], "II"),
        ),
    )

    async def run():
        app = PultApp()
        async with app.run_test(size=(150, 44)) as pilot:
            await pilot.pause()
            screen = LessonScreen(sequence, sequence.lessons[0].id)
            await app.push_screen(screen)
            await pilot.pause(0.4)
            assert not screen.query("SequenceContext")
            assert not screen.query("#lesson-goals, #lesson-schedule")
            assert screen.query_one(MaterialsPane).display
            assert screen.query_one("#lesson-navigation").region.width == 40
            pane = screen.query_one("#lesson-preparation", DocumentPane)
            assert pane.border_title == sequence.title
            assert pane.region.width > 100
            assert pane.region.y == screen.query_one("#lesson-list-frame").region.y
            assert not screen.query("#mode-preparation, #mode-planning")
            assert all(
                "Benötigtes Material" not in w.source
                for w in screen.query(DocumentViewer)
            )
            pane.scroll_to(y=20, animate=False)
            await pilot.pause()
            position = pane.scroll_y
            await pilot.press("space")
            assert screen.show_planning
            assert screen.query_one("#lesson-planning").display
            await pilot.press("space", "a")
            await pilot.pause()
            tasks = app.screen
            assert isinstance(tasks, TaskScreen)
            assert tasks.task_id == "zweitens"
            picker = tasks.query_one(OptionList)
            picker.highlighted = picker.get_option_index("erstens")
            await pilot.pause()
            assert [t.id for t in tasks.sequence.lessons[0].tasks] == ["zweitens"]
            await pilot.press("v")
            assert [t.id for t in tasks.sequence.lessons[0].tasks] == [
                "zweitens",
                "erstens",
            ]
            assert load_toml(directory / "stunden/anteile/stunde.toml")["aufgaben"] == [
                "zweitens",
                "erstens",
            ]
            await pilot.press("escape")
            await pilot.pause()
            assert app.screen is screen
            assert pane.scroll_y == position
            assert not screen.show_planning
            monkeypatch.setattr(app, "suspend", nullcontext)

            def editor(command, *, check):
                path = Path(command[-1])
                path.write_text(
                    "- Neues Ziel\n" if path.name == "ziele.md" else "# Geändert\n"
                )
                return SimpleNamespace(returncode=0)

            monkeypatch.setattr("pult.screens.lesson_screen.subprocess.run", editor)
            await pilot.press("space", "e")
            assert isinstance(app.screen, SelectLessonFileScreen)
            await pilot.press("enter")
            await pilot.pause()
            assert screen.lesson.goals == ["Neues Ziel"]

            # Invalid data retains the last valid model.
            def invalid(command, *, check):
                Path(command[-1]).write_text("## Ungültig")
                return SimpleNamespace(returncode=0)

            monkeypatch.setattr("pult.screens.lesson_screen.subprocess.run", invalid)
            await screen.edit("verlauf.md")
            assert screen.lesson.goals == ["Neues Ziel"]
            await pilot.press("escape")

    asyncio.run(run())


def test_material_box_stable_when_empty(tmp_path, monkeypatch):
    config = prepare_root(tmp_path)
    monkeypatch.setattr("pult.app.load_app_config", lambda: config)
    from pult.curriculum.sequence import load_sequence_library

    sequence = load_sequence_library(tmp_path)[0]
    sequence.lessons[0].title = "Ein sehr langer Stundentitel " * 12 + "\nWeitere Zeile"

    async def run():
        app = PultApp()
        async with app.run_test(size=(100, 30)) as pilot:
            await app.push_screen(LessonScreen(sequence, sequence.lessons[0].id))
            await pilot.pause(0.3)
            assert app.screen.query_one(MaterialsPane).region.height == 12
            listing = app.screen.query_one("#lesson-list", OptionList)
            assert all(
                str(listing.get_option_at_index(i).prompt).count("\n") == 0
                for i in range(listing.option_count)
            )
            assert listing.virtual_size.height == listing.option_count
            await pilot.resize_terminal(70, 30)
            await pilot.pause()
            assert listing.virtual_size.height == listing.option_count

    asyncio.run(run())


def test_document_font_change_invalidates_open_viewer(tmp_path, monkeypatch):
    from dataclasses import replace

    config = prepare_root(tmp_path)
    monkeypatch.setattr("pult.app.load_app_config", lambda: config)
    example = Path(__file__).parents[1] / "examples/unterricht"
    sequence = load_sequence(example, 6, "mathematik", "formatbeispiel")
    save_sequence(tmp_path, sequence)

    async def run():
        app = PultApp()
        async with app.run_test(size=(110, 36)) as pilot:
            await pilot.pause()
            await app.push_screen(LessonScreen(sequence, sequence.lessons[0].id))
            await pilot.pause(0.4)
            viewer = app.screen.query(DocumentViewer).first()
            before = viewer.signature
            app.app_config = replace(config, document_font="source-sans-3")
            viewer.schedule_render()
            assert viewer.signature != before
            assert viewer.signature[3] == "source-sans-3"

    asyncio.run(run())
