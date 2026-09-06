"""Gemeinsame deutsche Beschriftungen und Datumsformate für die Oberfläche."""

import re
from datetime import date, datetime

DATE_INPUT_HINT = "TT.MM.JJJJ"
UNTITLED_LESSON = "Noch ohne Titel"
NEXT_LESSON_LABEL = "Nächste Stunde"
NO_NEXT_LESSON = "Keine offene geplante Stunde"

WEEKDAY_NAMES = (
    "Montag",
    "Dienstag",
    "Mittwoch",
    "Donnerstag",
    "Freitag",
    "Samstag",
    "Sonntag",
)
WEEKDAYS = tuple(
    zip(("monday", "tuesday", "wednesday", "thursday", "friday"), WEEKDAY_NAMES[:5])
)


def format_date(value: date, *, with_weekday: bool = False) -> str:
    """Formatiere ein Datum als TT.MM.JJJJ, optional mit deutschem Wochentag."""
    text = f"{value.day:02d}.{value.month:02d}.{value.year:04d}"
    return f"{WEEKDAY_NAMES[value.weekday()]}, {text}" if with_weekday else text


def parse_date(value: str, description: str = "Das Datum") -> date:
    """Lies ein gültiges Datum im Eingabeformat TT.MM.JJJJ."""
    value = value.strip()
    try:
        if not re.fullmatch(r"[0-9]{2}\.[0-9]{2}\.[0-9]{4}", value):
            raise ValueError
        return datetime.strptime(value, "%d.%m.%Y").date()
    except ValueError as error:
        raise ValueError(
            f"{description} muss ein gültiges Datum im Format {DATE_INPUT_HINT} sein."
        ) from error


def format_school_year(school_year: str) -> str:
    """Formatiere den internen Schuljahreswert 2026-2027 als 2026/27."""
    start_year, end_year = school_year.split("-")
    return f"{start_year}/{end_year[-2:]}"
