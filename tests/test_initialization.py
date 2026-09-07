import pytest

from pult.config import AppConfig
from pult.curriculum.sequence import load_sequence_library
from pult.initialization.pult import (
    SetupError,
    initialize_pult,
)
from pult.initialization.school_class import (
    SchoolClassSetupError,
    initialize_school_class,
)
from pult.initialization.school_year import initialize_school_year
from pult.progress.class_progress import load_class_progress
from pult.school.calendar import (
    get_class_closures_path,
    get_school_closures_path,
    load_class_closures,
    load_school_closures,
)
from pult.school.school_class import SchoolClass, get_school_class_path
from pult.school.timetable import get_timetable_path, load_timetable


def test_full_initialization_copies_defaults_without_real_config(tmp_path, monkeypatch):
    saved = []
    monkeypatch.setattr(
        "pult.initialization.pult.save_app_config",
        saved.append,
    )

    config = initialize_pult(str(tmp_path), "nvim", "2026-2027")

    assert config == AppConfig(tmp_path, "nvim", "2026-2027")
    assert saved == [config]
    assert (tmp_path / "subjects.toml").is_file()
    assert (tmp_path / "periods.toml").is_file()
    assert (tmp_path / "calendars" / "2026-2027.toml").is_file()
    assert len(load_sequence_library(tmp_path)) > 100
    assert load_timetable(get_timetable_path(tmp_path, "2026-2027")) == []
    assert load_school_closures(tmp_path, "2026-2027") == []


def test_initialization_preserves_existing_default_file(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "pult.initialization.pult.save_app_config",
        lambda config: None,
    )
    marker = "[[subjects]]\nid = 'custom'\n"
    (tmp_path / "subjects.toml").write_text(marker)
    initialize_pult(str(tmp_path), "nvim", "2026-2027")
    assert (tmp_path / "subjects.toml").read_text() == marker


def test_school_year_requires_existing_calendar(tmp_path):
    with pytest.raises(FileNotFoundError):
        initialize_school_year(tmp_path, "2026-2027")


def test_school_year_initialization_is_idempotent(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "pult.initialization.pult.save_app_config",
        lambda config: None,
    )
    initialize_pult(str(tmp_path), "nvim", "2026-2027")
    initialize_school_year(tmp_path, "2026-2027")
    assert get_school_closures_path(tmp_path, "2026-2027").is_file()


@pytest.mark.parametrize("reuse_library", [False, True])
def test_class_initialization_creates_all_class_files(
    tmp_path, monkeypatch, reuse_library
):
    monkeypatch.setattr(
        "pult.initialization.pult.save_app_config",
        lambda config: None,
    )
    initialize_pult(str(tmp_path), "nvim", "2026-2027")
    school_class = SchoolClass("5A", 5, ["mathematik"])
    sequences = load_sequence_library(tmp_path) if reuse_library else None
    if reuse_library:

        def unexpected_load(root):
            pytest.fail("Die übergebene Bibliothek muss wiederverwendet werden.")

        monkeypatch.setattr(
            "pult.initialization.school_class.load_sequence_library",
            unexpected_load,
        )
    initialize_school_class(tmp_path, "2026-2027", school_class, sequences=sequences)

    assert get_school_class_path(tmp_path, "2026-2027", "5A").is_file()
    assert get_class_closures_path(tmp_path, "2026-2027", "5A").is_file()
    assert load_class_closures(tmp_path, "2026-2027", "5A") == []
    progress = load_class_progress(tmp_path, "2026-2027", "5A")
    assert progress.active_sequences[0].subject_id == "mathematik"


def test_duplicate_class_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "pult.initialization.pult.save_app_config",
        lambda config: None,
    )
    initialize_pult(str(tmp_path), "nvim", "2026-2027")
    school_class = SchoolClass("5A", 5, ["mathematik"])
    initialize_school_class(tmp_path, "2026-2027", school_class)
    with pytest.raises(SchoolClassSetupError):
        initialize_school_class(tmp_path, "2026-2027", school_class)


def test_illegal_subject_for_grade_is_rejected(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "pult.initialization.pult.save_app_config",
        lambda config: None,
    )
    initialize_pult(str(tmp_path), "nvim", "2026-2027")
    with pytest.raises(SchoolClassSetupError):
        initialize_school_class(
            tmp_path,
            "2026-2027",
            SchoolClass("5A", 5, ["informatik-ntg"]),
        )


@pytest.mark.parametrize(
    "root, editor, year",
    [("", "nvim", "2026-2027"), ("x", "", "2026-2027"), ("x", "nvim", "")],
)
def test_setup_requires_all_values(tmp_path, monkeypatch, root, editor, year):
    monkeypatch.setattr(
        "pult.initialization.pult.save_app_config",
        lambda config: None,
    )
    actual_root = root if not root else str(tmp_path / root)
    with pytest.raises(SetupError):
        initialize_pult(actual_root, editor, year)
