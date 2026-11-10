# Copyright (C) 2026 Lukas Podobnik
# SPDX-License-Identifier: GPL-3.0-or-later
# See COPYRIGHT and SOURCES.md for scope and third-party notices.

import logging

logging.getLogger(__name__).addHandler(logging.NullHandler())


def main(argv: list[str] | None = None) -> None:
    import argparse
    import asyncio
    import sys

    from .services.diagnostics import (
        configure_logging,
        log_async_exception,
        log_directory,
        log_failure,
    )

    parser = argparse.ArgumentParser(
        prog="pult",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Lokaler Unterrichtsplaner für das Terminal.",
        epilog=f"Logdatei: {log_directory() / 'pult.log'} (mit drei älteren Dateien).",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Ausführliche Diagnose in die Logdatei schreiben.",
    )
    args = parser.parse_args(argv)
    session = configure_logging(debug=args.debug)
    logger = logging.getLogger(__name__)

    async def run() -> None:
        from .app import PultApp

        loop = asyncio.get_running_loop()
        previous_handler = loop.get_exception_handler()
        loop.set_exception_handler(log_async_exception)
        try:
            app = PultApp()
            try:
                await app.run_async()
            finally:
                await app.document_renderer.close()
        finally:
            loop.set_exception_handler(previous_handler)

    try:
        from .services.documents import material_rendering as graphics

        graphics.initialize_graphics()
        widget = graphics.image_widget()
        logger.info(
            "graphics_initialized mode=%s cell_width=%s cell_height=%s",
            widget.__name__ if widget is not None else "text",
            *graphics.CELL,
        )
        asyncio.run(run())
    except KeyboardInterrupt:
        logger.info("session_interrupted")
        raise
    except Exception as error:
        log_failure(logger, "application_failed", error)
        raise
    finally:
        session.close()
        if session.failed:
            print(
                f"PULT: Diagnoseprotokoll konnte nicht geschrieben werden: {session.path}",
                file=sys.stderr,
            )
