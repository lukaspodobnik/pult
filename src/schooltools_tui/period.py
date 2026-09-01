from dataclasses import dataclass
from datetime import time
from pathlib import Path
from typing import Any

from schooltools_tui.storage import load_toml, save_toml


class PeriodsFileError(ValueError):
    """Die Stundendetailsdatei hat ein ungültiges Format."""


PERIODS_FILE_NAME = Path("periods.toml")


@dataclass
class Period:
    number: int
    start: time
    end: time

    def __post_init__(self) -> None:
        if self.number < 1:
            raise ValueError("Die Stundennummer muss größer als 0 sein.")

        if self.start >= self.end:
            raise ValueError("Der Stundenbeginn muss vor dem Stundenende liegen.")


def load_periods(root: Path) -> list[Period]:
    data = load_toml(root / PERIODS_FILE_NAME)
    periods = data.get("periods")

    if not isinstance(periods, list):
        raise PeriodsFileError(
            "Die Stundendetailsdatei muss eine Liste 'periods' enthalten."
        )

    if len(periods) == 0:
        raise PeriodsFileError("Die Liste 'periods' darf nicht leer sein.")

    loaded_periods = [
        _load_period(period_data, index)
        for index, period_data in enumerate(periods, start=1)
    ]
    loaded_periods.sort(key=lambda period: period.number)
    _validate_periods(loaded_periods)
    return loaded_periods


def save_periods(root: Path, periods: list[Period]) -> None:
    if len(periods) == 0:
        raise ValueError("Es muss mindestens eine Unterrichtsstunde existieren.")

    sorted_periods = sorted(periods, key=lambda period: period.number)
    _validate_periods(sorted_periods)

    data: dict[str, Any] = {
        "periods": [
            {
                "number": period.number,
                "start": period.start.isoformat(timespec="minutes"),
                "end": period.end.isoformat(timespec="minutes"),
            }
            for period in sorted_periods
        ]
    }
    save_toml(root / PERIODS_FILE_NAME, data)


def get_period_at(periods: list[Period], current_time: time) -> Period | None:
    return next(
        (
            period
            for period in periods
            if period.start <= current_time < period.end
        ),
        None,
    )


def _load_period(period_data: object, index: int) -> Period:
    if not isinstance(period_data, dict):
        raise PeriodsFileError(
            f"Der Eintrag {index} in 'periods' muss eine Tabelle sein."
        )

    try:
        number = period_data["number"]
        start = _parse_time(period_data["start"])
        end = _parse_time(period_data["end"])

        if not isinstance(number, int) or isinstance(number, bool):
            raise TypeError

        return Period(number=number, start=start, end=end)
    except (KeyError, TypeError, ValueError) as error:
        raise PeriodsFileError(
            f"Der Eintrag {index} in 'periods' ist ungültig."
        ) from error


def _parse_time(value: object) -> time:
    if isinstance(value, time):
        return value

    if isinstance(value, str):
        return time.fromisoformat(value)

    raise TypeError("Eine Uhrzeit muss als TOML-Uhrzeit oder String angegeben sein.")


def _validate_periods(periods: list[Period]) -> None:
    numbers = [period.number for period in periods]
    if len(numbers) != len(set(numbers)):
        raise PeriodsFileError("Jede Stundennummer darf nur einmal vorkommen.")

    for previous, current in zip(periods, periods[1:]):
        if previous.end > current.start:
            raise PeriodsFileError("Unterrichtsstunden dürfen sich nicht überschneiden.")


