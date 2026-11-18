"""Lokale GGB-Dateien an die macOS Calculator Suite übergeben."""

import logging
import subprocess
from pathlib import Path

from pult.services.diagnostics import document_id

logger = logging.getLogger(__name__)

CALCULATOR_SUITE_ID = "org.geogebra.calculator.suite"
LAUNCH_TIMEOUT_SECONDS = 15


class GeoGebraOpenError(RuntimeError):
    """Ein Material konnte nicht an GeoGebra übergeben werden."""


def open_geogebra(path: Path) -> None:
    """Neue App-Instanz starten; die Originaldatei wird nur gelesen.

    Der Sandbox der Calculator Suite fehlt der Zugriff auf einen bloß als
    Argument übergebenen Dateipfad. macOS öffnet deshalb die Standardeingabe
    für die App, die den Inhalt über /dev/stdin als Konstruktion importiert.
    Die App-Kennung lässt Launch Services die installierte Suite finden.
    """
    path = path.resolve()
    identifier = document_id(path)
    try:
        with path.open("rb"):
            pass
    except OSError as error:
        logger.warning(
            "geogebra_launch_failed document=%s reason=file_unreadable exception=%s",
            identifier,
            type(error).__name__,
        )
        raise GeoGebraOpenError(
            "Die GeoGebra-Datei konnte nicht gelesen werden."
        ) from error

    logger.debug("geogebra_launch_requested document=%s", identifier)
    try:
        result = subprocess.run(
            [
                "/usr/bin/open",
                "-n",
                "-b",
                CALCULATOR_SUITE_ID,
                "--stdin",
                str(path),
                "--args",
                "/dev/stdin",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=LAUNCH_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        logger.warning("geogebra_launch_failed document=%s reason=timeout", identifier)
        raise GeoGebraOpenError(
            "Der Start von GeoGebra wurde nicht rechtzeitig bestätigt. "
            "Bitte prüfe, ob ein GeoGebra-Fenster geöffnet wurde."
        ) from error
    except OSError as error:
        logger.warning(
            "geogebra_launch_failed document=%s reason=launcher_failed exception=%s",
            identifier,
            type(error).__name__,
        )
        raise GeoGebraOpenError("GeoGebra konnte nicht gestartet werden.") from error

    if result.returncode:
        logger.warning(
            "geogebra_launch_failed document=%s reason=launch_rejected returncode=%s",
            identifier,
            result.returncode,
        )
        raise GeoGebraOpenError(
            "GeoGebra Calculator Suite konnte nicht gestartet werden. "
            "Bitte prüfe, ob die App installiert ist und sich öffnen lässt."
        )
    # open bestätigt nur den App-Start, nicht das Laden der Konstruktion.
    logger.debug("geogebra_launch_succeeded document=%s", identifier)
