"""Neue Aufgaben nach dem Materialvertrag ohne Überschreiben anlegen."""

import re
import unicodedata
from pathlib import Path

from pult.curriculum.material import Task, TaskMetadata, material_path, save_task


def create_task_files(
    directory: Path, metadata: TaskMetadata
) -> tuple[str, list[Path]]:
    metadata.__post_init__()
    title = metadata.title
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
    paths = [target / name for name in ("aufgabe.md", "loesung.md", "aufgabe.toml")]
    try:
        save_task(directory, Task(task_id, f"# {title}\n\n", "", metadata=metadata))
    except OSError:
        for path in paths:
            path.unlink(missing_ok=True)
        target.rmdir()
        raise
    return task_id, paths
