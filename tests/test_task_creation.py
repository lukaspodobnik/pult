import asyncio
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_ui_integration import prepare_root
from textual.widgets import Input, OptionList, Select

from pult.app import PultApp
from pult.curriculum.material import TaskMetadata, load_task
from pult.curriculum.sequence import load_sequence, save_sequence
from pult.screens.create_task_screen import CreateTaskScreen
from pult.screens.task_screen import TaskScreen
from pult.services.task_creation import create_task_files
from pult.widgets.document_viewer import DocumentViewer


def test_create_task_files_preserves_existing_tasks(tmp_path):
    metadata = TaskMetadata("Brüche vergleichen", ["K1", "K4"], "II")
    task_id, paths = create_task_files(tmp_path, metadata)
    assert task_id == "brueche-vergleichen"
    assert paths[0].read_text() == "# Brüche vergleichen\n\n"
    assert paths[1].read_text() == ""
    assert paths[2].name == "aufgabe.toml"
    assert load_task(tmp_path, task_id).metadata == metadata
    paths[1].write_text("Bestehende Lösung")
    second_id, _ = create_task_files(tmp_path, metadata)
    assert second_id == "brueche-vergleichen-2"
    assert paths[1].read_text() == "Bestehende Lösung"
    metadata.title = "   "
    with pytest.raises(ValueError):
        create_task_files(tmp_path, metadata)
    assert len(list((tmp_path / "aufgaben").iterdir())) == 2


def test_create_task_cleans_up_after_partial_write(tmp_path, monkeypatch):
    def fail(path, source):
        raise OSError("Schreibfehler")

    monkeypatch.setattr("pult.curriculum.material.save_markdown", fail)
    with pytest.raises(OSError, match="Schreibfehler"):
        create_task_files(tmp_path, TaskMetadata("Neue Aufgabe", ["K5"], "I"))
    assert list((tmp_path / "aufgaben").iterdir()) == []


def test_create_task_opens_all_files_and_renders_one_entry(tmp_path, monkeypatch):
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
    calls = []

    def editor(command, *, check):
        files = [Path(value) for value in command[-3:]]
        assert [file.name for file in files] == [
            "aufgabe.md",
            "loesung.md",
            "aufgabe.toml",
        ]
        assert all(file.exists() for file in files)
        assert len({file.parent for file in files}) == 1
        files[0].write_text("# Brüche vergleichen\n\nVergleiche die Brüche.")
        files[1].write_text("Ein Halb ist größer.")
        calls.append(files)
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr("pult.screens.task_screen.subprocess.run", editor)

    async def run():
        app = PultApp()
        async with app.run_test(size=(180, 52)) as pilot:
            await pilot.pause()
            monkeypatch.setattr(app, "suspend", nullcontext)
            screen = TaskScreen(sequence, directory)
            await app.push_screen(screen)
            await pilot.pause()
            count = screen.query_one(OptionList).option_count
            await pilot.press("n", "escape")
            assert not calls
            assert screen.query_one(OptionList).option_count == count
            await pilot.press("n")
            app.screen.query_one("#new-task-title", Input).value = "Brüche vergleichen"
            await pilot.press("enter")
            assert isinstance(app.screen, CreateTaskScreen)
            assert not calls
            app.screen.query_one(Select).value = "II"
            await pilot.press("enter")
            assert isinstance(app.screen, CreateTaskScreen)
            assert not calls
            app.screen.query_one("#new-task-competencies", Input).value = "K1, K4"
            await pilot.press("enter")
            await pilot.pause()
            assert app.screen is screen
            assert len(calls) == 1
            assert screen.task_id == "brueche-vergleichen"
            assert screen.selected_task.metadata == TaskMetadata(
                "Brüche vergleichen", ["K1", "K4"], "II"
            )
            picker = screen.query_one(OptionList)
            assert picker.option_count == count + 1
            assert str(picker.get_option(screen.task_id).prompt).startswith(
                "Brüche vergleichen"
            )
            assert picker.get_option_at_index(picker.highlighted).id == screen.task_id
            material = list(screen.query(DocumentViewer))
            assert len(material) == 1
            assert material[0].source.endswith("Vergleiche die Brüche.")
            await pilot.press("s")
            await pilot.pause()
            assert screen.query_one(DocumentViewer).source == "Ein Halb ist größer."
            assert screen.query_one("#task-content").border_title == sequence.title
            assert not any(
                task.id == screen.task_id
                for lesson in screen.sequence.lessons
                for task in lesson.tasks
            )
            assert screen.query_one("PultFooter").region.bottom == 52

            previous_task = screen.selected_task

            def invalid_editor(command, *, check):
                Path(command[-1]).write_text('titel = "Unvollständig"')
                return SimpleNamespace(returncode=0)

            monkeypatch.setattr(
                "pult.screens.task_screen.subprocess.run", invalid_editor
            )
            await screen.create_task(TaskMetadata("Weitere Aufgabe", ["K5"], "I"))
            assert screen.selected_task is previous_task
            assert picker.get_option_at_index(picker.highlighted).id == previous_task.id
            assert screen.query_one(DocumentViewer).source == "Ein Halb ist größer."

    asyncio.run(run())
