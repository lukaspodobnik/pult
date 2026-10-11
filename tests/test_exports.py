import asyncio
from datetime import date, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from pult.config import AppConfig
from pult.progress.queries.distribution import DistributionKind, DistributionRow
from pult.services.distribution_export import (
    distribution_html,
    export_distribution_plan,
)
from pult.services.document_rendering import DocumentRenderer
from pult.services.exports import export_path, save_pdf


def test_export_paths_are_stable_and_support_shared_overviews(tmp_path):
    assert (
        export_path(
            tmp_path,
            "2026-2027",
            "stoffverteilungsplan",
            school_class_id="7D",
            subject_id="mathematik",
        )
        == tmp_path / "exports/2026-2027/7D/stoffverteilungsplan-mathematik.pdf"
    )
    assert (
        export_path(tmp_path, "2026-2027", "stundenplan")
        == tmp_path / "exports/2026-2027/uebersichten/stundenplan.pdf"
    )
    for kwargs in ({"school_class_id": "../7D"}, {"subject_id": "../mathe"}):
        with pytest.raises(ValueError):
            export_path(tmp_path, "2026-2027", "stoffverteilungsplan", **kwargs)
    with pytest.raises(ValueError):
        export_path(tmp_path, "2026-2028", "stoffverteilungsplan")


def test_atomic_export_replaces_only_successful_pdf(tmp_path, monkeypatch):
    target = tmp_path / "exports/plan.pdf"
    save_pdf(target, b"%PDF-old")
    with pytest.raises(ValueError):
        save_pdf(target, b"not a PDF")
    assert target.read_bytes() == b"%PDF-old"
    original_replace = type(target).replace

    def fail_replace(self, destination):
        if destination == target:
            raise OSError("disk failure")
        return original_replace(self, destination)

    monkeypatch.setattr(type(target), "replace", fail_replace)
    with pytest.raises(OSError):
        save_pdf(target, b"%PDF-new")
    assert target.read_bytes() == b"%PDF-old"
    assert list(target.parent.iterdir()) == [target]
    monkeypatch.setattr(type(target), "replace", original_replace)
    save_pdf(target, b"%PDF-new")
    assert target.read_bytes() == b"%PDF-new"


def test_pdf_html_preserves_rows_and_escapes_all_user_content():
    rows = (
        DistributionRow(
            DistributionKind.SEQUENCE, date(2026, 10, 12), "Terme (ca. 12 Std.)"
        ),
        DistributionRow(
            DistributionKind.LESSON,
            date(2026, 10, 12),
            "<script> & Thema",
            "Computerraum",
            2,
        ),
        DistributionRow(
            DistributionKind.ASSESSMENT, date(2026, 10, 13), "SA · Terme", "08:00"
        ),
        DistributionRow(
            DistributionKind.CANCELLED,
            date(2026, 11, 18),
            "Unterricht entfällt",
            "Buß und Bettag",
        ),
        DistributionRow(DistributionKind.HOLIDAY, date(2026, 10, 26), "Herbstferien"),
    )
    document = distribution_html(
        rows,
        school_class_id="7D",
        subject_name="Mathe <b>",
        school_year="2026-2027",
        generated_at=datetime(2026, 10, 11, 14, 30),
    )
    assert "<script>" not in document and "&lt;script&gt; &amp; Thema" in document
    assert "Mathe &lt;b&gt;" in document
    assert "<td>2</td><td>Mo</td><td>12.10.2026</td>" in document
    assert "HERBSTFERIEN" in document and "Buß und Bettag" in document
    assert "Terme (ca. 12 Std.)" in document
    assert "Stand: 11.10.2026, 14:30" in document
    assert "A4 portrait" in document and "table-header-group" in document
    assert ".assessment td:nth-child(4)" in document


def test_failed_render_preserves_previous_export(tmp_path):
    config = AppConfig(tmp_path, "editor", "2026-2027", "source-sans-3")
    target = export_path(
        tmp_path,
        config.active_school_year,
        "stoffverteilungsplan",
        school_class_id="7D",
        subject_id="mathematik",
    )
    save_pdf(target, b"%PDF-old")
    renderer = SimpleNamespace(
        resolve_font=AsyncMock(return_value="source-sans-3"),
        render_pdf=AsyncMock(side_effect=RuntimeError("browser failure")),
    )
    with pytest.raises(RuntimeError):
        asyncio.run(
            export_distribution_plan(
                renderer,
                config,
                school_class_id="7D",
                subject_id="mathematik",
                subject_name="Mathematik",
                rows=(),
            )
        )
    assert target.read_bytes() == b"%PDF-old"


def test_pdf_renderer_waits_for_fonts_and_closes_page_on_failure(tmp_path):
    page = SimpleNamespace(
        route=AsyncMock(),
        emulate_media=AsyncMock(),
        set_content=AsyncMock(),
        evaluate=AsyncMock(),
        pdf=AsyncMock(return_value=b"%PDF-test"),
        close=AsyncMock(),
    )
    renderer = DocumentRenderer(tmp_path)
    renderer.browser = SimpleNamespace(new_page=AsyncMock(return_value=page))

    async def run():
        assert await renderer.render_pdf("<html>Test</html>") == b"%PDF-test"
        assert "document.fonts.ready" in page.evaluate.call_args.args[0]
        assert page.pdf.call_args.kwargs["display_header_footer"] is True
        assert page.pdf.call_args.kwargs["format"] == "A4"
        page.close.assert_awaited_once()
        page.pdf.side_effect = RuntimeError("print failed")
        with pytest.raises(RuntimeError):
            await renderer.render_pdf("<html>Test</html>")
        assert page.close.await_count == 2

    asyncio.run(run())
