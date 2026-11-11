"""Deterministic orbital layout for the GitHub solar system.

The layout is a pure function of its inputs. It stores absolute static
positions for fallbacks and relative motion paths for nested SVG animation,
so a planet can carry its moons while each moon also orbits its planet.
"""

from __future__ import annotations

import hashlib
import math
import random
from dataclasses import dataclass
from urllib.parse import quote

from .colors import language_color, mix
from .data_models import Commit, Language, Repository, User

DEFAULT_WIDTH = 1200
DEFAULT_HEIGHT = 675
GOLDEN_ANGLE = 137.50776405003785
STAR_DENSITY = {"off": 0, "low": 90, "normal": 170, "high": 280}
MOONS_PER_RING = 12
MIN_PLANET_RADIUS = 0.5
MAX_PLANET_RADIUS = 34.0
DEFAULT_COMET_LIMIT = 6
ASPECT_CAP = 1.55
COMET_FLIGHT = 8.0
COMET_SLOT = 5.5
COMET_MIN_CYCLE = 26.0


@dataclass(frozen=True)
class Moon:
    name: str
    repo: str
    url: str
    stars: int
    radius: float
    orbit: float
    start_angle: float
    static_x: float
    static_y: float
    path: str
    period: float
    begin: float
    direction: int
    color: str
    label: str
    label_radius: float


@dataclass(frozen=True)
class Planet:
    language: str
    url: str
    radius: float
    orbit: float
    start_angle: float
    static_x: float
    static_y: float
    path: str
    period: float
    begin: float
    direction: int
    color: str
    label: str
    label_radius: float
    repo_count: int
    bytes: int
    moons: tuple[Moon, ...] = ()


@dataclass(frozen=True)
class Star:
    x: float
    y: float
    radius: float
    opacity: float


@dataclass(frozen=True)
class Comet:
    repo: str
    repo_name: str
    sha: str
    commit_url: str
    label: str
    start_x: float
    start_y: float
    end_x: float
    end_y: float
    cycle: float
    window_start: float
    flight: float
    static_x: float
    static_y: float


@dataclass(frozen=True)
class SolarSystemLayout:
    width: int
    height: int
    cx: float
    cy: float
    sun_radius: float
    max_extent: float
    aspect: float
    user: User
    repos_count: int
    languages_total: int
    planets: tuple[Planet, ...]
    stars: tuple[Star, ...]
    comets: tuple[Comet, ...]
    avatar_uri: str
    title: str
    description: str


def _jitter(key: str) -> float:
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") / 2**64


