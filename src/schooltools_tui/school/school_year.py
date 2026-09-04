from datetime import datetime
from zoneinfo import ZoneInfo


def get_school_year_options() -> list[tuple[str, str]]:
    now = datetime.now(ZoneInfo("Europe/Berlin"))
    start_year = now.year if now.month >= 8 else now.year - 1

    return [
        (f"{year}-{year + 1}", f"{year}-{year + 1}")
        for year in range(start_year - 1, start_year + 2)
    ]
