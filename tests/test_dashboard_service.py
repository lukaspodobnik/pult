import pytest
from test_ui_integration import prepare_root

from pult.initialization.school_class import initialize_school_class
from pult.school.school_class import SchoolClass
from pult.services.dashboard import load_school_class_view_data


@pytest.fixture
def config(tmp_path):
    config = prepare_root(tmp_path)
    initialize_school_class(
        tmp_path,
        config.active_school_year,
        SchoolClass("9B", 9, ["mathematik", "informatik-ntg"]),
    )
    return config


@pytest.mark.parametrize(
    "subject_id, preferred_subject_id, expected_subject_id",
    [
        ("mathematik", "informatik-ntg", "mathematik"),
        (None, "informatik-ntg", "informatik-ntg"),
        (None, "nicht-mehr-vorhanden", "mathematik"),
    ],
)
def test_class_data_respects_subject_selection(
    config, subject_id, preferred_subject_id, expected_subject_id
):
    data = load_school_class_view_data(
        config, "9B", subject_id, preferred_subject_id=preferred_subject_id
    )

    assert data.school_class.id == "9B"
    assert data.subject_id == expected_subject_id
    assert [summary.subject_id for summary in data.progress_summaries] == [
        expected_subject_id
    ]


def test_class_data_rejects_invalid_explicit_subject(config):
    with pytest.raises(ValueError, match="Das ausgewählte Fach gehört nicht"):
        load_school_class_view_data(
            config, "5A", "informatik-ntg", preferred_subject_id="mathematik"
        )
