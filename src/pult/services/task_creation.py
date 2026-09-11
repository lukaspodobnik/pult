"""Neue Aufgaben nach dem Materialvertrag ohne Überschreiben anlegen."""

import re
import unicodedata
from pathlib import Path

from pult.curriculum.material import material_path


def create_task_files(directory: Path, title: str) -> tuple[str, list[Path]]:
    title = " ".join(title.split())
    if not title:
        raise ValueError("Bitte einen Aufgabentitel eingeben.")
    normalized = (
        title.lower()
        .replace("ä", "ae")
        .replace("ö", "oe")
        .replace("ü", "ue")
        .replace("ß", "ss")
    )
    ascii_title = (
        unicodedata.normalize("NFKD", normalized).encode("ascii", "ignore").decode()
    )
    stem = (
        re.sub(r"[^a-z0-9]+", "-", ascii_title).strip("-")[:80].rstrip("-") or "aufgabe"
    )
    folder = material_path(directory, "aufgaben")
    folder.mkdir(parents=True, exist_ok=True)
    number = 1
    while True:
        task_id = stem if number == 1 else f"{stem}-{number}"
        target = folder / task_id
        try:
            target.mkdir()
            break
        except FileExistsError:
            number += 1
    paths = [target / "aufgabe.md", target / "loesung.md"]
    try:
        paths[0].write_text(f"# {title}\n\n", encoding="utf-8")
        paths[1].write_text("", encoding="utf-8")
    except OSError:
        for path in paths:
            path.unlink(missing_ok=True)
        target.rmdir()
        raise
    return task_id, paths
