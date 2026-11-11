"""Deterministic orbital layout for the GitHub solar system.

The layout is a pure function of its inputs: the same user, repositories,
languages and options always produce byte-identical geometry. Planet sizes
follow the square root of a language's byte share, and planets are placed on
golden-angle orbits whose spacing reserves room for moon rings and labels.
"""

from __future__ import annotations

import hashlib
import math
import random
from dataclasses import dataclass
from urllib.parse import quote

from .data_models import Language, Repository, User

DEFAULT_WIDTH = 1200
DEFAULT_HEIGHT = 675
GOLDEN_ANGLE = 137.50776405003785
STAR_DENSITY = {"off": 0, "low": 80, "normal": 160, "high": 260}
MOONS_PER_RING = 12
MIN_PLANET_RADIUS = 0.5
LABEL_BUDGET = 16
LEGEND_SIZE = 8


@dataclass(frozen=True)
class Moon:
    name: str
    repo: str
    url: str
    stars: int
    radius: float
    orbit: float
    angle: float


@dataclass(frozen=True)
class Label:
    text: str
    x: float
    y: float
    anchor: str


@dataclass(frozen=True)
class Planet:
    language: str
    url: str
    x: float
    y: float
    radius: float
    reach: float
    orbit: float
    angle: float
    label: Label
    repo_count: int
    bytes: int
    percent: float
    percent_text: str
    moons: tuple[Moon, ...] = ()


@dataclass(frozen=True)
class Star:
    x: float
    y: float
    radius: float
    opacity: float
    twinkle_delay: float


@dataclass(frozen=True)
class Comet:
    path: str
    duration: float
    begin: float
    origin_x: float
    origin_y: float
    static_x: float
    static_y: float
    streak_x: float
    streak_y: float


@dataclass(frozen=True)
class IndexEntry:
    name: str
    display: str
    url: str
    color_index: int


@dataclass(frozen=True)
class RepoIndex:
    entries: tuple[IndexEntry, ...]
    columns: int
    rows: int
    row_height: float
    font_size: float
    top: float
    left: float
    column_width: float
    header: str


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
    repo_index: RepoIndex | None
    title: str
    subtitle: str
    meta: str


def _jitter(key: str) -> float:
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") / 2**64


def _num(value: float) -> str:
    text = f"{float(value):.2f}".rstrip("0").rstrip(".")
    return "0" if text in {"", "-0"} else text


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _seed(width: int, height: int, login: str) -> int:
    digest = hashlib.sha256(f"{width}x{height}:{login}".encode("utf-8")).hexdigest()
    return int(digest[:16], 16)


def _truncate(text: str, limit: int) -> str:
    value = str(text)
    if limit <= 0:
        return ""
    if len(value) <= limit:
        return value
    return value[: max(1, limit - 1)].rstrip() + "…"


def _planet_radius(byte_count: int, max_bytes: int) -> float:
    if max_bytes <= 0:
        return 6.0
    ratio = _clamp(byte_count / max_bytes, 0.0, 1.0)
    return min(30.0, max(6.0, 6.0 + 24.0 * math.sqrt(ratio)))


def _moon_extent(moon_count: int) -> float:
    if moon_count <= 0:
        return 0.0
    rings = math.ceil(moon_count / MOONS_PER_RING)
    return 6.0 + 4.5 * (rings - 1) + 2.4


def _fit_orbits(
    pairs: list[tuple[float, float]],
    inner_orbit: float,
    max_extent: float,
    gap: float,
) -> tuple[list[tuple[float, float]], list[float]]:
    def build(items: list[tuple[float, float]], spacing: float) -> list[float]:
        orbits: list[float] = []
        for index, (radius, extent) in enumerate(items):
            if index == 0:
                orbits.append(inner_orbit + radius + extent)
            else:
                previous_radius, previous_extent = items[index - 1]
                orbits.append(
                    orbits[-1]
                    + previous_radius
                    + previous_extent
                    + spacing
                    + radius
                    + extent
                )
        return orbits

    if not pairs:
        return [], []

    orbits = build(pairs, gap)
    for _ in range(60):
        radius, extent = pairs[-1]
        if orbits[-1] + radius + extent <= max_extent - 6.0:
            break
        gap = max(4.0, gap * 0.9)
        pairs = [(max(2.0, radius * 0.94), extent * 0.94) for radius, extent in pairs]
        orbits = build(pairs, gap)

    radius, extent = pairs[-1]
    if orbits[-1] + radius + extent > max_extent - 6.0:
        span = orbits[-1] + radius + extent - inner_orbit
        available = max_extent - 6.0 - inner_orbit
        ratio = max(0.0, available / span) if span > 0 else 1.0
        gap = gap * ratio
        scaled: list[tuple[float, float]] = []
        for planet_radius, moon_extent in pairs:
            radius_scaled = planet_radius * ratio
            extent_scaled = moon_extent * ratio
            radius_final = max(MIN_PLANET_RADIUS, radius_scaled)
            extent_final = max(0.0, radius_scaled + extent_scaled - radius_final)
            scaled.append((radius_final, extent_final))
        pairs = scaled
        orbits = build(pairs, gap)

    return pairs, orbits


