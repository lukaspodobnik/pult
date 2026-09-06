# Code, Formatierung und Typen prüfen, danach Tests ausführen.
check:
    uv run ruff check .
    uv run ruff format --check .
    uv run pyright
    uv run pytest
