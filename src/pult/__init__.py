# Copyright (C) 2026 Lukas Podobnik
# SPDX-License-Identifier: GPL-3.0-or-later
# See COPYRIGHT and SOURCES.md for scope and third-party notices.


def main() -> None:
    from .services.documents.material_rendering import initialize_graphics

    initialize_graphics()
    import asyncio

    from .app import PultApp

    app = PultApp()

    async def run() -> None:
        try:
            await app.run_async()
        finally:
            await app.document_renderer.close()

    asyncio.run(run())
