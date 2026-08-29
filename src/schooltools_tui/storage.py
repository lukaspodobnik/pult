import tomllib
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
