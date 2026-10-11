import asyncio
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

from test_ui_integration import prepare_root
from textual.widgets import OptionList

from pult.app import PultApp
from pult.curriculum.material import Task, TaskMetadata, save_task
from pult.curriculum.sequence import load_sequence, save_sequence
from pult.screens.task_screen import TaskScreen
from pult.storage import load_toml, save_toml
from pult.widgets.document_viewer import DocumentViewer


def test_tasks_solutions_assignment_and_editor(tmp_path, monkeypatch):
    config = prepare_root(tmp_path)
    monkeypatch.setattr("pult.app.load_app_config", lambda: config)
    sequence = load_sequence(
        Path(__file__).parents[1] / "examples/unterricht",
        6,
        "mathematik",
        "formatbeispiel",
    )
    save_sequence(tmp_path, sequence)
    directory = tmp_path / "sequences/6/mathematik/formatbeispiel"
    extra = directory / "aufgaben/zusatz"
    save_task(
        directory,
        Task(
            "zusatz",
            "# Zusatz",
            metadata=TaskMetadata("Zusatzaufgabe", ["K1", "K6"], "II"),
        ),
    )

    async def run():
        app = PultApp()
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause()
            screen = TaskScreen(sequence, directory, lesson_id=sequence.lessons[0].id)
            await app.push_screen(screen)
            await pilot.pause()
            assert (
                screen.query_one("#task-list").border_subtitle
                == f"Für: {sequence.lessons[0].title}"
            )
            assert str(
                screen.query_one(OptionList).get_option(screen.task_id).prompt
            ).startswith("✓ ")
            assert not screen.query("SequenceContext")
            assert screen.query_one("#task-content").border_title == sequence.title
            assert (
                screen.query_one("#task-list").region.y
                == screen.query_one("#task-content").region.y
            )
            assert screen.query_one("#task-navigation").region.width == 40
            task = screen.selected_task
            assert screen.query_one(DocumentViewer).source == task.text
            await pilot.press("s")
            await pilot.pause()
            assert screen.query_one(DocumentViewer).source == task.solution
            picker = screen.query_one(OptionList)
            picker.highlighted = picker.get_option_index("zusatz")
            await pilot.pause()
            assert not screen.show_solution
            assert screen.query_one(DocumentViewer).source == "# Zusatz"
            assert str(picker.get_option("zusatz").prompt) == "Zusatzaufgabe"
            assert (
                screen.query_one("#task-content").border_subtitle
                == "Aufgabe · AFB II · K1, K6"
            )
            await pilot.press("v", "v")
            assert [t.id for t in screen.sequence.lessons[0].tasks] == [task.id]
            monkeypatch.setattr(app, "suspend", nullcontext)

            def editor(command, *, check):
                path = Path(command[-1])
                assert path == extra / "loesung.md"
                path.write_text("Neue Lösung")
                return SimpleNamespace(returncode=0)

            monkeypatch.setattr("pult.screens.task_screen.subprocess.run", editor)
            await pilot.press("e", "down", "enter")
            await pilot.pause()
            assert screen.selected_task.solution == "Neue Lösung"
            assert screen.query_one(DocumentViewer).source == "# Zusatz"
            await pilot.press("s")
            await pilot.pause()
            assert screen.query_one(DocumentViewer).source == "Neue Lösung"

            def metadata_editor(command, *, check):
                path = Path(command[-1])
                assert path == extra / "aufgabe.toml"
                save_toml(
                    path,
                    {
                        "titel": "Neuer Titel",
                        "kompetenzen": ["K2"],
                        "anforderungsbereich": "III",
                    },
                )
                return SimpleNamespace(returncode=0)

            monkeypatch.setattr(
                "pult.screens.task_screen.subprocess.run", metadata_editor
            )
            await pilot.press("e", "down", "down", "enter")
            await pilot.pause()
            assert screen.selected_task.metadata == TaskMetadata(
                "Neuer Titel", ["K2"], "III"
            )
            assert str(picker.get_option("zusatz").prompt) == "Neuer Titel"
            assert screen.query_one(DocumentViewer).source == "Neue Lösung"
            assert (
                screen.query_one("#task-content").border_subtitle
                == "Lösung · AFB III · K2"
            )

            # Invalid edits keep the selected task, documents and metadata available.
            before = screen.selected_task
            data = load_toml(extra / "aufgabe.toml")
            invalid = dict(data, anforderungsbereich=["I", "III"])
            save_toml(extra / "aufgabe.toml", invalid)
            await screen.reload_tasks()
            assert screen.selected_task is before
            assert screen.query_one(DocumentViewer).source == "Neue Lösung"
            save_toml(extra / "aufgabe.toml", data)
            await pilot.press("v")
            assert screen.sequence.lessons[0].tasks[-1].metadata == before.metadata

    asyncio.run(run())
