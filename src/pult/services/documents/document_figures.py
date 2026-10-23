"""Kompakte Abbildungen neben Markdown-Text, auch innerhalb einer Teilaufgabe."""

from markdown_it import MarkdownIt
from markdown_it.rules_core import StateCore
from markdown_it.token import Token
from mdit_py_plugins.container import container_plugin

OPEN = "container_abbildung_open"
CLOSE = "container_abbildung_close"

FIGURE_STYLES = """
article {container-type:inline-size}
.illustrated {
  display:grid; grid-template-columns:minmax(0,1fr) min(30%,11em);
  align-items:start; gap:1.2em; margin:.8em 0; break-inside:avoid;
}
.illustrated-text {min-width:0}
.illustrated-text > :first-child {margin-top:0}
.illustrated-text > :last-child {margin-bottom:0}
.illustrated > figure {margin:0; min-width:0}
.illustrated > figure p {margin:0}
.illustrated > figure img {display:block; width:100%; max-width:11em; height:auto}
@container (max-width:27em) {
  .illustrated {display:block}
  .illustrated > figure {margin:.6em 0 0; width:min(100%,11em)}
}
"""


def _wrap(tag: str, body: list[Token], class_name: str) -> list[Token]:
    return [
        Token("figure_layout_open", tag, 1, attrs={"class": class_name}, block=True),
        *body,
        Token("figure_layout_close", tag, -1, block=True),
    ]


def _layout(body: list[Token]) -> list[Token]:
    """Genau ein freistehendes Bild zuordnen; andere Inhalte unverändert erhalten."""
    depth = 0
    images = []
    for index, token in enumerate(body):
        if depth == 0 and token.type == "paragraph_open" and index + 2 < len(body):
            inline, closing = body[index + 1 : index + 3]
            children = inline.children or []
            if (
                inline.type == "inline"
                and closing.type == "paragraph_close"
                and len(children) == 1
                and children[0].type == "image"
            ):
                images.append(index)
        depth += token.nesting
    if len(images) != 1 or len(body) == 3:
        return body
    index = images[0]
    return _wrap(
        "div",
        _wrap("div", body[:index] + body[index + 3 :], "illustrated-text")
        + _wrap("figure", body[index : index + 3], "illustrated-image"),
        "illustrated",
    )


def figures_plugin(md: MarkdownIt, *, text_only: bool = False) -> None:
    md.use(
        container_plugin,
        "abbildung",
        validate=lambda info, markup: info.strip() == "abbildung",
    )

    def figures(state: StateCore) -> None:
        def transform(tokens: list[Token]) -> list[Token]:
            result = []
            index = 0
            while index < len(tokens):
                if tokens[index].type != OPEN:
                    result.append(tokens[index])
                    index += 1
                    continue
                end, depth = index + 1, 1
                while end < len(tokens):
                    depth += (tokens[end].type == OPEN) - (tokens[end].type == CLOSE)
                    if depth == 0:
                        break
                    end += 1
                body = transform(tokens[index + 1 : end])
                result.extend(body if text_only else _layout(body))
                index = end + 1
            return result

        state.tokens = transform(state.tokens)
        level = 0
        for token in state.tokens:
            if token.nesting == -1:
                level -= 1
            token.level = level
            if token.nesting == 1:
                level += 1

    md.core.ruler.after("inline", "pult_figures", figures)
