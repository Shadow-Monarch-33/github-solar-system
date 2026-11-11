"""GitHub Solar System: render a GitHub profile as a self-contained SVG."""

from .colors import (
    deterministic_color,
    deterministic_index,
    hex_to_rgb,
    hsl_to_hex,
    mix,
    rgb_to_hex,
    shade,
    with_alpha,
)
from .data_models import Commit, Language, Repository, SolarSystem, User
from .github_client import API_ROOT, GitHubClient, GitHubError
from .layout import (
    DEFAULT_COMET_LIMIT,
    DEFAULT_HEIGHT,
    DEFAULT_WIDTH,
    STAR_DENSITY,
    Comet,
    Moon,
    Planet,
    SolarSystemLayout,
    Star,
    build_layout,
)
from .renderer import render_svg
from .styles import DEFAULT_THEME, THEMES, get_theme

__all__ = [
    "API_ROOT",
    "Comet",
    "Commit",
    "DEFAULT_COMET_LIMIT",
    "DEFAULT_HEIGHT",
    "DEFAULT_THEME",
    "DEFAULT_WIDTH",
    "GitHubClient",
    "GitHubError",
    "Language",
    "Moon",
    "Planet",
    "Repository",
    "STAR_DENSITY",
    "SolarSystem",
    "SolarSystemLayout",
    "Star",
    "THEMES",
    "User",
    "build_layout",
    "deterministic_color",
    "deterministic_index",
    "get_theme",
    "hex_to_rgb",
    "hsl_to_hex",
    "mix",
    "render_svg",
    "rgb_to_hex",
    "shade",
    "with_alpha",
]
