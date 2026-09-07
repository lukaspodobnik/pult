import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Any

from pult.school.school_class import get_school_class_path
from pult.storage import load_toml, save_toml

CALENDARS_DIRECTORY_NAME = Path("calendars")
CALENDAR_FILE_SUFFIX = ".toml"
CLOSURES_FILE_NAME = Path("closures.toml")
SCHOOL_YEARS_DIRECTORY_NAME = Path("school-years")
SCHOOL_YEAR_PATTERN = re.compile(r"([0-9]{4})-([0-9]{4})")


class CalendarFileError(ValueError):
    """Raised when an official school calendar file is invalid."""


class ClosuresFileError(ValueError):
    """Raised when a local closures file is invalid."""


class ClosureKind(StrEnum):
    SCHOOL_HOLIDAY = "school-holiday"
    PUBLIC_HOLIDAY = "public-holiday"
    LOCAL = "local"


@dataclass(frozen=True)
class Closure:
    name: str
    kind: ClosureKind
    start: date
    end: date

    def __post_init__(self) -> None:
        if not isinstance(self.name, str):
            raise TypeError("Der Name des Ausfalls muss ein Text sein.")

        name = self.name.strip()
        if not name:
            raise ValueError("Der Name des Ausfalls darf nicht leer sein.")
        object.__setattr__(self, "name", name)

        if not isinstance(self.kind, ClosureKind):
            raise TypeError("Die Art des Ausfalls ist ungültig.")

        if type(self.start) is not date or type(self.end) is not date:
            raise TypeError("Start und Ende müssen Datumswerte ohne Uhrzeit sein.")

        if self.end < self.start:
            raise ValueError("Das Ende des Ausfalls darf nicht vor dem Start liegen.")


@dataclass(frozen=True)
class SchoolCalendar:
    school_year: str
    first_school_day: date
    last_school_day: date
    closures: tuple[Closure, ...]

    def __post_init__(self) -> None:
        school_year = validate_school_year(self.school_year)
        object.__setattr__(self, "school_year", school_year)

        if (
            type(self.first_school_day) is not date
            or type(self.last_school_day) is not date
        ):
            raise TypeError(
                "Erster und letzter Schultag müssen Datumswerte ohne Uhrzeit sein."
            )

        if self.last_school_day < self.first_school_day:
            raise ValueError(
                "Der letzte Schultag darf nicht vor dem ersten Schultag liegen."
            )

        if not isinstance(self.closures, tuple) or any(
            not isinstance(closure, Closure) for closure in self.closures
        ):
            raise TypeError("Kalenderschließungen müssen als Tupel angegeben werden.")

        if any(closure.kind is ClosureKind.LOCAL for closure in self.closures):
            raise ValueError(
                "Ein offizieller Schulkalender darf keine lokalen Ausfälle enthalten."
            )

        _validate_dates_in_school_year(
            school_year,
            self.first_school_day,
            self.last_school_day,
            "Der Unterrichtszeitraum",
        )
        _validate_closures(self.closures, school_year)

        if self.first_school_day.weekday() >= 5:
            raise ValueError("Der erste Schultag darf nicht am Wochenende liegen.")
        if self.last_school_day.weekday() >= 5:
            raise ValueError("Der letzte Schultag darf nicht am Wochenende liegen.")
        if is_date_closed(self.first_school_day, self.closures):
            raise ValueError("Der erste Schultag darf kein Schließtag sein.")
        if is_date_closed(self.last_school_day, self.closures):
            raise ValueError("Der letzte Schultag darf kein Schließtag sein.")

        object.__setattr__(
            self,
            "closures",
            tuple(sorted(self.closures, key=_closure_sort_key)),
        )


def validate_school_year(year: str) -> str:
    """Normalisiere ein Schuljahr im Format ``2026-2027`` und validiere es."""
    if not isinstance(year, str):
        raise TypeError("Das Schuljahr muss ein Text sein.")

    year = year.strip()
    match = SCHOOL_YEAR_PATTERN.fullmatch(year)
    if match is None:
        raise ValueError("Das Schuljahr muss dem Format '2026-2027' entsprechen.")

    start_year, end_year = (int(part) for part in match.groups())
    if end_year != start_year + 1:
        raise ValueError("Ein Schuljahr muss zwei aufeinanderfolgende Jahre umfassen.")

    return year


def get_school_calendar_path(root: Path, year: str) -> Path:
    """Gib den Pfad des offiziellen Kalenders eines Schuljahres zurück."""
    year = validate_school_year(year)
    return root / CALENDARS_DIRECTORY_NAME / f"{year}{CALENDAR_FILE_SUFFIX}"


def get_school_closures_path(root: Path, year: str) -> Path:
    """Gib den Pfad der schulweiten lokalen Ausfälle zurück."""
    year = validate_school_year(year)
    return root / SCHOOL_YEARS_DIRECTORY_NAME / year / CLOSURES_FILE_NAME


