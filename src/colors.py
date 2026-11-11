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


# GitHub's linguist palette for the languages this tool is likely to meet.
# Unknown languages fall back to the theme's curated palette.
LANGUAGE_COLORS: dict[str, str] = {
    "1c enterprise": "#814CCC",
    "abap": "#E8274B",
    "apex": "#1797c0",
    "assembly": "#6E4C13",
    "astro": "#ff5a03",
    "c": "#555555",
    "c#": "#178600",
    "c++": "#F34B7D",
    "clojure": "#db5855",
    "cmake": "#DA3434",
    "css": "#563D7C",
    "dart": "#00B4AB",
    "dockerfile": "#384d54",
    "elixir": "#6e4a7e",
    "elm": "#60B5CC",
    "erlang": "#B83998",
    "f#": "#b845fc",
    "go": "#00ADD8",
    "graphql": "#e10098",
    "haskell": "#5e5086",
    "html": "#E34C26",
    "java": "#B07219",
    "javascript": "#F1E05A",
    "julia": "#a270ba",
    "jupyter notebook": "#DA5B0B",
    "kotlin": "#A97BFF",
    "lua": "#000080",
    "makefile": "#427819",
    "markdown": "#083fa1",
    "mdx": "#fcb32c",
    "nim": "#ffc200",
    "nix": "#7e7eff",
    "objective-c": "#438eff",
    "ocaml": "#ef7a08",
    "perl": "#0298c3",
    "php": "#4F5D95",
    "plpgsql": "#336790",
    "powershell": "#012456",
    "python": "#3572A5",
    "r": "#198CE7",
    "ruby": "#701516",
    "rust": "#DEA584",
    "scala": "#c22d40",
    "scss": "#c6538c",
    "shell": "#89E051",
    "solidity": "#AA6746",
    "sql": "#e38c00",
    "svelte": "#FF3E00",
    "swift": "#F05138",
    "tex": "#3D6117",
    "typescript": "#3178C6",
    "vim script": "#199f4b",
    "vue": "#41B883",
    "zig": "#ec915c",
}


def language_color(name: str, fallback: str) -> str:
    """Return the linguist color for a language, or a theme fallback."""

    return LANGUAGE_COLORS.get(str(name).strip().lower(), fallback)
