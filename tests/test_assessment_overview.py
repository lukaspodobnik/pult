from dataclasses import replace
from datetime import date, datetime, time

from test_ui_integration import prepare_root

from pult.progress.queries.dashboard import assessment_count, get_home_dashboard_summary
from pult.school.assessment import Assessment, AssessmentKind, save_assessments
from pult.school.assessment_requirements import (
    AssessmentCategory,
    load_assessment_requirements,
)
from pult.school.period import load_periods
from pult.services.assessments import complete_assessment, reopen_assessment
from pult.services.progress import load_planning_data


def test_overview_completion_undo_and_jst_exclusion(tmp_path):
    config = prepare_root(tmp_path)
    entry = Assessment(
        "sa",
        "mathematik",
        AssessmentKind.SCHOOL_EXAM,
        "Test",
        date(2026, 10, 5),
        time(8),
        45,
        group_id="shared",
    )
    jst = replace(
        entry, id="jst", kind=AssessmentKind.YEAR_GROUP_TEST, date=date(2026, 9, 22)
    )
    save_assessments(tmp_path, config.active_school_year, "5A", [entry, jst])

    def overview():
        data = load_planning_data(config)
        return get_home_dashboard_summary(
            datetime(2026, 9, 22),
            data.progresses_by_class_id,
            data.sequences,
            data.timetable_entries,
            load_periods(tmp_path),
            data.school_classes,
            data.school_calendar,
            data.school_closures,
            data.class_closures_by_class_id,
            data.assessments_by_class_id,
            load_assessment_requirements(tmp_path, config.active_school_year),
        ).class_balances[0]

    assert overview().next_assessment.assessment.id == "sa"
    assert overview().large_assessments.label == "0/4"
    assert overview().small_assessments.label == "0"
    complete_assessment(config, "5A", "jst")
    assert overview().large_assessments.label == "0/4"
    assert overview().small_assessments.label == "0"
    complete_assessment(config, "5A", "sa")
    assert overview().large_assessments.label == "1/4"
    assert overview().next_assessment is None
    reopen_assessment(config, "5A", "sa")
    assert overview().large_assessments.label == "0/4"
    assert overview().next_assessment.assessment.id == "sa"


def test_small_counts_combine_kinds_ignore_groups_and_other_subjects(tmp_path):
    config = prepare_root(tmp_path)
    rules = load_assessment_requirements(tmp_path, config.active_school_year)
    ex = Assessment(
        "ex",
        "informatik-ntg",
        AssessmentKind.IMPROMPTU_TEST,
        "Test",
        date(2026, 10, 5),
        time(8),
        20,
        completed_on=date(2026, 10, 5),
        group_id="same",
    )
    entries = [
        ex,
        replace(ex, id="akl", kind=AssessmentKind.ANNOUNCED_TEST),
        replace(ex, id="ex2"),
        replace(ex, id="jst", kind=AssessmentKind.YEAR_GROUP_TEST),
        replace(ex, id="planned", completed_on=None),
        replace(ex, id="math", subject_id="mathematik"),
    ]
    assert (
        assessment_count(
            "informatik-ntg", 9, AssessmentCategory.SMALL_WRITTEN, entries, rules
        ).label
        == "3/2"
    )
    assert (
        assessment_count(
            "informatik-ntg", 9, AssessmentCategory.LARGE_WRITTEN, entries, rules
        ).label
        == "—"
    )
    assert (
        assessment_count(
            "mathematik", 5, AssessmentCategory.SMALL_WRITTEN, entries, rules
        ).label
        == "1"
    )
