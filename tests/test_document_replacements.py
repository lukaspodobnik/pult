import asyncio
from html import unescape
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from rich.console import Console
from rich.markdown import Markdown as RichMarkdown
from test_document_cache import mock_browser
from test_task_export import setup_export
from test_ui_integration import prepare_root
from textual.app import App

from pult.config import AppConfig, load_app_config, save_app_config
from pult.curriculum.material import Lesson, Phase, Task, TaskMetadata, save_task
from pult.services.documents.document_callouts import text_document_parser
from pult.services.documents.document_rendering import (
    DocumentRenderer,
    document_html,
    parser,
)
from pult.services.documents.document_replacements import (
    DEFAULT_REPLACEMENTS,
    validate_document_replacements,
)
from pult.services.exports.task_export import export_task_workbooks
from pult.services.settings import update_settings
from pult.widgets.document_viewer import DocumentViewer


@pytest.mark.parametrize("factory", [parser, text_document_parser])
def test_arrows_in_headings_lists_tables_and_callouts(factory):
    output = factory().render(
        "# A -> B\n\n- C <- D\n\n| Richtung |\n| --- |\n| E <-> F |\n\n"
        "> [!merksatz] G -> H\n> **I <- J**"
    )
    for text in ["A → B", "C ← D", "E ↔ F", "G → H", "I ← J"]:
        assert text in output
    assert "<h1>" in output and "<table>" in output and "<strong>" in output


@pytest.mark.parametrize("factory", [parser, text_document_parser])
def test_literal_code_math_and_escaped_arrows_are_protected(factory):
    source = (
        r"\-> \<- \<-> -&gt; &lt;-&gt; `a -> b` $x_1 -> y$"
        "\n\n$$x_1 -> y$$\n\n```python\ndef f() -> int:\n    pass\n```"
        "\n\n    a -> b\n\n> $$a <-> b$$\n"
    )
    output = unescape(factory().render(source))
    assert "→" not in output and "←" not in output and "↔" not in output
    for text in ["-> <- <->", "a -> b", "x_1 -> y", "a <-> b"]:
        assert text in output


@pytest.mark.parametrize("factory", [parser, text_document_parser])
def test_urls_and_destinations_are_preserved_but_link_labels_are_text(factory):
    source = (
        '[A -> B](file->.md "Title ->") ![C <- D](image->.png)\n\n'
        "<https://example.org/path> https://example.org/a->b\n\n"
        "www.example.org/path mailto:example@example.org example ->"
    )
    rules = {**DEFAULT_REPLACEMENTS, "example": "changed"}
    output = unescape(factory(rules).render(source))
    assert 'href="file-%3E.md"' in output and 'src="image-%3E.png"' in output
    assert 'title="Title ->"' in output
    assert "A → B" in output and "C ← D" in output
    assert "changed.org" not in output
    assert "changed →" in output
    assert "→b" not in output


@pytest.mark.parametrize("factory", [parser, text_document_parser])
def test_literal_longest_match_overrides_and_no_chained_replacements(factory):
    rules = validate_document_replacements(
        {"->": "=>", "=>": "⇒", "<-": "<-", "(test)": "**<b>literal</b>**"}
    )
    output = factory(rules).render("A->B <-> <- => (test)")
    assert "A=&gt;B ↔ &lt;- ⇒" in output
    assert "**&lt;b&gt;literal&lt;/b&gt;**" in output
    assert "<b>literal</b>" not in output and "<strong>" not in output


@pytest.mark.parametrize("factory", [parser, text_document_parser])
def test_other_typography_is_unchanged(factory):
    source = '"Zitat" -- --- ... !!!!! ????? ,,, +- (c)'
    assert unescape(factory().render(source)) == f"<p>{source}</p>\n"


def test_existing_config_defaults_and_custom_rules_survive_settings(
    tmp_path, monkeypatch
):
    config = prepare_root(tmp_path)
    path = tmp_path / "config.toml"
    monkeypatch.setattr("pult.config.app_config.APP_CONFIG_PATH", path)
    path.write_text(
        f'root = "{tmp_path}"\neditor = "true"\nactive_school_year = "{config.active_school_year}"\n'
    )
    assert load_app_config().document_replacements == DEFAULT_REPLACEMENTS
    with path.open("a") as file:
        file.write('\n[document_replacements]\n"=>" = "⇒"\n"<-" = "<-"\n')
    loaded = load_app_config()
    expected = {**DEFAULT_REPLACEMENTS, "=>": "⇒", "<-": "<-"}
    assert loaded.document_replacements == expected
    updated = update_settings(loaded, "nano", loaded.active_school_year)
    assert updated.document_replacements == expected
    assert load_app_config() == updated
    other = AppConfig(tmp_path, "true", config.active_school_year)
    loaded.document_replacements["->"] = "different"
    assert other.document_replacements["->"] == "→"


