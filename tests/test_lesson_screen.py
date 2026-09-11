import asyncio
from contextlib import nullcontext
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from test_ui_integration import prepare_root
from textual.widgets import OptionList

from pult.app import PultApp
from pult.curriculum.sequence import load_sequence, save_sequence
from pult.screens.lesson_screen import LessonScreen
from pult.screens.sequence_library_screen import SequenceLibraryScreen
from pult.storage import load_toml, save_toml
from pult.widgets.lesson_material import LessonMaterial
from pult.widgets.sequence_preview import SequencePreview


def test_viewer_opens_selected_lesson_and_edits_then_returns(tmp_path, monkeypatch):
    config = prepare_root(tmp_path)
    monkeypatch.setattr("pult.app.load_app_config", lambda: config)
    sequence = load_sequence(
        Path(__file__).parents[1] / "examples/unterricht",
        6,
        "mathematik",
        "formatbeispiel",
    )
    sequence.lessons.append(
        replace(
            sequence.lessons[0], id="zweite", title="Zweite Stunde", preparation=None
        )
    )
    save_sequence(tmp_path, sequence)
    calls = []

    async def run():
        app = PultApp()
        async with app.run_test(size=(180, 52)) as pilot:
            await pilot.pause(0.5)
            await app.push_screen(SequenceLibraryScreen())
            await pilot.pause()
            library = app.screen
            preview = library.query_one(SequencePreview)
            preview.show_sequence(sequence)
            preview.focus()
            await pilot.pause()
            await pilot.press("down")
            assert preview.selected_lesson.id == "zweite"
            await pilot.press("enter")
            await pilot.pause()
            assert isinstance(app.screen, LessonScreen)
            viewer = app.screen
            await app.workers.wait_for_complete()
            assert viewer.lesson.id == "zweite"
            assert viewer.focus_chain == [viewer.query_one("#lesson-list")]
            await pilot.press("tab")
            assert app.focused is viewer.query_one("#lesson-list")
            assert viewer.query_one("#lesson-preparation").display
            assert not viewer.query_one("#lesson-tasks").display
            assert viewer.query_one("#lesson-goals").region.height == 14
            assert viewer.query_one("#lesson-orientation").region.width == 44
            assert viewer.query_one("#lesson-workspace").region.y == 1
            # Material wird auch ohne Vorbereitungsdatei angezeigt.
            assert any(
                "Benötigtes Material" in m.source
                for m in viewer.query("#lesson-preparation LessonMaterial")
            )
            await pilot.press("space")
            await app.workers.wait_for_complete()
            assert viewer.query_one("#lesson-tasks").display
            children = list(viewer.query_one("#lesson-tasks").children)
            assert children[0].has_class("lesson-task-divider")
            assert isinstance(children[1], LessonMaterial)
            assert children[2].has_class("lesson-solution-title")
            assert isinstance(children[3], LessonMaterial)
            await pilot.press("space")
            monkeypatch.setattr(app, "suspend", nullcontext)
            notice = Mock()
            monkeypatch.setattr(viewer, "notify", notice)

            def editor(command, *, check):
                path = Path(command[-1])
                calls.append(path)
                if path.name == "vorbereitung.md":
                    assert path.exists()
                    path.write_text("# Aus dem Editor\n\n```python\nprint(42)\n```\n")
                else:
                    data = load_toml(path)
                    data["titel"] = "Geänderter Titel"
                    data["material"] = ["Lineal"]
                    save_toml(path, data)
                return SimpleNamespace(returncode=0)

            monkeypatch.setattr(
                "pult.screens.lesson_screen.subprocess", SimpleNamespace(run=editor)
            )
            await pilot.press("e")
            await pilot.pause()
            await app.workers.wait_for_complete()
            assert viewer.lesson.preparation.startswith("# Aus dem Editor")
            assert "Benötigtes Material" not in calls[0].read_text()
            assert viewer.query("MarkdownFence")
            await pilot.press("m")
            await pilot.pause()
            assert viewer.lesson.title == "Geänderter Titel"
            assert viewer.lesson.material == ["Lineal"]
            assert (
                viewer.query_one("#lesson-preparation").border_title
                == "Geänderter Titel"
            )
            assert app.require_sequence_library()._sequences is None

            # Fehlerhafte Bearbeitung überschreibt nicht den letzten gültigen Stand.
            def invalid(command, *, check):
                Path(command[-1]).write_text("titel = [")
                return SimpleNamespace(returncode=0)

            monkeypatch.setattr(
                "pult.screens.lesson_screen.subprocess", SimpleNamespace(run=invalid)
            )
            await pilot.press("m")
            await pilot.pause()
            assert viewer.lesson.title == "Geänderter Titel"
            assert notice.call_args.kwargs["severity"] == "error"
            save_sequence(tmp_path, viewer.sequence)
            await pilot.press("escape")
            await pilot.pause()
            assert app.screen is library
            assert app.focused is preview
            assert preview.selected_lesson.id == "zweite"
            assert preview.selected_lesson.title == "Geänderter Titel"
            await pilot.press("enter")
            await pilot.pause()
            viewer = app.screen
            listing = viewer.query_one("#lesson-list", OptionList)
            listing.focus()
            await pilot.press("up")
            await pilot.pause()
            await app.workers.wait_for_complete()
            assert viewer.lesson.id == "anteile"
            assert viewer.query_one("#lesson-preparation").display
            app.save_screenshot("lesson-viewer.svg", path=tmp_path)
            await pilot.press("escape", "escape")

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(run())
    finally:
        loop.close()


