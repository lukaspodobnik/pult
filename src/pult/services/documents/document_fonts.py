"""Gemeinsame Dokumenttypografie mit lokalem Avenir und freier Ersatzschrift."""

import base64
from functools import lru_cache
from pathlib import Path

FONT_CHOICES = {"auto", "avenir-next", "source-sans-3"}
FONT_DIRECTORY = Path(__file__).parents[2] / "assets" / "fonts"


def validate_document_font(value: str) -> str:
    if value not in FONT_CHOICES:
        raise ValueError("Bitte wähle eine gültige Dokumentschrift aus.")
    return value


@lru_cache(maxsize=None)
def embedded_font_faces(family: str, filename: str) -> str:
    rules = []
    for suffix, style in (("", "normal"), ("-Italic", "italic")):
        data = base64.b64encode(
            (FONT_DIRECTORY / f"{filename}{suffix}.ttf").read_bytes()
        ).decode("ascii")
        rules.append(
            f"@font-face {{font-family:'{family}';font-style:{style};"
            "font-weight:100 900;"
            f"src:url(data:font/ttf;base64,{data}) format('truetype');}}"
        )
    return "\n".join(rules)


def avenir_font_faces() -> str:
    rules = []
    for weight, face in ((400, "Regular"), (500, "Medium"), (600, "DemiBold")):
        for suffix, style in (("", "normal"), ("Italic", "italic")):
            local_face = "Italic" if weight == 400 and suffix else f"{face}{suffix}"
            rules.append(
                "@font-face {font-family:'Pult Avenir';"
                f"font-style:{style};font-weight:{weight};"
                f"src:local('AvenirNext-{local_face}');}}"
            )
    return "\n".join(rules)


@lru_cache(maxsize=2)
def document_font_stylesheet(font: str = "source-sans-3") -> str:
    validate_document_font(font)
    rules = [
        embedded_font_faces("Pult Source Sans", "SourceSans3"),
        embedded_font_faces("Pult Code", "JetBrainsMono"),
    ]
    family = "'Pult Source Sans',sans-serif"
    if font == "avenir-next":
        rules.append(avenir_font_faces())
        family = "'Pult Avenir','Pult Source Sans',sans-serif"
    rules.append(
        f"body {{font-family:{family};font-weight:400;}}"
        "h1,h2,h3,h4,h5,h6,table {font-family:inherit;}"
        "h1,h2,h3,h4,h5,h6 {font-weight:600;}"
        "strong,b {font-weight:500;}"
        "code {font-family:'Pult Code',monospace;}"
    )
    return "\n".join(rules)
