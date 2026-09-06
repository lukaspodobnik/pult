from typing import TYPE_CHECKING, TypeVar, cast

from textual.screen import ModalScreen, Screen

from schooltools_tui.config import AppConfig
from schooltools_tui.curriculum.sequence import Sequence

if TYPE_CHECKING:
    from schooltools_tui.app import SchooltoolsApp


ScreenResult = TypeVar("ScreenResult")


class SchooltoolsScreen(Screen[ScreenResult]):
    @property
    def schooltools_app(self) -> "SchooltoolsApp":
        return cast("SchooltoolsApp", self.app)

    @property
    def app_config(self) -> AppConfig:
        return self.schooltools_app.require_config()

    @property
    def sequence_library(self) -> list[Sequence]:
        return self.schooltools_app.require_sequence_library().get_sequences()


class SchooltoolsModalScreen(ModalScreen[ScreenResult]):
    @property
    def schooltools_app(self) -> "SchooltoolsApp":
        return cast("SchooltoolsApp", self.app)

    @property
    def app_config(self) -> AppConfig:
        return self.schooltools_app.require_config()

    @property
    def sequence_library(self) -> list[Sequence]:
        return self.schooltools_app.require_sequence_library().get_sequences()
