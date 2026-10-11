from pathlib import Path

import pytest

from pult.curriculum.material import save_markdown
from pult.services.exports import save_pdf
from pult.storage import load_csv, save_csv, save_toml


@pytest.mark.parametrize("format", ["toml", "csv", "markdown", "pdf"])
@pytest.mark.parametrize("failure", ["flush", "replace"])
def test_failed_save_preserves_existing_file_and_removes_temporary_file(
    tmp_path, monkeypatch, format, failure
):
    target = tmp_path / f"document.{format}"
    target.write_bytes(b"previous content")

    def fail(*args):
        raise OSError("disk failure")

    if failure == "flush":
        monkeypatch.setattr("pult.storage.os.fsync", fail)
    else:
        monkeypatch.setattr(Path, "replace", fail)

    with pytest.raises(OSError, match="disk failure"):
        if format == "toml":
            save_toml(target, {"titel": "Neue Stunde"})
        elif format == "csv":
            save_csv(target, ("room",), [{"room": "Übungsraum"}])
        elif format == "markdown":
            save_markdown(target, "# Neue Vorbereitung\n")
        else:
            save_pdf(target, b"%PDF-new")

    assert target.read_bytes() == b"previous content"
    assert list(tmp_path.iterdir()) == [target]


def test_csv_serialization_failure_preserves_existing_timetable(tmp_path):
    target = tmp_path / "timetable.csv"
    save_csv(target, ("room",), [{"room": "Pausenhof"}])
    original = target.read_bytes()

    def incomplete_rows():
        yield {"room": "Computerraum"}
        raise ValueError("invalid row")

    with pytest.raises(ValueError, match="invalid row"):
        save_csv(target, ("room",), incomplete_rows())
    assert target.read_bytes() == original
    assert list(tmp_path.iterdir()) == [target]


def test_csv_roundtrip_preserves_unicode_quotes_and_line_breaks(tmp_path):
    target = tmp_path / "timetable.csv"
    rows = [{"room": 'Übungsraum, "A"\n1. Stock'}]
    save_csv(target, ("room",), rows)
    assert load_csv(target) == rows
    assert target.read_bytes() == 'room\r\n"Übungsraum, ""A""\n1. Stock"\r\n'.encode()
