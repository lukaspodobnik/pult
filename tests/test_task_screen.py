import asyncio
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

from test_ui_integration import prepare_root
from textual.widgets import OptionList

from pult.app import PultApp
from pult.curriculum.material import Task, TaskMetadata, save_task
from pult.curriculum.sequence import load_sequence, save_sequence
from pult.screens.teaching.task_screen import TaskScreen
from pult.storage import load_toml, save_toml
from pult.widgets.document_viewer import DocumentViewer


def test_tasks_sort_by_title_number_and_preserve_assignment(tmp_path, sequences):
    tasks = [
        Task(task_id, "Aufgabe", metadata=TaskMetadata(title, ["K5"], "I"))
        for task_id, title in [
            ("a", "10. Produkte"),
            ("b", "2. Vergleichen"),
            ("c", "1. Umformen"),
            ("d", "Zusatz"),
            ("e", "alpha"),
            ("f", "2. Anwenden"),
            ("g", "2. Anwenden"),
        ]
    ]
    for task in tasks:
        save_task(tmp_path, task)
    sequence = sequences[0]
    lesson = sequence.lessons[0]
    lesson.tasks = [tasks[0]]
    screen = TaskScreen(sequence, tmp_path, lesson_id=lesson.id)
    assert [task.id for task in screen.tasks] == ["c", "f", "g", "b", "a", "e", "d"]
    assert screen.task_id == "a"
    assert [task.id for task in lesson.tasks] == ["a"]


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
        async with app.run_test(size=(160, 46)) as pilot:
            await pilot.pause()
            screen = TaskScreen(sequence, directory, lesson_id=sequence.lessons[0].id)
            await app.push_screen(screen)
            await pilot.pause()
            task = screen.selected_task
            assert screen.query_one(DocumentViewer).source == task.text
            screen.query_one("#task-content").focus()
            await pilot.press("space")
            await pilot.pause()
            assert screen.query_one(DocumentViewer).source == task.solution
            await pilot.press("space")
            assert screen.query_one(DocumentViewer).source == task.text
            picker = screen.query_one(OptionList)
            picker.focus()
            picker.highlighted = picker.get_option_index("zusatz")
            await pilot.pause()
            assert not screen.show_solution
            assert screen.query_one(DocumentViewer).source == "# Zusatz"
            assert str(picker.get_option("zusatz").prompt) == "Zusatzaufgabe"
            assert (
                screen.query_one("#task-content").border_subtitle
                == "Aufgabe · AFB II · K1, K6"
            )
            await pilot.press("v")
            assigned = load_toml(
                directory / "stunden" / sequence.lessons[0].id / "stunde.toml"
            )["aufgaben"]
            assert assigned == [task.id, "zusatz"]
            monkeypatch.setattr(app, "suspend", nullcontext)

            def metadata_editor(command, *, check):
                path = Path(command[-1])
                assert path == extra / "aufgabe.toml"
                save_toml(
                    path,
                    {
                        "titel": "1. Neuer Titel",
                        "kompetenzen": ["K2"],
                        "anforderungsbereich": "III",
                    },
                )
                return SimpleNamespace(returncode=0)

            monkeypatch.setattr(
                "pult.screens.teaching.task_screen.subprocess.run", metadata_editor
            )
            await pilot.press("e", "down", "down", "enter")
            await pilot.pause()
            assert screen.selected_task.metadata == TaskMetadata(
                "1. Neuer Titel", ["K2"], "III"
            )
            assert str(picker.get_option("zusatz").prompt).endswith("1. Neuer Titel")
            assert screen.query_one(DocumentViewer).source == "# Zusatz"
            assert (
                screen.query_one("#task-content").border_subtitle
                == "Aufgabe · AFB III · K2"
            )

            # Invalid edits keep the selected task, documents and metadata available.
            before = screen.selected_task
            data = load_toml(extra / "aufgabe.toml")
            invalid = dict(data, anforderungsbereich=["I", "III"])
            save_toml(extra / "aufgabe.toml", invalid)
            await screen.reload_tasks()
            assert screen.selected_task == before
            assert screen.query_one(DocumentViewer).source == "# Zusatz"
            save_toml(extra / "aufgabe.toml", data)
            await screen.reload_tasks()
            assigned = next(
                t for t in screen.sequence.lessons[0].tasks if t.id == "zusatz"
            )
            assert assigned.metadata == before.metadata
            await pilot.press("v")
            assert load_toml(
                directory / "stunden" / sequence.lessons[0].id / "stunde.toml"
            )["aufgaben"] == [task.id]

    asyncio.run(run())


def test_sequence_export_hotkey_is_guarded_and_recovers_after_failure(
    tmp_path, monkeypatch
):
    from unittest.mock import AsyncMock

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

    async def run():
        app = PultApp()
        started, release = asyncio.Event(), asyncio.Event()

        async def exporter(*args, **kwargs):
            started.set()
            await release.wait()
            raise ValueError("Lösung fehlt")

        mock = AsyncMock(side_effect=exporter)
        monkeypatch.setattr(
            "pult.screens.teaching.task_screen.export_task_workbooks", mock
        )
        async with app.run_test(size=(160, 46)) as pilot:
            await pilot.pause()
            screen = TaskScreen(sequence, directory)
            await app.push_screen(screen)
            await pilot.pause()
            await pilot.press("x")
            await asyncio.wait_for(started.wait(), 2)
            assert screen._exporting
            await pilot.press("x")
            assert mock.await_count == 1
            release.set()
            await pilot.pause()
            assert screen.check_action("export_pdf", ())
            assert mock.call_args.kwargs["sequence"] == sequence
            screen.tasks = []
            assert not screen.check_action("export_pdf", ())

    asyncio.run(run())
