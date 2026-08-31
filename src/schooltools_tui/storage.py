import csv
import tomllib
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import tomli_w


def load_toml(path: Path) -> dict[str, Any]:
    with path.open("rb") as file:
        return tomllib.load(file)


def save_toml(path: Path, data: dict[str, Any]) -> None:
    with path.open("wb") as file:
        tomli_w.dump(data, file)


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", newline="") as file:
        reader = csv.DictReader(file)
        return list(reader)


def save_csv(path: Path, fieldnames: tuple[str, ...], rows: Iterable[dict[str, str]]) -> None:
    with path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
