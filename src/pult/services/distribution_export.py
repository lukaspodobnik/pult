"""PDF-Export derselben Zeilen, die auch die Stoffverteilungsansicht zeigt."""

from datetime import datetime
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo

from pult.config import AppConfig
from pult.presentation import format_compact_date, format_school_year
from pult.progress.queries.distribution import DistributionKind, DistributionRow
from pult.services.document_rendering import DocumentRenderer
from pult.services.exports import export_path, pdf_stylesheet, save_pdf


def distribution_html(
    rows: tuple[DistributionRow, ...],
    *,
    school_class_id: str,
    subject_name: str,
    school_year: str,
    generated_at: datetime,
    font: str = "source-sans-3",
) -> str:
    body = []
    for row in rows:
        if row.kind in {DistributionKind.SEQUENCE, DistributionKind.HOLIDAY}:
            title = (
                row.title.upper() if row.kind == DistributionKind.HOLIDAY else row.title
            )
            body.append(
                f'<tr class="{row.kind.value}"><td colspan="4">{escape(title)}</td></tr>'
            )
        else:
            cells = (
                str(row.number) if row.number is not None else "",
                format_compact_date(row.date),
                row.title,
                row.notes,
            )
            rendered_cells = [escape(cell) for cell in cells]
            weekday, _, numeric_date = cells[1].partition(" ")
            rendered_cells[1] = (
                f'<span class="date-weekday">{escape(weekday)}</span> '
                f'<span class="date-number">{escape(numeric_date)}</span>'
            )
            body.append(
                f'<tr class="{row.kind.value}">'
                + "".join(f"<td>{cell}</td>" for cell in rendered_cells)
                + "</tr>"
            )
    if not rows:
        body.append('<tr><td colspan="4">Keine Unterrichtstermine vorhanden.</td></tr>')
    heading = f"{escape(school_class_id)} · {escape(subject_name)}"
    return f"""<!doctype html><html lang="de"><head><meta charset="utf-8">
<title>Stoffverteilungsplan · {heading}</title><style>
{pdf_stylesheet(font)}
@page {{ size:A4 portrait; }}
table {{ width:100%; border-collapse:collapse; table-layout:fixed; font-size:9pt; }}
thead {{ display:table-header-group; }}
th {{ font-weight:600; text-align:left; white-space:nowrap; border-bottom:1px solid #82909b; }}
td,th {{ padding:1.8mm 1mm; vertical-align:top; overflow-wrap:anywhere; }}
td {{ border-bottom:.2mm solid #e2e5e8; }}
tbody tr:not(.sequence):not(.holiday) td {{ padding-top:1.1mm; padding-bottom:1.1mm; }}
tbody tr:not(.sequence):not(.holiday) td:first-child {{ font-weight:500; }}
th:nth-child(n+2),td:nth-child(n+2) {{ border-left:.2mm solid #c5cdd4; padding-left:2mm; }}
td:nth-child(2) {{ white-space:nowrap; }}
.date-weekday {{ display:inline-block; width:1.8em; }}
.date-number {{ font-variant-numeric:tabular-nums; font-kerning:none; }}
tr {{ break-inside:avoid; }}
.sequence,.holiday {{ font-weight:600; break-after:avoid; text-align:center; }}
.sequence td {{ background:#e6edf3; }}
.holiday td {{ background:#eeece4; }}
.assessment td:nth-child(3) {{ background:#f4e3ca; font-weight:600; }}
td:nth-child(4) {{ color:#59616a; }}
</style></head><body><h1>Stoffverteilungsplan</h1>
<p class="meta">{heading} · Schuljahr {escape(format_school_year(school_year))}<br>
Stand: {generated_at.strftime("%d.%m.%Y, %H:%M")}</p>
<table><colgroup><col style="width:6mm"><col style="width:25mm">
<col style="width:60%"><col></colgroup>
<thead><tr><th>Nr</th><th>Datum</th><th>Stundenthema</th><th>Anmerkungen</th></tr></thead>
<tbody>{"".join(body)}</tbody></table></body></html>"""


async def export_distribution_plan(
    renderer: DocumentRenderer,
    config: AppConfig,
    *,
    school_class_id: str,
    subject_id: str,
    subject_name: str,
    rows: tuple[DistributionRow, ...],
) -> Path:
    target = export_path(
        config.root,
        config.active_school_year,
        "stoffverteilungsplan",
        school_class_id=school_class_id,
        subject_id=subject_id,
    )
    font = await renderer.resolve_font(config.document_font)
    document = distribution_html(
        rows,
        school_class_id=school_class_id,
        subject_name=subject_name,
        school_year=config.active_school_year,
        generated_at=datetime.now(ZoneInfo("Europe/Berlin")),
        font=font,
    )
    content = await renderer.render_pdf(document, font=font)
    return save_pdf(target, content)