@pytest.mark.parametrize(
    "invalid",
    [[], "->", {"": "→"}, {" ": "→"}, {"->": 3}, {"a\nb": "x"}, {"x": "a\nb"}],
)
def test_invalid_rules_do_not_overwrite_config(tmp_path, monkeypatch, invalid):
    path = tmp_path / "config.toml"
    monkeypatch.setattr("pult.config.app_config.APP_CONFIG_PATH", path)
    config = AppConfig(tmp_path, "true", "2026-2027")
    save_app_config(config)
    original = path.read_bytes()
    config.document_replacements = invalid
    with pytest.raises(ValueError, match="document_replacements"):
        save_app_config(config)
    assert path.read_bytes() == original


def test_planning_and_workbook_exports_use_configured_rules(tmp_path, sequences):
    config = setup_export(tmp_path, sequences[0])
    config.document_replacements["->"] = "⟶"
    lesson = Lesson(
        "arrows", "Pfeile", goals=["A -> B"], phases=[Phase("Übung", "C -> D")]
    )
    output = document_html(
        "",
        tmp_path / "verlauf.md",
        tmp_path,
        800,
        19,
        "#000000",
        "#ffffff",
        "#aaaaaa",
        planning=lesson,
        replacements=config.document_replacements,
    )
    assert "A ⟶ B" in output and "C ⟶ D" in output
    task = Task(
        "arrows",
        "Aufgabe -> Ziel",
        "Lösung -> Ergebnis",
        metadata=TaskMetadata("Pfeile", ["K5"], "I"),
    )
    save_task(tmp_path, task)
    sources = {
        path: path.read_bytes() for path in (tmp_path / "aufgaben/arrows").glob("*.md")
    }
    renderer = SimpleNamespace(
        resolve_font=AsyncMock(return_value="source-sans-3"),
        render_pdf=AsyncMock(return_value=b"%PDF-test"),
    )
    asyncio.run(
        export_task_workbooks(
            renderer, config, sequence=sequences[0], directory=tmp_path
        )
    )
    documents = [call.args[0] for call in renderer.render_pdf.call_args_list]
    assert "Aufgabe ⟶ Ziel" in documents[0] and "Lösung ⟶ Ergebnis" in documents[1]
    assert all(path.read_bytes() == original for path, original in sources.items())


def test_cache_key_changes_when_rendered_replacements_change(tmp_path, monkeypatch):
    async def run():
        renderer = DocumentRenderer(tmp_path / "cache")
        page = mock_browser(renderer, monkeypatch)
        args = (
            "A -> B",
            tmp_path / "text.md",
            tmp_path,
            800,
            19,
            "#000000",
            "#ffffff",
            "#aaaaaa",
        )
        first = await renderer.render(*args, font="source-sans-3")
        changed = await renderer.render(
            *args, font="source-sans-3", replacements={"->": "⟶"}
        )
        assert first != changed
        assert page.screenshot.await_count == 2
        assert await renderer.render(*args, font="source-sans-3") == first
        assert page.screenshot.await_count == 2

    asyncio.run(run())


def test_textual_and_rich_fallback_preserve_tex_with_custom_replacements(tmp_path):
    source = "A -> B mit $x_1 -> y$.\n\n$$a_b <-> c$$"
    rules = {"->": "⟶", "<->": "↔"}
    markdown = RichMarkdown(source)
    markdown.parsed = text_document_parser(rules).parse(source)
    console = Console(width=80, force_terminal=False)
    with console.capture() as capture:
        console.print(markdown)
    assert "A ⟶ B mit $x_1 -> y$." in capture.get()

    class ViewerApp(App):
        app_config = SimpleNamespace(document_replacements=rules)

        def compose(self):
            viewer = DocumentViewer(source, tmp_path / "text.md", tmp_path)
            viewer.text_mode = True
            yield viewer

    async def run():
        app = ViewerApp()
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.pause(0.3)
            await app.workers.wait_for_complete()
            text = "\n".join(
                widget._content.plain for widget in app.query("MarkdownParagraph")
            )
            assert "A ⟶ B mit $x_1 -> y$." in text and "$$a_b <-> c$$" in text

    asyncio.run(run())
