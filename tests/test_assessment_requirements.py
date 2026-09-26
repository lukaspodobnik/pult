from dataclasses import replace

import pytest
from test_ui_integration import prepare_root

from pult.initialization.school_year import initialize_school_year
from pult.school.assessment import AssessmentKind
from pult.school.assessment_requirements import (
    AssessmentCategory,
    AssessmentMinimum,
    AssessmentRequirement,
    AssessmentRequirementsFileError,
    assessment_category,
    get_assessment_requirements_path,
    initialize_assessment_requirements,
    load_assessment_requirements,
    load_default_assessment_requirements,
    save_assessment_requirements,
)
from pult.school.subject import load_subjects
from pult.services.settings import update_settings

LARGE = AssessmentCategory.LARGE_WRITTEN
SMALL = AssessmentCategory.SMALL_WRITTEN
YEAR = "2026-2027"


def test_defaults_cover_subjects_and_exclude_year_group_tests(tmp_path):
    prepare_root(tmp_path)
    entries = load_assessment_requirements(tmp_path, YEAR)
    by_key = {(entry.subject_id, entry.grade_level): entry for entry in entries}
    for subject in load_subjects(tmp_path):
        for grade in subject.grade_levels:
            assert (subject.id, grade) in by_key
    for grade, count in [(5, 4), (7, 4), (8, 3), (9, 3), (11, 3), (12, 2), (13, 2)]:
        entry = by_key["mathematik", grade]
        assert entry.minimum_for(LARGE) == count
        assert entry.minimum_for(SMALL) is None
    entry = by_key["informatik-ntg", 9]
    assert AssessmentKind.SCHOOL_EXAM not in entry.allowed_kinds
    assert entry.minimum_for(LARGE) is None
    assert entry.minimum_for(SMALL) == 2
    assert (
        by_key["informatik-grundlegendes-anforderungsniveau", 13].minimum_for(LARGE)
        == 1
    )
    assert (
        by_key["informatik-grundlegendes-anforderungsniveau", 13].minimum_for(SMALL)
        == 1
    )
    assert by_key["informatik-erhoehtes-anforderungsniveau", 13].minimum_for(LARGE) == 2
    assert assessment_category(AssessmentKind.YEAR_GROUP_TEST) is None
    assert assessment_category(AssessmentKind.SCHOOL_EXAM) == LARGE
    assert assessment_category(AssessmentKind.IMPROMPTU_TEST) == SMALL
    assert assessment_category(AssessmentKind.ANNOUNCED_TEST) == SMALL
    old = next(
        entry
        for entry in load_default_assessment_requirements("2025-2026")
        if (entry.subject_id, entry.grade_level) == ("mathematik", 9)
    )
    assert old.minimum_for(LARGE) == 4


def test_year_switch_copies_custom_values_and_preserves_both_years(
    tmp_path, monkeypatch
):
    config = prepare_root(tmp_path)
    monkeypatch.setattr("pult.services.settings.save_app_config", lambda config: None)
    original = load_assessment_requirements(tmp_path, YEAR)
    customized = [
        replace(entry, minimums=(AssessmentMinimum(SMALL, 3),))
        if entry.subject_id == "informatik-ntg"
        else entry
        for entry in original
    ]
    save_assessment_requirements(tmp_path, YEAR, customized)
    before = get_assessment_requirements_path(tmp_path, YEAR).read_bytes()
    update_settings(config, "nano", "2027-2028")
    assert load_assessment_requirements(tmp_path, "2027-2028") == customized
    save_assessment_requirements(tmp_path, "2027-2028", [])
    initialize_school_year(tmp_path, "2027-2028")
    assert load_assessment_requirements(tmp_path, "2027-2028") == []
    assert get_assessment_requirements_path(tmp_path, YEAR).read_bytes() == before
    # Eine absichtlich leere Konfiguration wird ebenfalls übernommen.
    path = get_assessment_requirements_path(tmp_path, "2028-2029")
    path.parent.mkdir()
    initialize_assessment_requirements(tmp_path, "2028-2029")
    assert load_assessment_requirements(tmp_path, "2028-2029") == []


def test_missing_file_reads_without_writing_and_never_inherits_future(tmp_path):
    future = get_assessment_requirements_path(tmp_path, "2027-2028")
    future.parent.mkdir(parents=True)
    save_assessment_requirements(tmp_path, "2027-2028", [])
    assert load_assessment_requirements(
        tmp_path, YEAR
    ) == load_default_assessment_requirements(YEAR)
    assert not get_assessment_requirements_path(tmp_path, YEAR).exists()


def test_roundtrip_distinguishes_zero_from_unset_and_validates_before_save(tmp_path):
    path = get_assessment_requirements_path(tmp_path, YEAR)
    path.parent.mkdir(parents=True)
    entry = AssessmentRequirement(
        "mathematik", 5, (AssessmentKind.SCHOOL_EXAM,), (AssessmentMinimum(LARGE, 0),)
    )
    save_assessment_requirements(tmp_path, YEAR, [entry])
    assert load_assessment_requirements(tmp_path, YEAR) == [entry]
    assert entry.minimum_for(LARGE) == 0
    assert entry.minimum_for(SMALL) is None
    before = path.read_bytes()
    with pytest.raises(AssessmentRequirementsFileError, match="Doppelte"):
        save_assessment_requirements(tmp_path, YEAR, [entry, entry])
    assert path.read_bytes() == before
    with pytest.raises(ValueError, match="positive Mindestzahl"):
        replace(entry, allowed_kinds=(), minimums=(AssessmentMinimum(LARGE, 1),))
    with pytest.raises(ValueError, match="Kategorie"):
        replace(
            entry, minimums=(AssessmentMinimum(LARGE, 0), AssessmentMinimum(LARGE, 1))
        )


@pytest.mark.parametrize("count", [-1, True, 1.5, "2"])
def test_invalid_minimum(count):
    with pytest.raises(ValueError):
        AssessmentMinimum(SMALL, count)


@pytest.mark.parametrize(
    "content",
    [
        "broken = [",
        "requirements = false",
        '[[requirements]]\nsubject_id="mathematik"\ngrade_level=true\nallowed_kinds=["sa"]',
        '[[requirements]]\nsubject_id="mathematik"\ngrade_level=5\nallowed_kinds=["unknown"]',
        '[[requirements]]\nsubject_id="mathematik"\ngrade_level=5\nallowed_kinds=["sa"]\nminimums={small_writen=2}',
    ],
)
def test_invalid_file_is_not_hidden_by_fallback_or_copied(tmp_path, content):
    path = get_assessment_requirements_path(tmp_path, YEAR)
    path.parent.mkdir(parents=True)
    path.write_text(content)
    with pytest.raises(
        AssessmentRequirementsFileError, match="assessment-requirements.toml"
    ):
        load_assessment_requirements(tmp_path, YEAR)
    target = get_assessment_requirements_path(tmp_path, "2027-2028")
    target.parent.mkdir()
    with pytest.raises(AssessmentRequirementsFileError):
        initialize_assessment_requirements(tmp_path, "2027-2028")
    assert not target.exists()
    assert path.read_text() == content
