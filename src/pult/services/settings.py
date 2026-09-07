from dataclasses import replace
from datetime import date

from pult.config import AppConfig, save_app_config
from pult.initialization.school_year import initialize_school_year
from pult.school.calendar import load_school_calendar
from pult.school.school_year import get_school_year_options

EDITOR_OPTIONS = [
    ("Neovim (btw)", "nvim"),
    ("Vim", "vim"),
    ("Nano", "nano"),
    ("Micro", "micro"),
    ("Emacs (Terminal)", "emacs -nw"),
    ("Visual Studio Code", "code --wait"),
]


def get_editor_options(current: str = "nvim") -> list[tuple[str, str]]:
    """Erhalte auch einen zuvor manuell konfigurierten Editor-Befehl."""
    options = list(EDITOR_OPTIONS)
    if current not in {value for _, value in options}:
        options.append((f"Bisheriger Editor: {current}", current))
    return options


def update_settings(config: AppConfig, editor: str, year: str) -> AppConfig:
    """Bereite das gewählte Jahr ohne Überschreiben vor; speichere erst danach."""
    if not editor.strip():
        raise ValueError("Bitte wähle einen Editor aus.")
    if year not in {value for _, value in get_school_year_options(config.root)}:
        raise ValueError("Für dieses Schuljahr ist kein gültiger Kalender vorhanden.")
    initialize_school_year(config.root, year)
    updated = replace(config, editor=editor, active_school_year=year)
    save_app_config(updated)
    return updated


def get_suggested_school_year(config: AppConfig, today: date) -> str | None:
    """Biete ein neueres Jahr erst ab seinem ersten Schultag an."""
    candidates = []
    for _, year in get_school_year_options(config.root):
        calendar = load_school_calendar(config.root, year)
        if (
            year > config.active_school_year
            and calendar.first_school_day <= today <= calendar.last_school_day
        ):
            candidates.append(year)
    return max(candidates, default=None)
