"""Druckbare Wochenübersicht des verwalteten Stundenplans."""

from collections.abc import Mapping
from datetime import datetime
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo

from pult.config import AppConfig
from pult.presentation import WEEKDAYS, format_school_year
from pult.school.period import Period
from pult.school.timetable import TimetableEntry
from pult.services.documents.document_rendering import DocumentRenderer
from pult.services.exports.common import export_path, pdf_stylesheet, save_pdf


def timetable_html(
    entries: tuple[TimetableEntry, ...],
    periods: tuple[Period, ...],
    subject_labels: Mapping[str, str],
    *,
    school_year: str,
    generated_at: datetime,
    font: str = "source-sans-3",
) -> str:
    slots = {(entry.weekday, entry.period): entry for entry in entries}
    rows = []
    for period in periods:
        cells = []
        for weekday, _ in WEEKDAYS:
            entry = slots.get((weekday, period.number))
            if entry is None:
                cells.append('<td class="empty"></td>')
                continue
            subject = subject_labels.get(entry.subject_id, entry.subject_id)
            label = escape(f"{entry.school_class_id} · {subject}")
            room = f'<div class="room">{escape(entry.room)}</div>' if entry.room else ""
            cells.append(f'<td><div class="lesson">{label}</div>{room}</td>')
        rows.append(
            '<tr><th scope="row">'
            f'<div class="period">{period.number}. Stunde</div>'
            f'<div class="time">{period.start:%H:%M}–{period.end:%H:%M}</div>'
            "</th>" + "".join(cells) + "</tr>"
        )
    if not periods:
        rows.append('<tr><td colspan="6">Keine Stundenzeiten konfiguriert.</td></tr>')
    headings = "".join(f'<th scope="col">{escape(label)}</th>' for _, label in WEEKDAYS)
    return f"""<!doctype html><html lang="de"><head><meta charset="utf-8">
<title>Stundenplan · {escape(format_school_year(school_year))}</title><style>
{pdf_stylesheet(font)}
@page {{ size:A4 landscape; }}
table {{ width:100%; border-collapse:collapse; table-layout:fixed; }}
thead {{ display:table-header-group; }}
tr {{ break-inside:avoid; }}
td,th {{ text-align:center; vertical-align:middle; overflow-wrap:anywhere; }}
thead th {{ padding:2.5mm 2mm; font-weight:600; background:#e6edf3;
    border-bottom:.3mm solid #82909b; }}
tbody td,tbody th {{ height:10mm; padding:1mm 2mm;
    border-bottom:.2mm solid #dce1e5; }}
td+td,th+td,thead th+th {{ border-left:.2mm solid #dce1e5; }}
tbody th {{ background:#f4f6f8; }}
.period {{ font-size:10pt; font-weight:500; }}
.time {{ font-size:8.5pt; font-weight:400; color:#59616a;
    font-variant-numeric:tabular-nums; white-space:nowrap; }}
.lesson {{ font-size:11pt; font-weight:600; }}
.room {{ font-size:8.5pt; color:#59616a; margin-top:.5mm; }}
</style></head><body><h1>Stundenplan</h1>
<p class="meta">Schuljahr {escape(format_school_year(school_year))} ·
Stand: {generated_at.strftime("%d.%m.%Y, %H:%M")}</p>
<table><colgroup><col style="width:27mm"><col span="5"></colgroup>
<thead><tr><th scope="col">Stunde</th>{headings}</tr></thead>
<tbody>{"".join(rows)}</tbody></table></body></html>"""


async def export_timetable(
    renderer: DocumentRenderer,
    config: AppConfig,
    *,
    entries: tuple[TimetableEntry, ...],
    periods: tuple[Period, ...],
    subject_labels: Mapping[str, str],
) -> Path:
    target = export_path(config.root, config.active_school_year, "stundenplan")
    font = await renderer.resolve_font(config.document_font)
    document = timetable_html(
        entries,
        periods,
        subject_labels,
        school_year=config.active_school_year,
        generated_at=datetime.now(ZoneInfo("Europe/Berlin")),
        font=font,
    )
    return save_pdf(target, await renderer.render_pdf(document, font=font))