def test_graphics_and_inline_math_survive_material_switch(tmp_path, monkeypatch):
    import shutil

    import pytest

    if not shutil.which("node") or not shutil.which("rsvg-convert"):
        pytest.skip("Lokaler Grafikrenderer nicht installiert")
    from pult.services import material_rendering
    from pult.widgets.sixel_image import StableSixelImage

    config = prepare_root(tmp_path)
    monkeypatch.setattr("pult.app.load_app_config", lambda: config)
    monkeypatch.setattr(material_rendering, "_image_widget", StableSixelImage)
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    example_root = Path(__file__).parents[1] / "examples/unterricht"
    sequence = load_sequence(example_root, 6, "mathematik", "formatbeispiel")
    sequence.lessons[0].tasks[0].text = "a) $\\frac{1}{2}$ und b) $\\frac{2}{3}$"
    save_sequence(tmp_path, sequence)
    shutil.copytree(
        example_root / "sequences/6/mathematik/formatbeispiel/dateien",
        tmp_path / "sequences/6/mathematik/formatbeispiel/dateien",
    )

    async def run():
        app = PultApp()
        async with app.run_test(size=(180, 52)) as pilot:
            await pilot.pause(0.5)
            await app.push_screen(LessonScreen(sequence, "anteile"))
            await pilot.pause()
            await app.workers.wait_for_complete()
            await pilot.pause()
            assert app.screen.query("#lesson-preparation .formula")
            assert app.screen.query("#lesson-preparation .figure")
            await pilot.press("space")
            await pilot.pause()
            await app.workers.wait_for_complete()
            flows = app.screen.query(".lesson-inline-flow")
            assert flows and all(flow.children for flow in flows)
            assert app.screen.query(".lesson-inline-text")
            await pilot.press("space", "space")
            await pilot.pause()
            assert all(flow.children for flow in flows)
            await pilot.press("escape")

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(run())
    finally:
        loop.close()


def test_edit_task_text_and_missing_solution(tmp_path, monkeypatch):
    from pult.screens.select_task_file_screen import SelectTaskFileScreen

    config = prepare_root(tmp_path)
    monkeypatch.setattr("pult.app.load_app_config", lambda: config)
    sequence = load_sequence(
        Path(__file__).parents[1] / "examples/unterricht",
        6,
        "mathematik",
        "formatbeispiel",
    )
    sequence.lessons[0].tasks[0].solution = None
    sequence.lessons.append(replace(sequence.lessons[0], id="zweite"))
    save_sequence(tmp_path, sequence)
    calls = []

    async def run():
        app = PultApp()
        async with app.run_test(size=(180, 52)) as pilot:
            await pilot.pause(0.5)
            viewer = LessonScreen(sequence, sequence.lessons[0].id)
            await app.push_screen(viewer)
            await pilot.pause()
            monkeypatch.setattr(app, "suspend", nullcontext)

            def editor(command, *, check):
                path = Path(command[-1])
                calls.append(path)
                assert path.exists()
                path.write_text("Neu: " + path.name)
                return SimpleNamespace(returncode=0)

            monkeypatch.setattr(
                "pult.screens.lesson_screen.subprocess", SimpleNamespace(run=editor)
            )
            await pilot.press("space", "e")
            assert isinstance(app.screen, SelectTaskFileScreen)
            await pilot.press("enter", "escape", "escape")
            assert app.screen is viewer
            assert not calls
            solution = (
                viewer.directory / "aufgaben" / viewer.lesson.tasks[0].id / "loesung.md"
            )
            assert not solution.exists()
            await pilot.press("e", "enter", "enter")
            await pilot.pause()
            assert app.screen is viewer
            assert calls[-1].name == "aufgabe.md"
            assert viewer.lesson.tasks[0].text == "Neu: aufgabe.md"
            assert viewer.sequence.lessons[1].tasks[0].text == "Neu: aufgabe.md"
            assert viewer.show_tasks
            await pilot.press("e", "enter", "down", "enter")
            await pilot.pause()
            await app.workers.wait_for_complete()
            assert app.screen is viewer
            assert calls[-1] == solution
            assert viewer.lesson.tasks[0].solution == "Neu: loesung.md"
            assert any(
                m.source == "Neu: loesung.md" for m in viewer.query(LessonMaterial)
            )
            await pilot.press("escape")

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(run())
    finally:
        loop.close()
