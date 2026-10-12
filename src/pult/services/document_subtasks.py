"""Teilaufgaben als Markdown-Blöcke mit gemeinsamem Raster für Ansicht und Druck."""

import re
from typing import Literal

from markdown_it import MarkdownIt
from markdown_it.rules_core import StateCore
from markdown_it.token import Token
from mdit_py_plugins.container import container_plugin

BLOCK_OPTIONS = re.compile(r"teilaufgaben(?:[ \t]+spalten=([123]))?")
ITEM_LABEL = re.compile(r"^([a-z]\))(?:[ \t]+|$)")
OPEN = "container_teilaufgaben_open"
CLOSE = "container_teilaufgaben_close"

SUBTASK_STYLES = """
.subtasks {
  --subtask-columns:1; --subtask-gap:1.6em;
  display:grid; align-items:baseline; column-gap:var(--subtask-gap); row-gap:.85em;
  grid-template-columns:repeat(auto-fill,minmax(min(100%,max(12em,
    calc((100% - (var(--subtask-columns) - 1)*var(--subtask-gap))/var(--subtask-columns)))),1fr));
  margin:1em 0;
}
.subtasks[data-columns="2"] {--subtask-columns:2}
.subtasks[data-columns="3"] {--subtask-columns:3}
.subtask {
  display:grid; grid-template-columns:1.6em minmax(0,1fr); column-gap:.4em;
  align-items:baseline; min-width:0; break-inside:avoid;
}
.subtask > .subtask-label {margin:0; font-weight:500}
.subtask-content {min-width:0}
.subtask-content > :first-child {margin-top:0}
.subtask-content > :last-child {margin-bottom:0}
"""


def _tag(kind: str, tag: str, nesting: Literal[-1, 0, 1], **attrs: str) -> Token:
    return Token(kind, tag, nesting, attrs={**attrs}, block=True)


def _grid(opening: Token, body: list[Token]) -> list[Token]:
    """Nur Beschriftungen am Anfang eines direkten Absatzes beginnen ein neues Feld."""
    result: list[Token] = []
    started = False
    skip_until = 0
    for index, token in enumerate(body):
        if index < skip_until:
            continue
        match = None
        if (
            token.type == "paragraph_open"
            and token.level == opening.level + 1
            and index + 1 < len(body)
            and body[index + 1].type == "inline"
        ):
            match = ITEM_LABEL.match(body[index + 1].content)
        if match is not None:
            if started:
                result.extend(
                    [
                        _tag("subtask_content_close", "div", -1),
                        _tag("subtask_close", "div", -1),
                    ]
                )
            else:
                options = BLOCK_OPTIONS.fullmatch(opening.info.strip())
                assert options is not None
                result.append(
                    _tag(
                        "subtasks_open",
                        "div",
                        1,
                        **{"class": "subtasks", "data-columns": options[1] or "1"},
                    )
                )
                started = True
            result.extend(
                [
                    _tag("subtask_open", "div", 1, **{"class": "subtask"}),
                    _tag("paragraph_open", "p", 1, **{"class": "subtask-label"}),
                    Token("inline", "", 0, content=match[1]),
                    _tag("paragraph_close", "p", -1),
                    _tag(
                        "subtask_content_open", "div", 1, **{"class": "subtask-content"}
                    ),
                ]
            )
            body[index + 1].content = body[index + 1].content[match.end() :]
            if not body[index + 1].content:
                skip_until = index + 3
                continue
        result.append(token)
    if started:
        result.extend(
            [
                _tag("subtask_content_close", "div", -1),
                _tag("subtask_close", "div", -1),
                _tag("subtasks_close", "div", -1),
            ]
        )
    return result


def subtasks_plugin(md: MarkdownIt, *, text_only: bool = False) -> None:
    """Im Textmodus bleiben die ursprünglichen Absätze samt Buchstaben erhalten."""
    md.use(
        container_plugin,
        "teilaufgaben",
        validate=lambda info, markup: BLOCK_OPTIONS.fullmatch(info.strip()) is not None,
    )

    def subtasks(state: StateCore) -> None:
        def transform(tokens: list[Token]) -> list[Token]:
            result: list[Token] = []
            index = 0
            while index < len(tokens):
                opening = tokens[index]
                if opening.type != OPEN:
                    result.append(opening)
                    index += 1
                    continue
                end = index + 1
                depth = 1
                while end < len(tokens):
                    depth += (tokens[end].type == OPEN) - (tokens[end].type == CLOSE)
                    if depth == 0:
                        break
                    end += 1
                body = tokens[index + 1 : end]
                # Convert outside-in so nested markers cannot become sibling items.
                result.extend(transform(body if text_only else _grid(opening, body)))
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

    md.core.ruler.before("inline", "pult_subtasks", subtasks)
