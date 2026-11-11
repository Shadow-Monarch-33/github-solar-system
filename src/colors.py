"""Color helpers used by themes and the SVG renderer."""

from __future__ import annotations

import hashlib


def hex_to_rgb(color: str) -> tuple[int, int, int]:
    value = color.strip().lstrip("#")
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    if len(value) != 6:
        raise ValueError(f"invalid hex color: {color!r}")
    try:
        return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]
    except ValueError as exc:
        raise ValueError(f"invalid hex color: {color!r}") from exc


def rgb_to_hex(rgb: tuple[float, float, float]) -> str:
    r, g, b = (max(0, min(255, int(round(channel)))) for channel in rgb)
    return f"#{r:02x}{g:02x}{b:02x}"


def shade(color: str, factor: float) -> str:
    """Darken (factor < 1) or lighten (factor > 1) a hex color."""
    r, g, b = hex_to_rgb(color)
    if factor <= 1.0:
        rgb = (r * factor, g * factor, b * factor)
    else:
        t = factor - 1.0
        rgb = (r + (255 - r) * t, g + (255 - g) * t, b + (255 - b) * t)
    return rgb_to_hex(rgb)


def mix(a: str, b: str, t: float) -> str:
    t = max(0.0, min(1.0, t))
    ar, ag, ab = hex_to_rgb(a)
    br, bg, bb = hex_to_rgb(b)
    return rgb_to_hex((ar + (br - ar) * t, ag + (bg - ag) * t, ab + (bb - ab) * t))


def with_alpha(color: str, alpha: float) -> str:
    r, g, b = hex_to_rgb(color)
    a = max(0.0, min(1.0, alpha))
    return f"rgba({r},{g},{b},{a:.3f})"


def hsl_to_hex(h: float, s: float, l: float) -> str:
    h = h % 360.0
    s = max(0.0, min(1.0, s))
    l = max(0.0, min(1.0, l))

    c = (1 - abs(2 * l - 1)) * s
    x = c * (1 - abs((h / 60.0) % 2 - 1))
    m = l - c / 2

    if h < 60:
        rgb = (c, x, 0.0)
    elif h < 120:
        rgb = (x, c, 0.0)
    elif h < 180:
        rgb = (0.0, c, x)
    elif h < 240:
        rgb = (0.0, x, c)
    elif h < 300:
        rgb = (x, 0.0, c)
    else:
        rgb = (c, 0.0, x)

    return rgb_to_hex(tuple((channel + m) * 255 for channel in rgb))


def _digest(key: str) -> int:
    return int.from_bytes(hashlib.sha256(key.encode("utf-8")).digest()[:8], "big")


def deterministic_index(key: str, n: int) -> int:
    if n <= 0:
        raise ValueError("n must be positive")
    return _digest(key) % n


def deterministic_color(key: str, palette: list[str]) -> str:
    if not palette:
        raise ValueError("palette must not be empty")
    return palette[deterministic_index(key, len(palette))]
