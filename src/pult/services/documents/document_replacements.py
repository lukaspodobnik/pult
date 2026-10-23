"""Ersetzungen in Markdown-Text; Quelltext, Code, Formeln und URLs bleiben erhalten."""

import re
from collections.abc import Mapping

from markdown_it import MarkdownIt
from markdown_it.rules_core import StateCore
from markdown_it.token import Token

DEFAULT_REPLACEMENTS = {"->": "→", "<-": "←", "<->": "↔"}
URL = re.compile(r"(?:[a-zA-Z][a-zA-Z0-9+.-]*://|mailto:|www\.)\S+")


def validate_document_replacements(value: object) -> dict[str, str]:
    if not isinstance(value, dict) or any(
        not isinstance(source, str)
        or not source.strip()
        or not isinstance(target, str)
        or any(char in source or char in target for char in "\r\n\0")
        for source, target in value.items()
    ):
        raise ValueError(
            "document_replacements muss eine Tabelle mit einzeiligen Textpaaren sein; "
            "der zu ersetzende Text darf nicht leer sein."
        )
    return {**DEFAULT_REPLACEMENTS, **value}


def replacements_plugin(
    md: MarkdownIt, replacements: Mapping[str, str] | None = None
) -> None:
    rules = dict(DEFAULT_REPLACEMENTS if replacements is None else replacements)
    if not rules:
        return
    # One pass, longest match first: <-> stays a single arrow, and replacement
    # text is never interpreted as another rule or as Markdown/HTML.
    pattern = re.compile(
        "|".join(re.escape(key) for key in sorted(rules, key=len, reverse=True))
    )

    def replace_text(tokens: list[Token]) -> str:
        text = "".join(token.content for token in tokens)
        protected = [match.span() for match in URL.finditer(text)]
        offset = 0
        for token in tokens:
            end = offset + len(token.content)
            if token.type == "text_special":
                protected.append((offset, end))
            offset = end

        def substitute(match: re.Match[str]) -> str:
            if any(
                start < match.end() and end > match.start() for start, end in protected
            ):
                return match[0]
            return rules[match[0]]

        return pattern.sub(substitute, text)

    def replace_tokens(tokens: list[Token]) -> None:
        result = []
        in_autolink = False
        index = 0
        while index < len(tokens):
            token = tokens[index]
            if token.type in {"text", "text_special"} and not in_autolink:
                end = index + 1
                while end < len(tokens) and tokens[end].type in {
                    "text",
                    "text_special",
                }:
                    end += 1
                token.content = replace_text(tokens[index:end])
                token.type = "text"
                result.append(token)
                index = end
                continue
            if token.type == "link_open" and token.info == "auto":
                in_autolink = True
            elif token.type == "link_close":
                in_autolink = False
            if token.children:
                replace_tokens(token.children)
            result.append(token)
            index += 1
        tokens[:] = result

    def replace_document(state: StateCore) -> None:
        replace_tokens(state.tokens)

    # Escaped punctuation and entities are still separate text_special tokens.
    md.core.ruler.before("text_join", "pult_replacements", replace_document)


def literal_math_plugin(md: MarkdownIt) -> None:
    """Nach den Ersetzungen TeX als normalen Text für Rich und Textual ausgeben."""

    def restore_inline(tokens: list[Token]) -> None:
        for token in tokens:
            if token.type.startswith("math_inline"):
                token.content = token.markup + token.content + token.markup
                token.type, token.tag = "text", ""
            if token.children:
                restore_inline(token.children)

    def literal_math(state: StateCore) -> None:
        restore_inline(state.tokens)
        result = []
        for token in state.tokens:
            if not token.type.startswith("math_block"):
                result.append(token)
                continue
            text = token.markup + token.content + token.markup
            if token.info:
                text += f" ({token.info})"
            result.extend(
                [
                    Token("paragraph_open", "p", 1, block=True, level=token.level),
                    Token(
                        "inline",
                        "",
                        0,
                        content=text,
                        level=token.level,
                        children=[Token("text", "", 0, content=text)],
                    ),
                    Token("paragraph_close", "p", -1, block=True, level=token.level),
                ]
            )
        state.tokens = result

    md.core.ruler.after("text_join", "pult_literal_math", literal_math)
