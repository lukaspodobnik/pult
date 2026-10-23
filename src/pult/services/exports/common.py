"""Gemeinsame Ablage für Exporte im Datenverzeichnis."""

import re
from pathlib import Path

from playwright.async_api import Error as PlaywrightError

from pult.curriculum.material import validate_id
from pult.school.calendar import validate_school_year
from pult.services.documents.document_fonts import document_font_stylesheet
from pult.storage import save_bytes


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
    save_bytes(target, content)
    return target


def export_error_message(error: Exception) -> str:
    if isinstance(error, PlaywrightError):
        return (
            "Der PDF-Export benötigt die Dokumentdarstellung. "
            "Bitte unter Einstellungen → Dokumentdarstellung einrichten prüfen."
        )
    return f"Der PDF-Export ist fehlgeschlagen: {error}"


def material_export_path(
    root: Path,
    year: str,
    grade: int,
    subject_id: str,
    sequence_id: str,
    document: str,
) -> Path:
    """Klassenunabhängige Materialien unter derselben jährlichen Exportablage."""
    year = validate_school_year(year)
    if type(grade) is not int or not 5 <= grade <= 13:
        raise ValueError("Ungültiger Jahrgang für den Export.")
    for value in (subject_id, sequence_id, document):
        if (
            not isinstance(value, str)
            or validate_id(value, "Exportbezeichnung") != value
        ):
            raise ValueError("Ungültige Exportbezeichnung.")
    return (
        root
        / "exports"
        / year
        / "materialien"
        / subject_id
        / str(grade)
        / sequence_id
        / f"{document}.pdf"
    )
