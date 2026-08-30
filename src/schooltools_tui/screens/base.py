from typing import TYPE_CHECKING, Generic, TypeVar, cast

from textual.screen import Screen

from schooltools_tui.config import AppConfig

if TYPE_CHECKING:
    from schooltools_tui.app import SchooltoolsApp


ScreenResult = TypeVar("ScreenResult")

class SchooltoolsScreen(Screen[ScreenResult], Generic[ScreenResult]):

    @property
    def schooltools_app(self) -> "SchooltoolsApp":
        return cast("SchooltoolsApp", self.app)

    @property
    def app_config(self) -> AppConfig:
        return self.schooltools_app.require_config()
