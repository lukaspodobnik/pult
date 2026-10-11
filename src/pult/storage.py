import csv
import io
import os
import tempfile
import tomllib
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import tomli_w


def save_bytes(path: Path, content: bytes) -> None:
    """Ersetze eine Datei erst nach vollständigem Schreiben; lege keine Ordner an."""
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=path.parent, suffix=".tmp", delete=False
        ) as file:
            temporary = Path(file.name)
            file.write(content)
            file.flush()
            os.fsync(file.fileno())
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def save_text(path: Path, content: str) -> None:
    """Speichere UTF-8-Text über denselben sicheren Schreibweg wie Binärdateien."""
    save_bytes(path, content.encode("utf-8"))


def load_toml(path: Path) -> dict[str, Any]:
    """Lade eine TOML-Datei; eine fehlende Datei wird nicht abgefangen."""
    with path.open("rb") as file:
        return tomllib.load(file)


def save_toml(path: Path, data: dict[str, Any]) -> None:
    """Speichere TOML-Daten, ohne das Elternverzeichnis anzulegen."""
    save_text(path, tomli_w.dumps(data))


def load_csv(path: Path) -> list[dict[str, str]]:
    """Lade alle Zeilen einer UTF-8-CSV-Datei als String-Dictionaries."""
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def save_csv(
    path: Path, fieldnames: tuple[str, ...], rows: Iterable[dict[str, str]]
) -> None:
    """Ersetze eine CSV-Datei durch die vollständig aufbereiteten Zeilen und Spalten."""
    with io.StringIO(newline="") as buffer:
        writer = csv.DictWriter(buffer, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        save_text(path, buffer.getvalue())
