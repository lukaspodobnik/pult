import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from test_task_export import setup_export
from test_ui_integration import prepare_root
from textual.widgets import OptionList

from pult.app import PultApp
from pult.curriculum.material import (
    Task,
    TaskMetadata,
    TaskSource,
    load_task,
    load_tasks,
    save_task,
)
from pult.curriculum.sequence import save_sequence
from pult.screens.teaching.select_task_file_screen import SelectTaskFileScreen
from pult.screens.teaching.task_screen import TaskScreen
from pult.services.exports.task_export import export_task_workbooks
from pult.storage import load_toml


def book_task(task_id, page, number=None, label=None):
    source = TaskSource("buch", "fokus", page, number, label)
    reference = f"A. {number}" if number else label
    return Task(
        task_id,
        f"# S. {page} {reference}",
        "Lösung",
        metadata=TaskMetadata(
            f"Trainieren, S. {page} {reference}",
            ["K5"],
            "I",
            source=source,
        ),
    )


@pytest.mark.parametrize(
    "title",
    [
        "1. Trainieren, S. 32 A. 8",
        "Trainieren, A. 8",
        "S. 32 Umformen",
        "S. 31 A. 8",
        "S. 32 A. 9",
        "S. 320 A. 8",
        "S. 32 A. 80",
        "S. 32 A. 8a",
        "S. 32 A. 8 A. 8",
        "S. 32 S. 32 A. 8",
    ],
)
def test_book_titles_require_matching_single_reference(title):
    with pytest.raises(ValueError):
        TaskMetadata(title, ["K5"], "I", source=TaskSource("buch", "fokus", 32, "8"))


@pytest.mark.parametrize("number", ["0", "01", "1a", "IIII", "VX", "iv"])
def test_book_numbers_cannot_silently_sort_as_text(number):
    with pytest.raises(ValueError):
        TaskSource("buch", "fokus", 32, number)


def test_books_sort_by_numeric_page_number_and_keep_special_tasks(tmp_path):
    tasks = [
        book_task("p100", 100, "1"),
        book_task("a10", 32, "10"),
        book_task("ii", 32, "II"),
        book_task("a2", 32, "2"),
        book_task("intro", 32, label="Punktemuster"),
        book_task("i", 32, "I"),
        book_task("a1", 32, "1"),
        book_task("p9", 9, "12"),
    ]
    for task in tasks:
        save_task(tmp_path, task)
    result = load_tasks(tmp_path)
    assert [t.id for t in result] == [
        "p9",
        "intro",
        "a1",
        "a2",
        "a10",
        "i",
        "ii",
        "p100",
    ]
    picker = SelectTaskFileScreen(result)
    assert [str(option.prompt) for option in picker.task_options()] == [
        t.metadata.title for t in result
    ]


def renderer_mock():
    return SimpleNamespace(
        resolve_font=AsyncMock(return_value="source-sans-3"),
        render_pdf=AsyncMock(return_value=b"%PDF-test"),
    )


def test_sequence_export_uses_union_of_bookmarks_and_fresh_book_order(
    tmp_path, sequences
):
    sequence = sequences[0]
    config = setup_export(tmp_path, sequence)
    sequence.books = {"fokus": "Fokus Mathematik"}
    tasks = [
        book_task("task-10", 32, "10"),
        book_task("task-2", 32, "2"),
        book_task("task-1", 9, "1"),
    ]
    for task in tasks:
        save_task(tmp_path, task)
    # The same exercise appears in two lessons; metadata is read from disk.
    sequence.lessons[0].tasks = [tasks[0], tasks[1]]
    sequence.lessons[1].tasks = [tasks[1], tasks[2]]
    tasks[0].text = "Frisch bearbeitet"
    save_task(tmp_path, tasks[0])
    # Unassigned exercises neither need solutions nor a registered book.
    excluded = book_task("unassigned", 1, "1")
    excluded.metadata.source = TaskSource("buch", "anderes-buch", 1, "1")
    excluded.solution = None
    save_task(tmp_path, excluded)
    renderer = renderer_mock()
    asyncio.run(
        export_task_workbooks(renderer, config, sequence=sequence, directory=tmp_path)
    )
    for call in renderer.render_pdf.call_args_list:
        document = call.args[0]
        assert 'data-task="unassigned"' not in document
        assert document.count('data-task="task-2"') == 1
        assert (
            document.index('data-task="task-1"')
            < document.index('data-task="task-2"')
            < document.index('data-task="task-10"')
        )
    assert "Frisch bearbeitet" in renderer.render_pdf.call_args_list[0].args[0]


def test_lesson_export_keeps_bookmark_order_and_separate_paths(tmp_path, sequences):
    sequence = sequences[0]
    config = setup_export(tmp_path, sequence)
    lesson = sequence.lessons[0]
    lesson.tasks = [load_task(tmp_path, "task-10"), load_task(tmp_path, "task-1")]
    sequence.lessons[1].tasks = [load_task(tmp_path, "task-2")]
    renderer = renderer_mock()

    async def run():
        whole = await export_task_workbooks(
            renderer, config, sequence=sequence, directory=tmp_path
        )
        renderer.render_pdf.reset_mock()
        single = await export_task_workbooks(
            renderer, config, sequence=sequence, directory=tmp_path, lesson_id=lesson.id
        )
        assert not set(whole) & set(single)
        assert [p.name for p in whole] == ["aufgaben.pdf", "loesungen.pdf"]
        assert [p.name for p in single] == [
            f"{lesson.id}-aufgaben.pdf",
            f"{lesson.id}-loesungen.pdf",
        ]
        assert all(p.read_bytes() == b"%PDF-test" for p in (*whole, *single))

    asyncio.run(run())
    for call in renderer.render_pdf.call_args_list:
        document = call.args[0]
        assert 'data-task="task-2"' not in document
        assert document.index('data-task="task-10"') < document.index(
            'data-task="task-1"'
        )
        assert f"<h1>{lesson.title}" in document
        assert lesson.title in call.kwargs["header_template"]


