"""Gemeinsame Ablage für Exporte im Datenverzeichnis."""

import os
import re
import tempfile
from pathlib import Path

from pult.school.calendar import validate_school_year
from pult.services.document_fonts import document_font_stylesheet


def pdf_stylesheet(font: str) -> str:
    """Gemeinsame Schrift, Überschriften und Farben für PDF-Exporte."""
    return (
        document_font_stylesheet(font)
        + """
body { margin:0; color:#253038; font-size:10pt; line-height:1.35; }
h1 { font-size:20pt; margin:0 0 3mm; font-weight:600; }
.meta { margin:0 0 6mm; color:#59616a; }
"""
    )


def export_path(
    root: Path,
    year: str,
    document: str,
    *,
    school_class_id: str | None = None,
    subject_id: str | None = None,
) -> Path:
    year = validate_school_year(year)
    for component in (document, subject_id):
        if component is not None and not re.fullmatch(
            r"[a-z0-9]+(?:-[a-z0-9]+)*", component
        ):
            raise ValueError("Ungültige Exportbezeichnung.")
    if school_class_id is not None and (
        school_class_id in {"", ".", "..", "uebersichten"}
        or any(c in school_class_id for c in "/\\")
    ):
        raise ValueError("Ungültige Klassenbezeichnung für den Export.")
    directory = school_class_id if school_class_id is not None else "uebersichten"
    filename = document + (f"-{subject_id}" if subject_id else "") + ".pdf"
    return root / "exports" / year / directory / filename


def save_pdf(target: Path, content: bytes) -> Path:
    """Eine bestehende Datei erst nach vollständigem Schreiben ersetzen."""
    if not content.startswith(b"%PDF-"):
        raise ValueError("Der Renderer hat keine PDF-Datei erzeugt.")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=target.parent, suffix=".tmp", delete=False
        ) as stream:
            temporary = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(target)
        return target
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
