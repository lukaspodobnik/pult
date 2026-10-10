"""Pixelmasken für die festen Ecken einer scrollbaren Dokumentfläche."""

from functools import lru_cache

from PIL import Image, ImageDraw


@lru_cache(maxsize=8)
def corner_masks(radius: int) -> tuple[Image.Image, ...]:
    scale = 4
    mask = Image.new("L", (radius * 2 * scale, radius * 2 * scale))
    ImageDraw.Draw(mask).rounded_rectangle(
        (0, 0, mask.width - 1, mask.height - 1), radius=radius * scale, fill=255
    )
    mask = mask.resize((radius * 2, radius * 2), Image.Resampling.LANCZOS)
    return tuple(
        mask.crop(box)
        for box in (
            (0, 0, radius, radius),
            (radius, 0, radius * 2, radius),
            (0, radius, radius, radius * 2),
            (radius, radius, radius * 2, radius * 2),
        )
    )


def round_document_tile(
    image: Image.Image,
    viewport: tuple[int, int, int, int],
    outside: str,
    radius: int,
) -> Image.Image:
    """Runde nur die sichtbaren Viewportecken, nicht die Grenzen der Bildkacheln."""
    left, top, right, bottom = viewport
    radius = min(radius, (right - left) // 2, (bottom - top) // 2)
    if radius < 1:
        return image
    positions = (
        (left, top),
        (right - radius, top),
        (left, bottom - radius),
        (right - radius, bottom - radius),
    )
    result = image
    for (x, y), mask in zip(positions, corner_masks(radius)):
        if x >= image.width or y >= image.height or x + radius <= 0 or y + radius <= 0:
            continue
        if result is image:
            result = image.copy()
        box = (x, y, x + radius, y + radius)
        corner = Image.new("RGB", (radius, radius), outside)
        corner.paste(image.crop(box), (0, 0), mask)
        result.paste(corner, (x, y))
    return result
