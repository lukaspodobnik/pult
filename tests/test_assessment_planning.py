from dataclasses import replace
from datetime import date, time

from pult.school.assessment import Assessment, AssessmentKind
from pult.school.assessment_requirements import load_default_assessment_requirements
from pult.school.school_class import SchoolClass
from pult.services.assessment_planning import get_assessment_planning_gaps
from pult.services.assessments import ScopedAssessment


def test_gaps_include_empty_classes_and_ignore_conflicts_and_jst():
    classes = [
        SchoolClass("5A", 5, ["mathematik"]),
        SchoolClass("9A", 9, ["informatik-ntg"]),
    ]
    rules = load_default_assessment_requirements("2026-2027")
    gaps = get_assessment_planning_gaps(classes, rules, [], set())
    assert [(g.school_class_id, g.large, g.small) for g in gaps] == [
        ("5A", 4, 0),
        ("9A", 0, 2),
    ]
    ex = Assessment(
        "ex",
        "informatik-ntg",
        AssessmentKind.IMPROMPTU_TEST,
        "Test",
        date(2026, 10, 5),
        time(8),
        20,
    )
    entries = [
        ScopedAssessment("9A", ex, 1),
        ScopedAssessment(
            "9A", replace(ex, id="akl", kind=AssessmentKind.ANNOUNCED_TEST), 1
        ),
        ScopedAssessment(
            "9A", replace(ex, id="jst", kind=AssessmentKind.YEAR_GROUP_TEST), 1
        ),
    ]
    gaps = get_assessment_planning_gaps(classes, rules, entries, {("9A", "akl")})
    assert gaps[1].small == 1
    entries[1] = replace(
        entries[1], assessment=replace(entries[1].assessment, completed_on=ex.date)
    )
    assert (
        len(get_assessment_planning_gaps(classes, rules, entries, {("9A", "akl")})) == 1
    )
    restricted = [
        replace(rule, allowed_kinds=(AssessmentKind.IMPROMPTU_TEST,))
        if (rule.subject_id, rule.grade_level) == ("informatik-ntg", 9)
        else rule
        for rule in rules
    ]
    assert (
        get_assessment_planning_gaps(classes, restricted, entries, set())[1].small == 1
    )
    assert get_assessment_planning_gaps(classes, [], entries, set()) == []