def _seed(width: int, height: int, login: str) -> int:
    digest = hashlib.sha256(f"{width}x{height}:{login}".encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def _seed_for(key: str) -> int:
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def _num(value: float) -> str:
    text = f"{float(value):.2f}".rstrip("0").rstrip(".")
    return "0" if text in {"", "-0"} else text


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _truncate(text: str, limit: int) -> str:
    value = str(text)
    if limit <= 0:
        return ""
    if len(value) <= limit:
        return value
    return value[: max(1, limit - 1)].rstrip() + "…"


def _planet_radius(byte_count: int, max_bytes: int) -> float:
    if max_bytes <= 0:
        return 8.0
    ratio = _clamp(byte_count / max_bytes, 0.0, 1.0)
    return min(MAX_PLANET_RADIUS, max(8.0, 8.0 + 26.0 * math.sqrt(ratio)))


def _moon_extent(moon_count: int) -> float:
    if moon_count <= 0:
        return 0.0
    rings = math.ceil(moon_count / MOONS_PER_RING)
    return 30.0 + 12.0 * (rings - 1) + 4.0


def _ellipse_motion_path(
    rx: float,
    ry: float,
    start_x: float,
    start_y: float,
    cx: float,
    cy: float,
    direction: int,
) -> str:
    """Relative ellipse anchored at the planet's static position.

    The group keeps ``translate(static_x, static_y)`` so a renderer that
    ignores SMIL still places it correctly. The arc is centred on the sun in
    that translated frame, so motion and fallback stay consistent.
    """

    span_x = 2.0 * (cx - start_x)
    span_y = 2.0 * (cy - start_y)
    sweep = 1 if direction >= 0 else 0
    return (
        f"M 0 0 A {_num(rx)} {_num(ry)} 0 0 {sweep} {_num(span_x)} {_num(span_y)} "
        f"A {_num(rx)} {_num(ry)} 0 0 {sweep} 0 0"
    )


def _circle_motion_path(radius: float, start_angle: float, direction: int) -> str:
    """Relative circle anchored at the moon's static position."""

    sweep = 1 if direction >= 0 else 0
    radians = math.radians(start_angle)
    start_x = math.cos(radians) * radius
    start_y = math.sin(radians) * radius
    span_x = -2.0 * start_x
    span_y = -2.0 * start_y
    return (
        f"M 0 0 A {_num(radius)} {_num(radius)} 0 0 {sweep} {_num(span_x)} {_num(span_y)} "
        f"A {_num(radius)} {_num(radius)} 0 0 {sweep} 0 0"
    )


def _fit_orbits(
    radii: list[float],
    extents: list[float],
    sun_radius: float,
    max_extent: float,
) -> tuple[list[float], list[float], list[float]]:
    if not radii:
        return [], [], []

    gap_base = 24.0 if len(radii) <= 8 else 13.0
    scale = 1.0
    result: tuple[list[float], list[float], list[float]] = ([], [], [])

    for _ in range(80):
        scaled_radii = [max(MIN_PLANET_RADIUS, radius * scale) for radius in radii]
        scaled_extents = [max(0.0, extent * scale) for extent in extents]
        gap = max(1.2, gap_base * scale)
        orbits: list[float] = []
        previous_reach = 0.0
        for index, (radius, extent) in enumerate(zip(scaled_radii, scaled_extents)):
            reach = radius + extent
            floor = sun_radius + 14.0 + reach
            if index == 0:
                orbit = floor
            else:
                orbit = max(floor, orbits[-1] + previous_reach + gap + reach)
            orbits.append(orbit)
            previous_reach = reach
        result = (scaled_radii, scaled_extents, orbits)
        outer = orbits[-1] + previous_reach
        if outer <= max_extent:
            break
        span = outer - (sun_radius + 14.0)
        available = max_extent - (sun_radius + 14.0)
        if span <= 0.0 or available <= 0.0:
            break
        scale *= max(0.03, (available / span) * 0.97)

    return result


def _boxes_overlap(
    first: tuple[float, float, float, float],
    second: tuple[float, float, float, float],
    padding: float = 0.0,
) -> bool:
    return not (
        first[2] + padding <= second[0]
        or second[2] + padding <= first[0]
        or first[3] + padding <= second[1]
        or second[3] + padding <= first[1]
    )


def _box_distance(
    first: tuple[float, float, float, float],
    second: tuple[float, float, float, float],
) -> float:
    dx = max(first[0] - second[2], second[0] - first[2], 0.0)
    dy = max(first[1] - second[3], second[1] - first[3], 0.0)
    return math.hypot(dx, dy)


def _build_moons(
    repositories: list[Repository],
    language: str,
    planet_radius: float,
    moon_extent: float,
    planet_color: str,
) -> tuple[Moon, ...]:
    group = [repo for repo in repositories if repo.primary_language == language]
    if not group:
        return ()
    group.sort(key=lambda repo: (-repo.stargazers_count, repo.name.lower()))

    rings = math.ceil(len(group) / MOONS_PER_RING)
    nominal = _moon_extent(len(group)) or 1.0
    scale = (moon_extent / nominal) if nominal > 0 else 0.0
    scale = max(0.03, scale)
    base = _jitter(f"moon-base:{language}") * 360.0
    moons: list[Moon] = []

    for index, repo in enumerate(group):
        ring = index // MOONS_PER_RING
        slot = index % MOONS_PER_RING
        ring_count = min(MOONS_PER_RING, len(group) - ring * MOONS_PER_RING)
        orbit = planet_radius + (24.0 + 12.0 * ring) * scale
        angle = (
            base
            + slot * (360.0 / ring_count)
            + ring * 17.0
            + _jitter(f"moon-angle:{repo.full_name}") * 9.0
        ) % 360.0
        direction = 1 if (index + ring) % 2 == 0 else -1
        # One angular velocity per planet keeps its moons evenly spaced forever,
        # so staggered phases never collapse into a cluster.
        period = round(16.0 + _jitter(f"moon-period:{language}") * 6.0, 2)
        begin = -round(_jitter(f"moon-begin:{repo.full_name}") * period, 2)
        radians = math.radians(angle)
        static_x = math.cos(radians) * orbit
        static_y = math.sin(radians) * orbit
        star_weight = math.log1p(max(0, repo.stargazers_count))
        moon_radius = max(0.35, (1.75 + 0.32 * star_weight) * scale)
        label_text = repo.name
        label_radius = max(orbit + 26.0, 5.4 * len(label_text) / 2.0 + 14.0)
        url = repo.html_url or f"https://github.com/{repo.full_name}"
        moons.append(
            Moon(
                name=repo.name,
                repo=repo.full_name,
                url=url,
                stars=repo.stargazers_count,
                radius=round(moon_radius, 2),
                orbit=round(orbit, 2),
                start_angle=round(angle, 2),
                static_x=round(static_x, 2),
                static_y=round(static_y, 2),
                path=_circle_motion_path(orbit, angle, direction),
                period=period,
                begin=begin,
                direction=direction,
                color=mix(planet_color, "#ffffff", 0.48),
                label=label_text,
                label_radius=round(label_radius, 2),
            )
        )
    return tuple(moons)


def _build_comets(
    commits: list[Commit],
    width: int,
    height: int,
    limit: int,
    seed: int,
) -> tuple[Comet, ...]:
    """Map verified commits to white, diagonal comets on a shared cycle.

    Every comet travels from the upper-left toward the lower-right. Their
    active windows are spaced on one repeating cycle so that at most two
    comets are ever visible at the same instant, including the loop boundary.
    """

    unique: dict[tuple[str, str], Commit] = {}
    for commit in commits:
        if commit.sha:
            unique.setdefault(commit.identity, commit)

    ordered = sorted(
        unique.values(),
        key=lambda commit: (commit.committed_at or "", commit.repo.lower(), commit.sha),
        reverse=True,
    )
    selected = ordered[: max(0, min(8, int(limit)))]
    count = len(selected)
    if count == 0:
        return ()

    cycle = max(COMET_MIN_CYCLE, count * COMET_SLOT + COMET_FLIGHT)
    comets: list[Comet] = []
    for index, commit in enumerate(selected):
        rng = random.Random(_seed_for(f"comet:{seed}:{commit.repo}:{commit.sha}"))
        start_x = rng.uniform(-0.18, 0.32) * width
        start_y = rng.uniform(-0.16, 0.05) * height
        end_x = width + rng.uniform(70.0, 210.0)
        end_y = height + rng.uniform(40.0, 130.0)
        end_x = max(end_x, start_x + 0.60 * width)
        end_y = max(end_y, start_y + 0.60 * height)
        # Static/preview frames park comets in clear corners instead of on top
        # of the orbital system. Animation always uses the diagonal trajectory.
        static_slots = (
            (0.10, 0.16),
            (0.64, 0.82),
            (0.80, 0.12),
            (0.16, 0.78),
            (0.30, 0.86),
            (0.86, 0.30),
        )
        slot_x, slot_y = static_slots[index % len(static_slots)]
        static_x = slot_x * width
        static_y = slot_y * height
        comets.append(
            Comet(
                repo=commit.repo,
                repo_name=commit.repo_name,
                sha=commit.sha,
                commit_url=commit.url
                or f"https://github.com/{commit.repo}/commit/{commit.sha}",
                label=commit.repo_name,
                start_x=round(start_x, 2),
                start_y=round(start_y, 2),
                end_x=round(end_x, 2),
                end_y=round(end_y, 2),
                cycle=round(cycle, 2),
                window_start=round(index * COMET_SLOT, 2),
                flight=COMET_FLIGHT,
                static_x=round(static_x, 2),
                static_y=round(static_y, 2),
            )
        )
    return tuple(comets)


def _build_stars(width: int, height: int, density: str, seed: int) -> tuple[Star, ...]:
    base = STAR_DENSITY.get(density, STAR_DENSITY["normal"])
    count = 0
    if base > 0:
        count = max(1, round(base * (width * height) / (DEFAULT_WIDTH * DEFAULT_HEIGHT)))
    rng = random.Random(seed)
    return tuple(
        Star(
            x=round(rng.uniform(0, width), 2),
            y=round(rng.uniform(0, height), 2),
            radius=round(rng.uniform(0.28, 1.05), 2),
            opacity=round(rng.uniform(0.14, 0.72), 2),
        )
        for _ in range(count)
    )


def build_layout(
    user: User,
    repositories: list[Repository],
    languages: list[Language],
    *,
    commits: list[Commit] | tuple[Commit, ...] = (),
    avatar_uri: str = "",
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    star_density: str = "normal",
    comet_limit: int = DEFAULT_COMET_LIMIT,
) -> SolarSystemLayout:
    width = max(320, int(width))
    height = max(240, int(height))
    repositories = list(repositories)
    languages = sorted(
        (
            language
            for language in languages
            if language.repo_count > 0 and language.bytes > 0
        ),
        key=lambda language: (-language.bytes, language.name.lower()),
    )

    classified = {language.name for language in languages}
    shown = [repo for repo in repositories if repo.primary_language in classified]
    counts: dict[str, int] = {}
    for repo in shown:
        language = repo.primary_language
        if language is not None:
            counts[language] = counts.get(language, 0) + 1

    sun_radius = _clamp(min(width, height) * 0.06, 30.0, 46.0)
    cx = width / 2.0
    cy = height / 2.0
    horizontal_margin = 66.0
    vertical_margin = 34.0
    label_reserve = 58.0
    available_rx = width / 2.0 - horizontal_margin - MAX_PLANET_RADIUS
    available_ry = height / 2.0 - vertical_margin - MAX_PLANET_RADIUS - label_reserve
    aspect = _clamp(available_rx / max(1.0, available_ry), 1.0, ASPECT_CAP)
    max_extent = max(60.0, min(available_rx / aspect, available_ry))

    total_bytes = sum(language.bytes for language in languages) or 1
    max_bytes = max((language.bytes for language in languages), default=1)
    base_radii = [_planet_radius(language.bytes, max_bytes) for language in languages]
    base_extents = [_moon_extent(counts.get(language.name, 0)) for language in languages]
    radii, extents, orbits = _fit_orbits(base_radii, base_extents, sun_radius, max_extent)

    palette = [
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
    ]

    phase = _jitter(f"phase:{user.login}:{len(languages)}") * 360.0
    specs: list[dict] = []
    for index, language in enumerate(languages):
        radius = radii[index]
        extent = extents[index]
        orbit = orbits[index]
        fallback = palette[index % len(palette)]
        color = language_color(language.name, fallback)
        if len(languages) <= 8:
            angle = (
                phase
                + index * (360.0 / max(1, len(languages)))
                + (_jitter(f"planet:{language.name}") - 0.5) * 16.0
            ) % 360.0
        else:
            angle = (
                index * GOLDEN_ANGLE + _jitter(f"planet:{language.name}") * 360.0
            ) % 360.0
        direction = 1 if _jitter(f"direction:{language.name}") >= 0.5 else -1
        rx = orbit * aspect
        ry = orbit
        radians = math.radians(angle)
        static_x = cx + math.cos(radians) * rx
        static_y = cy + math.sin(radians) * ry
        period = round(
            34.0
            + (orbit / max(1.0, max_extent)) * 32.0
            + _jitter(f"period:{language.name}") * 9.0,
            2,
        )
        begin = -round(_jitter(f"begin:{language.name}") * period, 2)
        label = language.name
        url = (
            f"https://github.com/{user.login}"
            f"?tab=repositories&language={quote(language.name.lower())}"
        )
        specs.append(
            {
                "index": index,
                "language": language,
                "radius": radius,
                "extent": extent,
                "orbit": orbit,
                "color": color,
                "angle": angle,
                "direction": direction,
                "rx": rx,
                "ry": ry,
                "static_x": static_x,
                "static_y": static_y,
                "period": period,
                "begin": begin,
                "label": label,
                "url": url,
            }
        )

    planets: list[Planet] = []
    for spec in specs:
        moons = _build_moons(
            shown,
            spec["language"].name,
            spec["radius"],
            spec["extent"],
            spec["color"],
        )
        moon_reach = max((moon.label_radius for moon in moons), default=0.0)
        label_radius = max(spec["radius"] + 30.0, moon_reach + 16.0)
        planets.append(
            Planet(
                language=spec["language"].name,
                url=spec["url"],
                radius=round(spec["radius"], 2),
                orbit=round(spec["orbit"], 2),
                start_angle=round(spec["angle"], 2),
                static_x=round(spec["static_x"], 2),
                static_y=round(spec["static_y"], 2),
                path=_ellipse_motion_path(
                    spec["rx"],
                    spec["ry"],
                    spec["static_x"],
                    spec["static_y"],
                    cx,
                    cy,
                    spec["direction"],
                ),
                period=spec["period"],
                begin=spec["begin"],
                direction=spec["direction"],
                color=spec["color"],
                label=spec["label"],
                label_radius=round(label_radius, 2),
                repo_count=spec["language"].repo_count,
                bytes=spec["language"].bytes,
                moons=moons,
            )
        )

    seed = _seed(width, height, user.login)
    description = (
        f"An animated orbit of {len(repositories)} public repositories across "
        f"{len(languages)} programming languages."
    )

    return SolarSystemLayout(
        width=width,
        height=height,
        cx=cx,
        cy=cy,
        sun_radius=round(sun_radius, 2),
        max_extent=round(max_extent, 2),
        aspect=round(aspect, 3),
        user=user,
        repos_count=len(repositories),
        languages_total=len(languages),
        planets=tuple(planets),
        stars=_build_stars(width, height, star_density, seed),
        comets=_build_comets(
            list(commits),
            width,
            height,
            int(comet_limit),
            seed,
        ),
        avatar_uri=str(avatar_uri or ""),
        title=f"Solar system for @{user.login}",
        description=description,
    )
