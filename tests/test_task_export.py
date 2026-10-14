import asyncio
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from pult.config import AppConfig
from pult.curriculum.material import (
    Task,
    TaskExport,
    TaskMetadata,
    load_task,
    save_task,
)
from pult.services.exports import material_export_path
from pult.services.task_export import (
    export_task_workbooks,
    workbook_furniture,
    workbook_html,
)
from pult.storage import save_toml


def exercise(options=None):
    return Task(
        "terme",
        "# Titel\n\nVereinfache.\n\n:::teilaufgaben spalten=2\na) $a(1+b)=$\n\nb) $(k+a^2)2=$\n:::\n",
        "# Lösung\n\n:::teilaufgaben\na) $a+ab$\n\nb) $2k+2a^2$\n:::\n",
        metadata=TaskMetadata("1. Terme", ["K5"], "I", options),
    )


@pytest.mark.parametrize(
    "data",
    [
        {},
        {"antwortbereich": "linien"},
        {"antwortbereich": "keiner"},
        {"antwortbereich": "kariert", "zeilen": 6, "pro_teilaufgabe": True},
    ],
)
def test_export_metadata_roundtrip(tmp_path, data):
    task = exercise(TaskExport.from_dict(data))
    save_task(tmp_path, task)
    assert load_task(tmp_path, task.id) == task


@pytest.mark.parametrize(
    "data",
    [
        [],
        "linien",
        {"antwortbereich": ["linien", "kariert"]},
        {"antwortbereich": "andere"},
        {"zeilen": True},
        {"zeilen": 1.5},
        {"zeilen": -1},
        {"zeilen": 41},
        {"zeilen": 0},
        {"antwortbereich": "keiner", "zeilen": 2},
        {"pro_teilaufgabe": "true"},
        {"pro_teilaufgabe": 1},
        {"unbekannt": 1},
    ],
)
def test_export_metadata_rejects_malformed_values_with_filename(tmp_path, data):
    # TOML cannot express every malformed structure; the parser validates them too.
    with pytest.raises(ValueError):
        TaskExport.from_dict(data)


def test_bad_export_metadata_load_reports_file(tmp_path):
    task = exercise()
    save_task(tmp_path, task)
    path = tmp_path / "aufgaben/terme/aufgabe.toml"
    data = task.metadata.to_dict()
    data["export"] = {"zeilen": "viel"}
    save_toml(path, data)
    with pytest.raises(ValueError, match="aufgabe.toml"):
        load_task(tmp_path, task.id)


@pytest.mark.parametrize(
    "area,per_subtask,expected",
    [
        ("kariert", False, 1),
        ("kariert", True, 2),
        ("linien", False, 1),
        ("linien", True, 2),
        ("keiner", True, 0),
    ],
)
def test_workbook_injects_only_requested_answer_fields(
    tmp_path, sequences, area, per_subtask, expected
):
    options = TaskExport(area, 0 if area == "keiner" else 3, per_subtask)
    document = workbook_html([exercise(options)], sequences[0], tmp_path)
    assert document.count('class="answer-area ') == expected
    assert 'data-columns="2"' in document
    assert "1. Aufgabe" in document
    assert "<h1>Titel</h1>" not in document
    body = document.split("</style>", 1)[1]
    assert "AFB" not in body and "K5" not in body
    solution = workbook_html(
        [exercise(options)], sequences[0], tmp_path, solutions=True
    )
    assert 'class="answer-area ' not in solution
    assert r"\(a+ab\)" in solution


def test_default_space_and_structured_subtasks_requirement(tmp_path, sequences):
    task = exercise()
    assert 'style="--rows:8"' in workbook_html([task], sequences[0], tmp_path)
    task.metadata.export = TaskExport("kariert", 4, True)
    task.text = "a) Rechne.\n\nb) Zeichne."
    with pytest.raises(ValueError, match=":::teilaufgaben"):
        workbook_html([task], sequences[0], tmp_path)