def _label_rect(label: Label) -> tuple[float, float, float, float]:
    text_width = 6.2 * len(label.text) + 4.0
    if label.anchor == "start":
        return (label.x, label.y - 12.0, label.x + text_width, label.y + 3.0)
    return (label.x - text_width, label.y - 12.0, label.x, label.y + 3.0)


def _overlaps(first, second, padding: float = 2.0) -> bool:
    return not (
        first[2] + padding <= second[0]
        or second[2] + padding <= first[0]
        or first[3] + padding <= second[1]
        or second[3] + padding <= first[1]
    )


def _label_candidates(
    x: float, y: float, direction_x: float, direction_y: float
):
    yield x, y
    for step in range(1, 7):
        yield x + direction_x * 7.0 * step, y + direction_y * 7.0 * step
    for radius in (14.0, 26.0, 38.0):
        for delta_x, delta_y in (
            (-1, -1),
            (1, -1),
            (-1, 1),
            (1, 1),
            (0, -1),
            (0, 1),
            (-1, 0),
            (1, 0),
        ):
            yield x + delta_x * radius, y + delta_y * radius * 0.7


def _resolve_labels(
    labels: list[Label],
    directions: list[tuple[float, float]],
    obstacles: list[tuple[float, float, float, float]],
    hard_zones: list[tuple[float, float, float, float]],
    width: int,
    height: int,
) -> list[Label]:
    resolved = list(labels)
    placed = list(obstacles)
    order = sorted(
        (index for index, label in enumerate(resolved) if label.text),
        key=lambda index: (resolved[index].y, resolved[index].x),
    )

    for index in order:
        label = resolved[index]
        direction_x, direction_y = directions[index]
        chosen: Label | None = None
        for x, y in _label_candidates(label.x, label.y, direction_x, direction_y):
            x = _clamp(x, 8.0, width - 8.0)
            y = _clamp(y, 20.0, height - 10.0)
            candidate = Label(text=label.text, x=x, y=y, anchor=label.anchor)
            box = _label_rect(candidate)
            if any(_overlaps(box, zone, 0.0) for zone in hard_zones):
                continue
            if any(_overlaps(box, other) for other in placed):
                continue
            chosen = candidate
            placed.append(box)
            break
        resolved[index] = chosen or Label(
            text="", x=label.x, y=label.y, anchor=label.anchor
        )

    return resolved


def _build_moons(
    repositories: list[Repository],
    language: str,
    planet_radius: float,
    moon_extent: float,
) -> tuple[Moon, ...]:
    group = [repo for repo in repositories if repo.primary_language == language]
    if not group:
        return ()
    group.sort(key=lambda repo: (-repo.stargazers_count, repo.name.lower()))

    rings = math.ceil(len(group) / MOONS_PER_RING)
    nominal = 6.0 + 4.5 * (rings - 1) + 2.4
    scale = (moon_extent / nominal) if nominal > 0 else 1.0
    if scale <= 0.0:
        scale = 0.15
    base = _jitter(language) * 360.0
    dot = _clamp(planet_radius * 0.16, 1.0, 2.4)

    moons: list[Moon] = []
    for index, repo in enumerate(group):
        ring = index // MOONS_PER_RING
        slot = index % MOONS_PER_RING
        ring_count = min(MOONS_PER_RING, len(group) - ring * MOONS_PER_RING)
        orbit = planet_radius + (6.0 + 4.5 * ring) * scale
        angle = (
            base + slot * (360.0 / ring_count) + ring * 13.0
        ) % 360.0
        url = repo.html_url or f"https://github.com/{repo.full_name}"
        moons.append(
            Moon(
                name=repo.name,
                repo=repo.name,
                url=url,
                stars=repo.stargazers_count,
                radius=dot,
                orbit=orbit,
                angle=angle,
            )
        )
    return tuple(moons)


