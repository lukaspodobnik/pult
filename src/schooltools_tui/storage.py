import csv
import tomllib
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import tomli_w


def load_toml(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None

    with path.open("rb") as file:
        return tomllib.load(file)


def save_toml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("wb") as file:
        tomli_w.dump(data, file)


def load_csv(path: Path) -> list[dict[str, str]] | None:
    if not path.exists():
        return None

    with path.open("r", newline="") as file:
        reader = csv.DictReader(file)
        return list(reader)


def save_csv(path: Path, fieldnames: tuple[str, ...], rows: Iterable[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