def test_images_are_embedded_and_paths_stay_inside_sequence(tmp_path, sequences):
    folder = tmp_path / "aufgaben/terme"
    folder.mkdir(parents=True)
    (folder / "figur.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg"/>')
    task = exercise(TaskExport("keiner", 0))
    task.text = ":::abbildung\nBestimme.\n\n![Figur](figur.svg)\n:::\n"
    result = workbook_html([task], sequences[0], tmp_path)
    assert 'class="illustrated"' in result
    assert "data:image/svg+xml;base64," in result
    task.text = "![Bild](https://example.org/figur.svg)"
    with pytest.raises(ValueError, match="relative Dateien"):
        workbook_html([task], sequences[0], tmp_path)
    task.text = "![Bild](../../../outside.svg)"
    with pytest.raises(ValueError, match="außerhalb"):
        workbook_html([task], sequences[0], tmp_path)


def test_header_and_footer_escape_user_text():
    header, footer = workbook_furniture("<Fach> & Thema", "<Name>", "source-sans-3")
    assert "&lt;Fach&gt; &amp; Thema" in header
    assert "&lt;Name&gt;" in footer
    assert "pageNumber" in footer


def test_material_export_paths_are_class_independent(tmp_path):
    assert (
        material_export_path(
            tmp_path, "2026-2027", 7, "mathematik", "terme", "aufgaben"
        )
        == tmp_path / "exports/2026-2027/materialien/mathematik/7/terme/aufgaben.pdf"
    )
    for subject, sequence, document in [
        ("../mathe", "terme", "aufgaben"),
        ("mathe", "../terme", "aufgaben"),
        ("mathe", "terme", "../out"),
    ]:
        with pytest.raises(ValueError):
            material_export_path(tmp_path, "2026-2027", 7, subject, sequence, document)


def setup_export(tmp_path, sequence):
    save_toml(
        tmp_path / "subjects.toml",
        {
            "subjects": [
                {
                    "id": sequence.subject_id,
                    "name": "Mathematik",
                    "short_name": "Ma",
                    "grade_levels": [sequence.grade_level],
                }
            ]
        },
    )
    for number in [10, 2, 1]:
        task = exercise()
        task.id = f"task-{number}"
        task.metadata.title = f"{number}. Aufgabe {number}"
        task.text = f"Inhalt {number}"
        save_task(tmp_path, task)
    return AppConfig(tmp_path, "true", "2026-2027")


def test_export_loads_all_tasks_in_library_order_and_renders_both_before_saving(
    tmp_path, sequences
):
    sequence = sequences[0]
    config = setup_export(tmp_path, sequence)
    renderer = SimpleNamespace(
        resolve_font=AsyncMock(return_value="source-sans-3"),
        render_pdf=AsyncMock(side_effect=[b"%PDF-tasks", b"%PDF-solutions"]),
    )
    targets = asyncio.run(
        export_task_workbooks(renderer, config, sequence=sequence, directory=tmp_path)
    )
    assert [p.read_bytes() for p in targets] == [b"%PDF-tasks", b"%PDF-solutions"]
    document = renderer.render_pdf.call_args_list[0].args[0]
    assert (
        document.index("Inhalt 1")
        < document.index("Inhalt 2")
        < document.index("Inhalt 10")
    )
    assert renderer.render_pdf.call_args.kwargs["math"] is True
    assert renderer.render_pdf.call_args.kwargs["margins"]["left"] == "25mm"
    renderer.render_pdf.side_effect = [
        b"%PDF-new",
        RuntimeError("failed second document"),
    ]
    with pytest.raises(RuntimeError):
        asyncio.run(
            export_task_workbooks(
                renderer, config, sequence=sequence, directory=tmp_path
            )
        )
    assert [p.read_bytes() for p in targets] == [b"%PDF-tasks", b"%PDF-solutions"]


def test_missing_solution_leaves_previous_exports_and_reports_task(tmp_path, sequences):
    config = setup_export(tmp_path, sequences[0])
    task = exercise()
    task.solution = None
    save_task(tmp_path, task)
    renderer = SimpleNamespace(
        resolve_font=AsyncMock(return_value="source-sans-3"), render_pdf=AsyncMock()
    )
    with pytest.raises(ValueError, match="1. Terme: loesung.md"):
        asyncio.run(
            export_task_workbooks(
                renderer, config, sequence=sequences[0], directory=tmp_path
            )
        )
    renderer.render_pdf.assert_not_awaited()
    assert not (tmp_path / "exports").exists()


@pytest.mark.skipif(
    not os.environ.get("PULT_TEST_BROWSER"),
    reason="Expliziter lokaler Browser-Test",
)
def test_browser_answer_fields_and_math_print_without_overflow(tmp_path, sequences):
    from dataclasses import replace

    from pult.services.document_rendering import DocumentRenderer
    from pult.services.task_export import ASSETS, MARGINS

    async def run():
        tasks = []
        for index, options in enumerate(
            [
                TaskExport("linien", 1, True),
                TaskExport("kariert", 6, True),
                TaskExport("linien", 2, False),
                TaskExport("kariert", 8, False),
                TaskExport("keiner", 0),
            ],
            1,
        ):
            task = exercise(options)
            task.id = f"task-{index}"
            tasks.append(task)
        renderer = DocumentRenderer(tmp_path / "cache")
        try:
            await renderer.ensure_browser()
            page = await renderer.browser.new_page()
            await page.route("**/*", lambda route: route.abort())
            await page.emulate_media(media="print")
            await page.set_content(workbook_html(tasks, sequences[0], tmp_path))
            await renderer._prepare_page(page, math=True)
            assert await page.evaluate((ASSETS / "layout.js").read_text()) is None
            layout = await page.evaluate("""() => ({
                grids: document.querySelectorAll('.answer-grid > svg path').length,
                lines: document.querySelectorAll('.answer-line').length,
                math: document.querySelectorAll('mjx-container svg').length,
                inline: [...document.querySelectorAll('.answer-inline-row')].map(row => {
                    const p = row.querySelector('p').getBoundingClientRect();
                    const line = row.querySelector('.answer-line').getBoundingClientRect();
                    return {start:line.x, end:p.right, width:line.width};
                }),
                rows: [...document.querySelectorAll('.subtask-row')].map(row => getComputedStyle(row).breakInside),
            })""")
            assert layout["grids"] == 3
            assert layout["lines"] == 4
            assert layout["math"] == 10
            assert all(
                line["start"] >= line["end"] and line["width"] >= 25 * 96 / 25.4 - 1
                for line in layout["inline"]
            )
            assert set(layout["rows"]) == {"avoid"}
            output = await page.pdf(format="A4", print_background=True, margin=MARGINS)
            assert output.startswith(b"%PDF-")
            (tmp_path / "answer-variants.pdf").write_bytes(output)
            await page.close()
            # Syntax errors must fail, never silently print a TeX error box.
            bad = replace(tasks[0], text=r"Bad $\notARealCommand{x}$")
            bad.metadata = TaskMetadata("bad", ["K5"], "I", TaskExport("keiner", 0))
            with pytest.raises(ValueError, match="Formel"):
                await renderer.render_pdf(
                    workbook_html([bad], sequences[0], tmp_path), math=True
                )
        finally:
            await renderer.close()

    asyncio.run(run())
