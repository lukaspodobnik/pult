import asyncio
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace

from test_ui_integration import prepare_root
from textual.widgets import OptionList

from pult.app import PultApp
from pult.curriculum.sequence import load_sequence, save_sequence
from pult.screens.sequence_library_screen import SequenceLibraryScreen
from pult.screens.task_screen import TaskScreen
from pult.widgets.lesson_material import LessonMaterial
from pult.widgets.sequence_preview import SequencePreview
from pult.widgets.sequence_tree import SequenceTree


def test_task_inventory_edit_and_return(tmp_path, monkeypatch):
    config = prepare_root(tmp_path)
    monkeypatch.setattr("pult.app.load_app_config", lambda: config)
    sequence = load_sequence(Path(__file__).parents[1] / "examples/unterricht",
                             6, "mathematik", "formatbeispiel")
    save_sequence(tmp_path, sequence)
    directory = tmp_path / "sequences/6/mathematik/formatbeispiel"
    extra = directory / "aufgaben/zusatz"
    extra.mkdir()
    (extra / "aufgabe.md").write_text("Private Zusatzaufgabe")

    async def run():
        app = PultApp()
        async with app.run_test(size=(180, 52)) as pilot:
            await pilot.pause(.5)
            library = SequenceLibraryScreen()
            await app.push_screen(library)
            await pilot.pause()
            preview = library.query_one(SequencePreview)
            preview.show_sequence(sequence)
            preview.focus()
            original = preview.selected_lesson.id
            await pilot.press("a")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, TaskScreen)
            picker = screen.query_one(OptionList)
            assert picker.option_count == 2
            assert "Noch nicht zugeordnet" in str(picker.get_option("zusatz").prompt)
            await pilot.press("down")
            await pilot.pause()
            assert screen.task_id == "zusatz"
            assert screen.query_one(LessonMaterial).source == "Private Zusatzaufgabe"
            assert screen.query_one("#task-content").region.x > picker.region.x
            assert len(screen.focus_chain) == 2
            await pilot.press("tab")
            assert app.focused.id == "task-content"
            monkeypatch.setattr(app, "suspend", nullcontext)

            def editor(command, *, check):
                path = Path(command[-1])
                assert path == extra / "loesung.md"
                assert path.exists()
                path.write_text("Neue Lösung")
                return SimpleNamespace(returncode=0)

            monkeypatch.setattr("pult.screens.task_screen.subprocess", SimpleNamespace(run=editor))
            await pilot.press("e", "down", "enter")
            await pilot.pause()
            assert app.screen is screen
            assert screen.task_id == "zusatz"
            assert screen.selected_task.solution == "Neue Lösung"
            assert any(m.source == "Neue Lösung" for m in screen.query(LessonMaterial))
            app.save_screenshot("tasks.svg", path=str(tmp_path))
            await pilot.press("escape")
            await pilot.pause()
            assert app.screen is library
            assert app.focused is preview
            assert preview.selected_lesson.id == original
            # Der identische Zugang funktioniert auch aus dem Sequenzbaum.
            tree = library.query_one(SequenceTree)
            def find(node):
                if node.data and node.data.id == sequence.id:
                    return node
                for child in node.children:
                    result = find(child)
                    if result:
                        return result
            node = find(tree.root)
            assert node is not None
            parent = node.parent
            while parent is not None:
                parent.expand()
                parent = parent.parent
            await pilot.pause()
            tree.move_cursor(node)
            await pilot.pause()
            tree.focus()
            await pilot.press("a")
            await pilot.pause()
            assert isinstance(app.screen, TaskScreen)
            await pilot.press("escape")
            assert app.focused is tree

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(run())
    finally:
        loop.close()
