"""Named color themes for the solar system renderer."""

from __future__ import annotations

import warnings

DEFAULT_THEME = "nebula"

THEMES: dict[str, dict[str, object]] = {
    "nebula": {
        "background_top": "#050816",
        "background_bottom": "#0b1026",
        "star": "#ffffff",
        "orbit": "#8ea0c9",
        "text": "#eef2ff",
        "muted": "#9aa4c4",
        "sun_core": "#ffe9a8",
        "sun_mid": "#ffb84d",
        "sun_glow": "#ff7a18",
        "accent": "#7dd3fc",
        "palette": [
            "#7dd3fc",
            "#a78bfa",
            "#f472b6",
            "#34d399",
            "#fbbf24",
            "#fb7185",
            "#60a5fa",
            "#2dd4bf",
            "#c084fc",
            "#f59e0b",
            "#38bdf8",
            "#f87171",
        ],
    },
    "midnight": {
        "background_top": "#01030a",
        "background_bottom": "#071224",
        "star": "#dbeafe",
        "orbit": "#64748b",
        "text": "#e2e8f0",
        "muted": "#8291a8",
        "sun_core": "#fef3c7",
        "sun_mid": "#f59e0b",
        "sun_glow": "#b45309",
        "accent": "#38bdf8",
        "palette": [
            "#38bdf8",
            "#818cf8",
            "#f472b6",
            "#2dd4bf",
            "#facc15",
            "#f87171",
            "#a78bfa",
            "#4ade80",
            "#e879f9",
            "#fbbf24",
            "#22d3ee",
            "#fb923c",
        ],
    },
    "light": {
        "background_top": "#f8fafc",
        "background_bottom": "#e2e8f0",
        "star": "#1e293b",
        "orbit": "#64748b",
        "text": "#0f172a",
        "muted": "#475569",
        "sun_core": "#fde68a",
        "sun_mid": "#f59e0b",
        "sun_glow": "#fb923c",
        "accent": "#2563eb",
        "palette": [
            "#2563eb",
            "#7c3aed",
            "#db2777",
            "#059669",
            "#d97706",
            "#e11d48",
            "#0891b2",
            "#65a30d",
            "#9333ea",
            "#ea580c",
            "#0284c7",
            "#dc2626",
        ],
    },
    "mono": {
        "background_top": "#0a0a0a",
        "background_bottom": "#161616",
        "star": "#f5f5f5",
        "orbit": "#737373",
        "text": "#fafafa",
        "muted": "#a3a3a3",
        "sun_core": "#fafafa",
        "sun_mid": "#d4d4d4",
        "sun_glow": "#a3a3a3",
        "accent": "#e5e5e5",
        "palette": [
            "#fafafa",
            "#d4d4d4",
            "#a3a3a3",
            "#e5e5e5",
            "#c4c4c4",
            "#8f8f8f",
            "#f0f0f0",
            "#bdbdbd",
            "#999999",
            "#dedede",
            "#cccccc",
            "#b3b3b3",
        ],
    },
}


def get_theme(name: str) -> dict[str, object]:
    theme = THEMES.get(name)
    if theme is not None:
        return theme
    warnings.warn(f"unknown theme {name!r}; falling back to {DEFAULT_THEME!r}", stacklevel=2)
    return THEMES[DEFAULT_THEME]
