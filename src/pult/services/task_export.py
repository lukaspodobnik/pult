"""Aufgaben und Lösungen einer Sequenz als gemeinsam gestaltete Arbeitshefte."""

from html import escape
from pathlib import Path

from markdown_it.token import Token
from playwright.async_api import PdfMargins

from pult.config import AppConfig
from pult.curriculum.material import Task, TaskExport, load_tasks, material_path
from pult.curriculum.sequence import Sequence
from pult.school.subject import load_subjects
from pult.services.document_figures import FIGURE_STYLES
from pult.services.document_fonts import document_font_stylesheet
from pult.services.document_rendering import (
    DocumentRenderer,
    markdown_html,
    syntax_stylesheet,
)
from pult.services.document_subtasks import SUBTASK_STYLES
from pult.services.exports import material_export_path, save_pdf

ASSETS = Path(__file__).parents[1] / "assets/workbook"
MARGINS: PdfMargins = {"top": "24mm", "bottom": "22mm", "left": "25mm", "right": "18mm"}


def answer_html(options: TaskExport) -> str:
    if options.answer_area == "keiner":
        return ""
    if options.answer_area == "kariert":
        return (
            f'<div class="answer-area answer-grid" style="--rows:{options.rows}"></div>'
        )
    return (
        '<div class="answer-area answer-lines">'
        + ('<span class="answer-line"></span>' * options.rows)
        + "</div>"
    )


def task_tokens(tokens: list[Token], options: TaskExport | None) -> list[Token]:
    # The workbook supplies its own numbered task heading, also for solutions.
    if tokens and tokens[0].type == "heading_open" and tokens[0].tag == "h1":
        tokens = tokens[3:]
    if options is None or options.answer_area == "keiner":
        return tokens
    area = answer_html(options)
    if not options.per_subtask:
        return [*tokens, Token("html_block", "", 0, content=area, block=True)]
    if not any(token.type == "subtask_content_close" for token in tokens):
        raise ValueError(
            "pro_teilaufgabe = true benötigt einen :::teilaufgaben-Block. "
            "Für eine Aufgabe ohne Teilaufgaben false verwenden."
        )
    result = []
    for token in tokens:
        if token.type == "subtask_content_close":
            result.append(Token("html_block", "", 0, content=area, block=True))
        result.append(token)
    return result


def workbook_html(
    tasks: list[Task],
    sequence: Sequence,
    directory: Path,
    *,
    solutions: bool = False,
    font: str = "source-sans-3",
) -> str:
    bodies = []
    for number, task in enumerate(tasks, 1):
        source = task.solution if solutions else task.text
        filename = "loesung.md" if solutions else "aufgabe.md"
        if not source or not source.strip():
            raise ValueError(f"{task.metadata.title}: {filename} fehlt oder ist leer.")
        options = None if solutions else task.metadata.export or TaskExport()
        try:
            body = markdown_html(
                source,
                material_path(directory, "aufgaben", task.id, filename),
                directory,
                transform=lambda tokens: task_tokens(tokens, options),
            )
        except (OSError, ValueError) as error:
            raise ValueError(f"{task.metadata.title}: {error}") from error
        bodies.append(
            f'<section class="exercise" data-task="{escape(task.id, quote=True)}">'
            f'<h2 class="exercise-heading">{number}. Aufgabe</h2>'
            f'<div class="exercise-body">{body}</div></section>'
        )
    title = sequence.title + (" · Lösungen" if solutions else "")
    return (
        '<!doctype html><html lang="de"><head><meta charset="utf-8">'
        f"<title>{escape(title)}</title><style>"
        + document_font_stylesheet(font)
        + syntax_stylesheet("#ffffff")
        + SUBTASK_STYLES
        + FIGURE_STYLES
        + (ASSETS / "print.css").read_text(encoding="utf-8")
        + "</style></head><body><article><h1>"
        + escape(title)
        + "</h1>"
        + "".join(bodies)
        + "</article></body></html>"
    )


def workbook_furniture(context: str, author: str, font: str) -> tuple[str, str]:
    family = (
        "'Avenir Next',sans-serif"
        if font == "avenir-next"
        else "'Pult Source Sans',sans-serif"
    )
    css = document_font_stylesheet(font)
    common = (
        f"font-family:{family};font-size:8.5pt;font-weight:400;color:#647282;"
        "box-sizing:border-box;width:100%;padding-left:25mm;padding-right:18mm;"
    )
    header = f'<style>{css}</style><div style="{common}text-align:right;padding-top:4mm">{escape(context)}</div>'
    footer = (
        f'<style>{css}</style><div style="{common}display:flex;justify-content:space-between;padding-bottom:10.5mm">'
        f'<span>{escape(author)}</span><span><span class="pageNumber"></span> / '
        '<span class="totalPages"></span></span></div>'
    )
    return header, footer


async def export_task_workbooks(
    renderer: DocumentRenderer,
    config: AppConfig,
    *,
    sequence: Sequence,
    directory: Path,
) -> tuple[Path, Path]:
    # Re-read edited files; export every task, including unassigned ones, once.
    tasks = load_tasks(directory)
    if not tasks:
        raise ValueError("Diese Sequenz enthält noch keine Aufgaben.")
    subject = next(
        (s for s in load_subjects(config.root) if s.id == sequence.subject_id), None
    )
    if subject is None:
        raise ValueError("Das Fach der Sequenz wurde nicht gefunden.")
    targets = tuple(
        material_export_path(
            config.root,
            config.active_school_year,
            sequence.grade_level,
            sequence.subject_id,
            sequence.id,
            name,
        )
        for name in ("aufgaben", "loesungen")
    )
    font = await renderer.resolve_font(config.document_font)
    documents = [
        workbook_html(tasks, sequence, directory, solutions=solutions, font=font)
        for solutions in (False, True)
    ]
    header, footer = workbook_furniture(
        f"{subject.name} {sequence.grade_level} · {sequence.title}",
        config.export_author,
        font,
    )
    contents = []
    for document in documents:
        contents.append(
            await renderer.render_pdf(
                document,
                font=font,
                math=True,
                margins=MARGINS,
                header_template=header,
                footer_template=footer,
                prepare_script=(ASSETS / "layout.js").read_text(encoding="utf-8"),
            )
        )
    # Both documents must render before either previous export is replaced.
    if any(not content.startswith(b"%PDF-") for content in contents):
        raise ValueError("Der Renderer hat keine PDF-Datei erzeugt.")
    for target, content in zip(targets, contents, strict=True):
        save_pdf(target, content)
    return targets[0], targets[1]
