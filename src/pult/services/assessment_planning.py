"""Fehlende Jahresplanung anhand der erlaubten, konfliktfreien LNWs."""

from collections import Counter
from dataclasses import dataclass

from pult.school.assessment_requirements import (
    AssessmentCategory,
    AssessmentRequirement,
    assessment_category,
)
from pult.school.school_class import SchoolClass
from pult.services.assessments import ScopedAssessment


@dataclass(frozen=True)
class AssessmentPlanningGap:
    school_class_id: str
    subject_id: str
    large: int
    small: int


def get_assessment_planning_gaps(
    classes: list[SchoolClass],
    requirements: list[AssessmentRequirement],
    entries: list[ScopedAssessment],
    conflicting: set[tuple[str, str]],
) -> list[AssessmentPlanningGap]:
    rules = {(rule.subject_id, rule.grade_level): rule for rule in requirements}
    result = []
    for school_class in sorted(classes, key=lambda item: (item.grade_level, item.id)):
        for subject_id in school_class.subject_ids:
            rule = rules.get((subject_id, school_class.grade_level))
            if rule is None:
                continue
            counts = Counter(
                assessment_category(item.assessment.kind)
                for item in entries
                if item.school_class_id == school_class.id
                and item.assessment.subject_id == subject_id
                and item.assessment.kind in rule.allowed_kinds
                and (
                    item.assessment.completed_on is not None
                    or (item.school_class_id, item.assessment.id) not in conflicting
                )
            )
            large = max(
                0,
                (rule.minimum_for(AssessmentCategory.LARGE_WRITTEN) or 0)
                - counts[AssessmentCategory.LARGE_WRITTEN],
            )
            small = max(
                0,
                (rule.minimum_for(AssessmentCategory.SMALL_WRITTEN) or 0)
                - counts[AssessmentCategory.SMALL_WRITTEN],
            )
            if large or small:
                result.append(
                    AssessmentPlanningGap(school_class.id, subject_id, large, small)
                )
    return result
