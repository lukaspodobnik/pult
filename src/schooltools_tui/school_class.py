from dataclasses import dataclass


@dataclass
class Class:
    id: str
    subjects_ids: list[str]
