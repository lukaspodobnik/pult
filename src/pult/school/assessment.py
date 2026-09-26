"""Geplante schriftliche Leistungsnachweise einer Klasse im Schuljahr."""

from dataclasses import dataclass
from datetime import date, time
from enum import StrEnum


class AssessmentKind(StrEnum):
    SCHOOL_EXAM = "sa"
    IMPROMPTU_TEST = "ex"
    ANNOUNCED_TEST = "akl"
    YEAR_GROUP_TEST = "jst"

    @property
    def abbreviation(self) -> str:
        return self.value.upper()

    @property
    def label(self) -> str:
        return {
            AssessmentKind.SCHOOL_EXAM: "Schulaufgabe",
            AssessmentKind.IMPROMPTU_TEST: "Stegreifaufgabe",
            AssessmentKind.ANNOUNCED_TEST: "Angekündigter kleiner Leistungsnachweis",
            AssessmentKind.YEAR_GROUP_TEST: "Jahrgangsstufentest",
        }[self]


@dataclass(frozen=True)
class Assessment:
    """Ein Termin; Klasse und Schuljahr ergeben sich aus dem Ablagekontext.

    ``occupied_periods`` enthält die Nummern der eigenen Unterrichtsstunden
    am angegebenen Datum, die vollständig belegt werden. Ein leerer Wert
    bezeichnet einen Termin ohne Verbrauch eigener Unterrichtsstunden.
    Die Dauer in Minuten bestimmt diese Zuordnung ausdrücklich nicht.

    ``group_id`` verbindet bei Bedarf Termine innerhalb derselben Klasse und
    desselben Fachs, etwa BMT und ergänzenden Test. Die Anrechnung auf eine
    Mindestzahl und eine etwaige Notengewichtung werden hier nicht festgelegt.
    Planung bedeutet bei einer Stegreifaufgabe keine Ankündigung an die Klasse.
    """

    id: str
    subject_id: str
    kind: AssessmentKind
    title: str
    date: date
    start: time
    duration_minutes: int
    occupied_periods: tuple[int, ...] = ()
    group_id: str | None = None

    def __post_init__(self) -> None:
        for field in ("id", "subject_id", "title", "group_id"):
            value = getattr(self, field)
            if field == "group_id" and value is None:
                continue
            if not isinstance(value, str):
                raise TypeError(f"{field} muss ein Text sein.")
            if not value.strip():
                raise ValueError(f"{field} darf nicht leer sein.")
            object.__setattr__(self, field, value.strip())

        if not isinstance(self.kind, AssessmentKind):
            raise TypeError("Die Art des Leistungsnachweises ist ungültig.")
        if type(self.date) is not date:
            raise TypeError("Der Termin muss ein Datum ohne Uhrzeit sein.")
        if not isinstance(self.start, time) or self.start.tzinfo is not None:
            raise TypeError("Der Beginn muss eine lokale Uhrzeit sein.")
        if type(self.duration_minutes) is not int or self.duration_minutes < 1:
            raise ValueError("Die Dauer muss eine positive ganze Minutenzahl sein.")
        if not isinstance(self.occupied_periods, tuple):
            raise TypeError("Die belegten Stunden müssen als Tupel angegeben werden.")
        if any(
            type(period) is not int or period < 1 for period in self.occupied_periods
        ):
            raise ValueError(
                "Belegte Stundennummern müssen positive ganze Zahlen sein."
            )
        if len(set(self.occupied_periods)) != len(self.occupied_periods):
            raise ValueError(
                "Eine Unterrichtsstunde darf nicht mehrfach belegt werden."
            )