def _plan_index(
    repositories: list[Repository], languages: list[Language], width: int
) -> tuple[list[tuple[str, str, int]], int, int] | None:
    if not repositories:
        return None
    order = {language.name: index for index, language in enumerate(languages)}
    entries: list[tuple[str, str, int]] = []
    for language in languages:
        group = [repo for repo in repositories if repo.primary_language == language.name]
        group.sort(key=lambda repo: (-repo.stargazers_count, repo.name.lower()))
        for repo in group:
            url = repo.html_url or f"https://github.com/{repo.full_name}"
            entries.append((repo.name, url, order[language.name]))

    count = len(entries)
    columns = min(6, count) if count <= 24 else min(8, math.ceil(count / 8))
    rows = math.ceil(count / columns)
    while rows > 12 and columns < 12:
        columns += 1
        rows = math.ceil(count / columns)
    return entries, columns, rows


def _index_height(plan: tuple[list[tuple[str, str, int]], int, int] | None) -> float:
    if plan is None:
        return 0.0
    _, _, rows = plan
    return 16.0 + rows * 13.0 + 12.0


def _build_index(
    plan: tuple[list[tuple[str, str, int]], int, int] | None,
    width: int,
    height: int,
) -> RepoIndex | None:
    if plan is None:
        return None
    entries, columns, rows = plan
    column_width = (width - 72.0) / columns
    limit = max(6, int((column_width - 18.0) / 5.3))
    top = height - _index_height(plan) - 12.0
    return RepoIndex(
        entries=tuple(
            IndexEntry(
                name=name,
                display=_truncate(name, limit),
                url=url,
                color_index=color_index,
            )
            for name, url, color_index in entries
        ),
        columns=columns,
        rows=rows,
        row_height=13.0,
        font_size=9.5,
        top=top,
        left=32.0,
        column_width=column_width,
        header=f"REPOSITORIES · {len(entries)}",
    )


def _build_stars(width: int, height: int, density: str, seed: int) -> tuple[Star, ...]:
    base = STAR_DENSITY.get(density, STAR_DENSITY["normal"])
    count = 0
    if base > 0:
        count = max(1, round(base * (width * height) / (DEFAULT_WIDTH * DEFAULT_HEIGHT)))
    rng = random.Random(seed)
    stars = [
        Star(
            x=round(rng.uniform(0, width), 2),
            y=round(rng.uniform(0, height), 2),
            radius=round(rng.uniform(0.4, 1.4), 2),
            opacity=round(rng.uniform(0.25, 0.9), 2),
            twinkle_delay=round(rng.uniform(0, 4), 2),
        )
        for _ in range(count)
    ]
    return tuple(stars)


def _build_comets(width: int, height: int, count: int, seed: int) -> tuple[Comet, ...]:
    total = max(0, min(3, int(count)))
    comets: list[Comet] = []
    for index in range(total):
        rng = random.Random(seed + index)
        x0 = rng.uniform(0.05 * width, 0.42 * width)
        y0 = rng.uniform(0.28 * height, 0.45 * height)
        x1 = rng.uniform(0.55 * width, 0.92 * width)
        y1 = rng.uniform(0.55 * height, 0.85 * height)
        control_x = (x0 + x1) / 2 + rng.uniform(-0.12 * width, 0.12 * width)
        control_y = (y0 + y1) / 2 + rng.uniform(-0.10 * height, 0.10 * height)
        path = (
            f"M 0 0 Q {_num(control_x - x0)} {_num(control_y - y0)} "
            f"{_num(x1 - x0)} {_num(y1 - y0)}"
        )
        heading = math.atan2(y1 - y0, x1 - x0)
        comets.append(
            Comet(
                path=path,
                duration=round(rng.uniform(6, 12), 2),
                begin=-float(index * 3),
                origin_x=round(x0, 2),
                origin_y=round(y0, 2),
                static_x=round(0.25 * x0 + 0.5 * control_x + 0.25 * x1, 2),
                static_y=round(0.25 * y0 + 0.5 * control_y + 0.25 * y1, 2),
                streak_x=round(-math.cos(heading) * 22.0, 2),
                streak_y=round(-math.sin(heading) * 22.0, 2),
            )
        )
    return tuple(comets)


