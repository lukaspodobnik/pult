import csv
import os
import tempfile
import tomllib
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import tomli_w


def load_toml(path: Path) -> dict[str, Any]:
    """Lade eine TOML-Datei; eine fehlende Datei wird nicht abgefangen."""
    with path.open("rb") as file:
        return tomllib.load(file)


def save_toml(path: Path, data: dict[str, Any]) -> None:
    """Speichere TOML-Daten, ohne das Elternverzeichnis anzulegen."""
    content = tomli_w.dumps(data)
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, delete=False
        ) as file:
            temp_path = Path(file.name)
            file.write(content)
            file.flush()
            os.fsync(file.fileno())
        temp_path.replace(path)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def load_csv(path: Path) -> list[dict[str, str]]:
    """Lade alle Zeilen einer CSV-Datei als String-Dictionaries."""
    with path.open("r", newline="") as file:
        reader = csv.DictReader(file)
        return list(reader)


def save_csv(
    path: Path, fieldnames: tuple[str, ...], rows: Iterable[dict[str, str]]
) -> None:
    """Ersetze eine CSV-Datei durch die übergebenen Zeilen und Spalten."""
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
