import asyncio
import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from pult.services.documents import document_rendering
from pult.services.documents.document_rendering import DocumentRenderer


def cached_image(directory, index, size, last_use):
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{index:064x}.png"
    path.write_bytes(b"x" * size)
    os.utime(path, (last_use, last_use))
    return path


def mock_browser(renderer, monkeypatch, image=b"image"):
    page = SimpleNamespace(
        route=AsyncMock(),
        set_content=AsyncMock(),
        evaluate=AsyncMock(return_value=None),
        screenshot=AsyncMock(return_value=image),
        close=AsyncMock(),
    )
    renderer.browser = SimpleNamespace(new_page=AsyncMock(return_value=page))
    monkeypatch.setattr(renderer, "ensure_browser", AsyncMock())
    monkeypatch.setattr(renderer, "_prepare_page", AsyncMock())
    return page


async def render(renderer, source, directory):
    return await renderer.render(
        source,
        directory / "document.md",
        directory,
        800,
        19,
        "#000000",
        "#ffffff",
        "#aaaaaa",
        font="source-sans-3",
    )


def test_startup_prunes_old_cache_without_touching_other_files(tmp_path, monkeypatch):
    monkeypatch.setattr(document_rendering, "DOCUMENT_CACHE_MAX_BYTES", 10)
    cache = tmp_path / "cache"
    old = cached_image(cache, 1, 6, 10)
    middle = cached_image(cache, 2, 5, 20)
    recent = cached_image(cache, 3, 5, 30)
    unrelated = cache / "figure.png"
    unrelated.write_bytes(b"user image")
    markdown = cache / "notes.md"
    markdown.write_text("Notes")
    pending = cache / "pending.tmp"
    pending.write_bytes(b"unfinished write")
    outside = tmp_path / "outside.png"
    outside.write_bytes(b"outside image")
    link = cache / f"{4:064x}.png"
    link.symlink_to(outside)
    directory = cache / f"{5:064x}.png"
    directory.mkdir()

    DocumentRenderer(cache)

    assert not old.exists()
    assert middle.read_bytes() == recent.read_bytes() == b"x" * 5
    assert unrelated.read_bytes() == b"user image"
    assert markdown.read_text() == "Notes"
    assert pending.read_bytes() == b"unfinished write"
    assert link.is_symlink() and outside.read_bytes() == b"outside image"
    assert directory.is_dir()


def test_restart_reuses_recent_images_and_regenerates_evicted_images(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(document_rendering, "DOCUMENT_CACHE_MAX_BYTES", 10)

    async def run():
        cache = tmp_path / "cache"
        first = DocumentRenderer(cache)
        assert not cache.exists()
        mock_browser(first, monkeypatch)
        a = await render(first, "A", tmp_path)
        b = await render(first, "B", tmp_path)
        assert isinstance(a, Path) and isinstance(b, Path)
        os.utime(a, (10, 10))
        os.utime(b, (20, 20))
        assert await render(first, "A", tmp_path) == a
        assert a.stat().st_mtime > b.stat().st_mtime

        restarted = DocumentRenderer(cache)
        page = mock_browser(restarted, monkeypatch)
        assert await render(restarted, "A", tmp_path) == a
        page.screenshot.assert_not_awaited()
        c = await render(restarted, "C", tmp_path)
        assert isinstance(c, Path) and c.exists() and a.exists()
        assert not b.exists()
        assert sum(path.stat().st_size for path in cache.glob("*.png")) == 10

        assert await render(restarted, "B", tmp_path) == b
        assert b.exists()
        assert page.screenshot.await_count == 2
        assert sum(path.stat().st_size for path in cache.glob("*.png")) == 10

    asyncio.run(run())


def test_cache_hits_do_not_scan_the_directory_or_create_missing_images(
    tmp_path, monkeypatch
):
    async def run():
        renderer = DocumentRenderer(tmp_path / "cache")
        mock_browser(renderer, monkeypatch)
        missing = renderer.cache / f"{1:064x}.png"
        assert not renderer.touch_cache(missing)
        assert not missing.exists()
        cached = await render(renderer, "Cached", tmp_path)
        assert isinstance(cached, Path)
        os.utime(cached, (10, 10))
        prune = Mock(side_effect=AssertionError("Warm access must not scan"))
        monkeypatch.setattr(renderer, "prune_cache", prune)
        async with renderer.lock:
            assert (
                await asyncio.wait_for(render(renderer, "Cached", tmp_path), 1)
                == cached
            )
        assert cached.stat().st_mtime > 10
        prune.assert_not_called()

    asyncio.run(run())


def test_new_image_remains_readable_despite_an_older_timestamp(tmp_path, monkeypatch):
    monkeypatch.setattr(document_rendering, "DOCUMENT_CACHE_MAX_BYTES", 5)
    cache = tmp_path / "cache"
    old = cached_image(cache, 1, 5, 4_000_000_000)

    async def run():
        renderer = DocumentRenderer(cache)
        mock_browser(renderer, monkeypatch)
        current = await render(renderer, "New", tmp_path)
        assert isinstance(current, Path) and current.read_bytes() == b"image"
        assert not old.exists()

    asyncio.run(run())


def test_oversized_image_bypasses_disk_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(document_rendering, "DOCUMENT_CACHE_MAX_BYTES", 5)
    cache = tmp_path / "cache"
    old = cached_image(cache, 1, 5, 10)

    async def run():
        renderer = DocumentRenderer(cache)
        page = mock_browser(renderer, monkeypatch, image=b"oversized image")
        assert await render(renderer, "Large", tmp_path) == b"oversized image"
        assert old.read_bytes() == b"x" * 5
        assert list(cache.iterdir()) == [old]
        assert await render(renderer, "Large", tmp_path) == b"oversized image"
        assert page.screenshot.await_count == 2

    asyncio.run(run())