def get_class_closures_path(
    root: Path,
    year: str,
    school_class_id: str,
) -> Path:
    """Gib den Pfad der lokalen Ausfälle einer Klasse zurück."""
    year = validate_school_year(year)
    class_directory = get_school_class_path(root, year, school_class_id).parent
    return class_directory / CLOSURES_FILE_NAME


def load_school_calendar(root: Path, year: str) -> SchoolCalendar:
    """Lade und validiere den offiziellen Kalender eines Schuljahres."""
    path = get_school_calendar_path(root, year)

    try:
        data = load_toml(path)
        _require_exact_keys(
            data,
            {
                "school_year",
                "first_school_day",
                "last_school_day",
                "closures",
            },
            "Kalenderdatei",
        )
        closures_data = _require_list(data, "closures")
        calendar = SchoolCalendar(
            school_year=_require_string(data, "school_year"),
            first_school_day=_require_date(data, "first_school_day"),
            last_school_day=_require_date(data, "last_school_day"),
            closures=tuple(
                _load_closure(closure_data, index)
                for index, closure_data in enumerate(closures_data, start=1)
            ),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise CalendarFileError(f"Ungültige Kalenderdatei '{path}': {error}") from error

    expected_year = validate_school_year(year)
    if calendar.school_year != expected_year:
        raise CalendarFileError(
            f"Das Schuljahr in '{path}' stimmt nicht mit dem Dateinamen überein."
        )

    return calendar


def save_school_calendar(root: Path, calendar: SchoolCalendar) -> None:
    """Speichere einen validierten offiziellen Schulkalender."""
    data: dict[str, Any] = {
        "school_year": calendar.school_year,
        "first_school_day": calendar.first_school_day,
        "last_school_day": calendar.last_school_day,
        "closures": [_serialize_closure(closure) for closure in calendar.closures],
    }
    save_toml(
        get_school_calendar_path(root, calendar.school_year),
        data,
    )


def load_school_closures(root: Path, year: str) -> list[Closure]:
    """Lade die schulweiten lokalen Ausfälle eines Schuljahres."""
    return _load_local_closures(get_school_closures_path(root, year), year)


def load_class_closures(
    root: Path,
    year: str,
    school_class_id: str,
) -> list[Closure]:
    """Lade die lokalen Ausfälle einer einzelnen Klasse."""
    return _load_local_closures(
        get_class_closures_path(root, year, school_class_id),
        year,
    )


def save_school_closures(
    root: Path,
    year: str,
    closures: list[Closure],
) -> None:
    """Speichere die schulweiten lokalen Ausfälle eines Schuljahres."""
    _save_local_closures(get_school_closures_path(root, year), year, closures)


def save_class_closures(
    root: Path,
    year: str,
    school_class_id: str,
    closures: list[Closure],
) -> None:
    """Speichere die lokalen Ausfälle einer einzelnen Klasse."""
    _save_local_closures(
        get_class_closures_path(root, year, school_class_id),
        year,
        closures,
    )


def create_empty_school_closures(root: Path, year: str) -> None:
    """Lege die schulweite Ausfalldatei an, falls sie noch nicht existiert."""
    _create_empty_local_closures(get_school_closures_path(root, year), year)


def create_empty_class_closures(
    root: Path,
    year: str,
    school_class_id: str,
) -> None:
    """Lege die Ausfalldatei einer Klasse an, falls sie noch nicht existiert."""
    _create_empty_local_closures(
        get_class_closures_path(root, year, school_class_id),
        year,
    )


def is_date_closed(
    target_date: date,
    closures: Iterable[Closure],
) -> bool:
    """Prüfe, ob ein Datum in mindestens einem Ausfallzeitraum liegt."""
    if type(target_date) is not date:
        raise TypeError("Das zu prüfende Datum muss ein Datum ohne Uhrzeit sein.")

    return any(closure.start <= target_date <= closure.end for closure in closures)


def is_school_day(
    calendar: SchoolCalendar,
    target_date: date,
    local_closures: Iterable[Closure] = (),
) -> bool:
    """Prüfe Unterrichtszeitraum, Wochenende und offizielle sowie lokale Ausfälle."""
    if type(target_date) is not date:
        raise TypeError("Das zu prüfende Datum muss ein Datum ohne Uhrzeit sein.")

    if not calendar.first_school_day <= target_date <= calendar.last_school_day:
        return False

    if target_date.weekday() >= 5:
        return False

    return not is_date_closed(
        target_date,
        (*calendar.closures, *local_closures),
    )


def has_school_day(
    calendar: SchoolCalendar,
    start: date,
    end: date,
    local_closures: Iterable[Closure] = (),
) -> bool:
    """Prüfe, ob ein inklusiver Datumsbereich mindestens einen Schultag enthält."""
    if type(start) is not date or type(end) is not date:
        raise TypeError("Start und Ende müssen Datumswerte ohne Uhrzeit sein.")
    if end < start:
        raise ValueError("Das Ende darf nicht vor dem Start liegen.")

    local_closures = tuple(local_closures)
    candidate = start
    while candidate <= end:
        if is_school_day(calendar, candidate, local_closures):
            return True
        candidate += timedelta(days=1)

    return False


def _load_local_closures(path: Path, year: str) -> list[Closure]:
    try:
        data = load_toml(path)
        _require_exact_keys(data, {"closures"}, "Ausfalldatei")
        closures_data = _require_list(data, "closures")
        closures = [
            _load_closure(closure_data, index)
            for index, closure_data in enumerate(closures_data, start=1)
        ]
        _validate_local_closures(closures, year)
    except (KeyError, TypeError, ValueError) as error:
        raise ClosuresFileError(f"Ungültige Ausfalldatei '{path}': {error}") from error

    return sorted(closures, key=_closure_sort_key)


def _create_empty_local_closures(path: Path, year: str) -> None:
    if path.exists():
        if not path.is_file():
            raise IsADirectoryError(f"Der Ausfall-Pfad ist keine Datei: {path}")
        return

    _save_local_closures(path, year, [])


def _save_local_closures(
    path: Path,
    year: str,
    closures: list[Closure],
) -> None:
    if not isinstance(closures, list) or any(
        not isinstance(closure, Closure) for closure in closures
    ):
        raise TypeError("Lokale Ausfälle müssen als Liste angegeben werden.")

    _validate_local_closures(closures, year)
    sorted_closures = sorted(closures, key=_closure_sort_key)
    data: dict[str, Any] = {
        "closures": [_serialize_closure(closure) for closure in sorted_closures]
    }
    save_toml(path, data)


def _load_closure(data: Any, index: int) -> Closure:
    if not isinstance(data, dict):
        raise TypeError(f"Ausfall {index} muss eine TOML-Tabelle sein.")

    _require_exact_keys(
        data,
        {"name", "kind", "start", "end"},
        f"Ausfall {index}",
    )
    return Closure(
        name=_require_string(data, "name"),
        kind=ClosureKind(_require_string(data, "kind")),
        start=_require_date(data, "start"),
        end=_require_date(data, "end"),
    )


def _serialize_closure(closure: Closure) -> dict[str, Any]:
    return {
        "name": closure.name,
        "kind": closure.kind.value,
        "start": closure.start,
        "end": closure.end,
    }


def _validate_local_closures(
    closures: Iterable[Closure],
    year: str,
) -> None:
    closures = tuple(closures)
    if any(closure.kind is not ClosureKind.LOCAL for closure in closures):
        raise ValueError("Lokale Ausfalldateien dürfen nur lokale Ausfälle enthalten.")
    _validate_closures(closures, year)


def _validate_closures(
    closures: tuple[Closure, ...],
    year: str,
) -> None:
    if len(closures) != len(set(closures)):
        raise ValueError("Ein Ausfall darf nicht mehrfach eingetragen sein.")

    for closure in closures:
        _validate_dates_in_school_year(
            year,
            closure.start,
            closure.end,
            f"Der Ausfall '{closure.name}'",
        )


def _validate_dates_in_school_year(
    year: str,
    start: date,
    end: date,
    description: str,
) -> None:
    start_year = int(validate_school_year(year).split("-", maxsplit=1)[0])
    school_year_start = date(start_year, 8, 1)
    school_year_end = date(start_year + 1, 7, 31)
    if start < school_year_start or end > school_year_end:
        raise ValueError(
            f"{description} muss vollständig innerhalb des Schuljahres liegen."
        )


def _closure_sort_key(closure: Closure) -> tuple[date, date, str, str]:
    return closure.start, closure.end, closure.kind.value, closure.name


def _require_exact_keys(
    data: dict[str, Any],
    expected_keys: set[str],
    description: str,
) -> None:
    actual_keys = set(data)
    missing_keys = sorted(expected_keys - actual_keys)
    unexpected_keys = sorted(actual_keys - expected_keys)
    if not missing_keys and not unexpected_keys:
        return

    details = []
    if missing_keys:
        details.append(f"fehlend: {', '.join(missing_keys)}")
    if unexpected_keys:
        details.append(f"unbekannt: {', '.join(unexpected_keys)}")
    raise ValueError(
        f"{description} enthält ungültige Schlüssel ({'; '.join(details)})."
    )


def _require_list(data: dict[str, Any], key: str) -> list[Any]:
    value = data[key]
    if not isinstance(value, list):
        raise TypeError(f"'{key}' muss eine Liste sein.")
    return value


def _require_string(data: dict[str, Any], key: str) -> str:
    value = data[key]
    if not isinstance(value, str):
        raise TypeError(f"'{key}' muss ein Text sein.")
    return value


def _require_date(data: dict[str, Any], key: str) -> date:
    value = data[key]
    if type(value) is not date:
        raise TypeError(f"'{key}' muss ein TOML-Datum sein.")
    return value
