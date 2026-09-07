import asyncio
from dataclasses import replace

from test_ui_integration import prepare_root

from schooltools_tui.app import SchooltoolsApp
from schooltools_tui.initialization.school_class import initialize_school_class
from schooltools_tui.progress.class_progress import (
    load_class_progress,
    save_class_progress,
)
from schooltools_tui.school.school_class import SchoolClass, save_school_class
from schooltools_tui.school.subject import load_subjects
from schooltools_tui.widgets.navigation import ViewPicker


def test_class_subject_options_and_selection_survive_refresh(tmp_path, monkeypatch):
    config = prepare_root(tmp_path)
    school_class = SchoolClass("9B-NTG", 9, ["mathematik", "informatik-ntg"])
    initialize_school_class(tmp_path, config.active_school_year, school_class)
    monkeypatch.setattr("schooltools_tui.app.load_app_config", lambda: config)
    subjects = {s.id: s for s in load_subjects(tmp_path)}

    async def run():
        app = SchooltoolsApp()
        async with app.run_test(size=(140, 42)) as pilot:
            await pilot.pause(0.3)
            screen = app.screen
            picker = screen.query_one(ViewPicker)

            async def settled():
                for _ in range(40):
                    await pilot.pause(0.05)
                    if screen._pending_view_id is None:
                        return
                raise AssertionError("Ansichtswechsel wurde nicht abgeschlossen")

            await settled()
            assert picker.option_count == 4
            assert picker.get_option_at_index(0).id == "home"
            assert (
                str(picker.get_option_at_index(1).prompt)
                == "5A     · " + subjects["mathematik"].short_name
            )
            assert {
                str(picker.get_option_at_index(index).prompt).index("·")
                for index in range(1, picker.option_count)
            } == {7}
            picker.focus()
            await pilot.press("down")
            await settled()
            assert picker.highlighted == 1
            await pilot.press("up")
            await settled()
            assert picker.highlighted == 0
            assert list(picker.class_subjects_by_option_id.values()) == [
                ("5A", "mathematik"),
                ("9B-NTG", "informatik-ntg"),
                ("9B-NTG", "mathematik"),
            ]
            picker.highlighted = 2
            await settled()
            assert screen.active_school_class_id == "9B-NTG"
            assert screen.active_subject_id == "informatik-ntg"
            option_id = picker.get_option_at_index(2).id
            screen.refresh_view_picker()
            await settled()
            assert picker.get_option_at_index(picker.highlighted).id == option_id
            assert screen.active_subject_id == "informatik-ntg"
            await screen.refresh_current_view()
            assert screen.active_subject_id == "informatik-ntg"

            picker.highlighted = 3
            await settled()
            assert screen.active_subject_id == "mathematik"
            picker.highlighted = 2
            await settled()
            save_school_class(
                tmp_path,
                config.active_school_year,
                SchoolClass("9B-NTG", 9, ["mathematik"]),
            )
            progress = load_class_progress(
                tmp_path, config.active_school_year, "9B-NTG"
            )
            save_class_progress(
                tmp_path,
                config.active_school_year,
                "9B-NTG",
                replace(
                    progress,
                    active_sequences=tuple(
                        s
                        for s in progress.active_sequences
                        if s.subject_id == "mathematik"
                    ),
                ),
            )
            screen.refresh_view_picker()
            await settled()
            assert picker.highlighted == 0
            assert screen.active_school_class_id is None
            assert screen.active_subject_id is None

    asyncio.run(run())