def build_layout(
    user: User,
    repositories: list[Repository],
    languages: list[Language],
    *,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    star_density: str = "normal",
    comet_count: int = 0,
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

    index_plan = _plan_index(shown, languages, width)
    index_height = _index_height(index_plan)
    top_reserved = 96.0
    bottom_reserved = index_height + 24.0 if index_plan is not None else 54.0
    available_height = max(120.0, height - top_reserved - bottom_reserved)
    cx = width / 2.0
    cy = top_reserved + available_height / 2.0
    max_extent = max(60.0, min((width - 160.0) / 2.0, available_height / 2.0))
    aspect = min(1.75, max(1.0, (width - 160.0) / (2.0 * max_extent)))
    sun_radius = max(22.0, min(width, height) * 0.05)
    inner_orbit = sun_radius + 46.0

    total_bytes = sum(language.bytes for language in languages) or 1
    max_bytes = max((language.bytes for language in languages), default=1)

    radii = [_planet_radius(language.bytes, max_bytes) for language in languages]
    extents = [_moon_extent(counts.get(language.name, 0)) for language in languages]
    gap = 24.0 if len(languages) <= 8 else 16.0
    pairs, orbits = _fit_orbits(
        list(zip(radii, extents)), inner_orbit, max_extent, gap
    )

    geometry: list[tuple[float, float, float, float, float, float]] = []
    percents: list[tuple[float, str]] = []
    labels: list[Label] = []
    directions: list[tuple[float, float]] = []

    for index, language in enumerate(languages):
        radius, extent = pairs[index]
        orbit = orbits[index]
        angle = (index * GOLDEN_ANGLE + _jitter(language.name) * 360.0) % 360.0
        radians = math.radians(angle)
        planet_x = cx + math.cos(radians) * orbit * aspect
        planet_y = cy + math.sin(radians) * orbit
        geometry.append((planet_x, planet_y, orbit, radius, extent, angle))
        percent = 100.0 * language.bytes / total_bytes
        percent_text = f"{percent:.0f}%" if percent >= 1.0 else "<1%"
        percents.append((percent, percent_text))
        offset = radius + max(14.0, extent + 12.0)
        label_x = _clamp(planet_x + math.cos(radians) * offset, 8.0, width - 8.0)
        label_y = _clamp(planet_y + math.sin(radians) * offset + 4.0, 20.0, height - 10.0)
        anchor = "start" if label_x >= cx else "end"
        if anchor == "start" and label_x > width - 140.0:
            anchor = "end"
        text = "" if index >= LABEL_BUDGET else f"{language.name} · {percent_text}"
        labels.append(Label(text=text, x=label_x, y=label_y, anchor=anchor))
        directions.append((math.cos(radians), math.sin(radians)))

    header_zone = (0.0, 0.0, 680.0, 94.0)
    legend_zone = (width - 268.0, 14.0, width - 8.0, 196.0)
    hard_zones = [header_zone, legend_zone]
    if index_plan is not None:
        index_top = height - index_height - 12.0
        hard_zones.append((0.0, index_top - 8.0, float(width), float(height)))

    obstacles: list[tuple[float, float, float, float]] = list(hard_zones)
    for x, y, _orbit, radius, extent, _angle in geometry:
        reach = radius + extent
        obstacles.append((x - reach, y - reach, x + reach, y + reach))

    labels = _resolve_labels(labels, directions, obstacles, hard_zones, width, height)

    planets: list[Planet] = []
    for index, language in enumerate(languages):
        x, y, orbit, radius, extent, angle = geometry[index]
        percent, percent_text = percents[index]
        url = (
            f"https://github.com/{user.login}"
            f"?tab=repositories&language={quote(language.name.lower())}"
        )
        planets.append(
            Planet(
                language=language.name,
                url=url,
                x=x,
                y=y,
                radius=radius,
                reach=radius + extent,
                orbit=orbit,
                angle=angle,
                label=labels[index],
                repo_count=language.repo_count,
                bytes=language.bytes,
                percent=percent,
                percent_text=percent_text,
                moons=_build_moons(shown, language.name, radius, extent),
            )
        )

    seed = _seed(width, height, user.login)
    unclassified = len(repositories) - len(shown)
    meta = f"{len(repositories)} repositories · {len(languages)} languages"
    if unclassified:
        meta += f" · {unclassified} unclassified"

    return SolarSystemLayout(
        width=width,
        height=height,
        cx=cx,
        cy=cy,
        sun_radius=sun_radius,
        max_extent=max_extent,
        aspect=aspect,
        user=user,
        repos_count=len(repositories),
        languages_total=len(languages),
        planets=tuple(planets),
        stars=_build_stars(width, height, star_density, seed),
        comets=_build_comets(width, height, comet_count, seed),
        repo_index=_build_index(index_plan, width, height),
        title=_truncate(f"{user.name or user.login} · GitHub Solar System", 52),
        subtitle=_truncate(
            user.bio
            or "Open-source repositories mapped to the languages that power them.",
            86,
        ),
        meta=meta,
    )