@pytest.mark.parametrize("single_lesson", [False, True])
def test_empty_bookmarks_do_not_replace_previous_exports(
    tmp_path, sequences, single_lesson
):
    sequence = sequences[0]
    config = setup_export(tmp_path, sequence)
    lesson_id = sequence.lessons[0].id if single_lesson else None
    renderer = renderer_mock()
    targets = asyncio.run(
        export_task_workbooks(
            renderer, config, sequence=sequence, directory=tmp_path, lesson_id=lesson_id
        )
    )
    for lesson in sequence.lessons:
        lesson.tasks = []
    if single_lesson:
        # Even when another lesson has tasks, an empty lesson never exports them.
        sequence.lessons[1].tasks = [load_task(tmp_path, "task-1")]
    renderer.render_pdf.reset_mock()
    with pytest.raises(ValueError, match="keine Aufgaben vorgemerkt"):
        asyncio.run(
            export_task_workbooks(
                renderer,
                config,
                sequence=sequence,
                directory=tmp_path,
                lesson_id=lesson_id,
            )
        )
    renderer.render_pdf.assert_not_awaited()
    assert all(p.read_bytes() == b"%PDF-test" for p in targets)


def test_unknown_lesson_does_not_fall_back_to_sequence_export(tmp_path, sequences):
    config = setup_export(tmp_path, sequences[0])
    renderer = renderer_mock()
    with pytest.raises(ValueError, match="Stunde.*nicht gefunden"):
        asyncio.run(
            export_task_workbooks(
                renderer,
                config,
                sequence=sequences[0],
                directory=tmp_path,
                lesson_id="unknown",
            )
        )
    renderer.render_pdf.assert_not_awaited()


def test_removed_bookmarks_disappear_from_next_export(tmp_path, sequences):
    sequence = sequences[0]
    config = setup_export(tmp_path, sequence)
    renderer = renderer_mock()
    asyncio.run(
        export_task_workbooks(renderer, config, sequence=sequence, directory=tmp_path)
    )
    sequence.lessons[0].tasks = [load_task(tmp_path, "task-1")]
    renderer.render_pdf.reset_mock()
    asyncio.run(
        export_task_workbooks(renderer, config, sequence=sequence, directory=tmp_path)
    )
    for call in renderer.render_pdf.call_args_list:
        assert 'data-task="task-1"' in call.args[0]
        assert 'data-task="task-2"' not in call.args[0]
        assert 'data-task="task-10"' not in call.args[0]


def test_hotkeys_use_lesson_context_and_keep_rows_compact(
    tmp_path, monkeypatch, sequences
):
    config = prepare_root(tmp_path)
    monkeypatch.setattr("pult.app.load_app_config", lambda: config)
    sequence = sequences[0]
    save_sequence(tmp_path, sequence)
    directory = (
        tmp_path
        / f"sequences/{sequence.grade_level}/{sequence.subject_id}/{sequence.id}"
    )
    lesson = sequence.lessons[0]
    task = lesson.tasks[0]
    exporter = AsyncMock(
        return_value=(tmp_path / "aufgaben.pdf", tmp_path / "loesungen.pdf")
    )
    monkeypatch.setattr(
        "pult.screens.teaching.task_screen.export_task_workbooks", exporter
    )

    async def run():
        app = PultApp()
        async with app.run_test(size=(160, 46)) as pilot:
            await pilot.pause()
            screen = TaskScreen(sequence, directory, lesson_id=lesson.id)
            await app.push_screen(screen)
            await pilot.pause()
            assert all("\n" not in str(option.prompt) for option in screen.options())
            assert (
                str(screen.query_one(OptionList).get_option(task.id).prompt)
                == f"✓ {task.metadata.title}"
            )
            await pilot.press("x")
            await app.workers.wait_for_complete()
            assert exporter.call_args.kwargs["lesson_id"] == lesson.id
            await pilot.press("X")
            await app.workers.wait_for_complete()
            assert exporter.call_args.kwargs["lesson_id"] is None
            await pilot.press("v")
            assert lesson.tasks == []
            assert (
                str(screen.query_one(OptionList).get_option(task.id).prompt)
                == task.metadata.title
            )
            assert (
                load_toml(directory / f"stunden/{lesson.id}/stunde.toml")["aufgaben"]
                == []
            )
            assert "ausgewaehlt" not in load_toml(
                directory / f"aufgaben/{task.id}/aufgabe.toml"
            )
            await pilot.press("escape")
            library = TaskScreen(sequence, directory)
            await app.push_screen(library)
            await pilot.pause()
            assert not library.check_action("export_pdf", ())
            assert library.check_action("export_sequence_pdf", ())
            exporter.reset_mock()
            await pilot.press("x")
            await pilot.pause()
            exporter.assert_not_awaited()
            await pilot.press("X")
            await app.workers.wait_for_complete()
            exporter.assert_awaited_once()
            assert exporter.call_args.kwargs["lesson_id"] is None

    asyncio.run(run())
