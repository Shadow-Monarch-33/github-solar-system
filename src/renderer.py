"""Self-contained SVG renderer for a solar system layout."""

from __future__ import annotations

import math
import os
import tempfile
from pathlib import Path
from xml.sax.saxutils import escape

from .colors import mix, shade
from .layout import SolarSystemLayout
from .styles import DEFAULT_THEME, get_theme

FONT_STACK = "'Segoe UI', Ubuntu, 'Helvetica Neue', Arial, sans-serif"


def _esc(value: object) -> str:
    return escape(str(value), {'"': "&quot;", "'": "&apos;"})


def _attr(value: object) -> str:
    return escape(str(value), {'"': "&quot;"})


def _n(value: object) -> str:
    text = f"{float(value):.2f}".rstrip("0").rstrip(".")
    return "0" if text in {"", "-0"} else text


def _tag(name: str, attrs: dict, *, close: bool = False) -> str:
    parts = [name]
    for key, value in attrs.items():
        if value is None:
            continue
        parts.append(f'{key}="{_attr(value)}"')
    head = " ".join(parts)
    return f"<{head}/>" if close else f"<{head}>"


def _text_tag(attrs: dict, content: object) -> list[str]:
    return [_tag("text", attrs), _esc(content), "</text>"]


def _description(layout: SolarSystemLayout) -> str:
    pieces = [layout.subtitle]
    if layout.planets:
        summary = ", ".join(
            f"{planet.language} {planet.percent_text}" for planet in layout.planets
        )
        pieces.append(f"Languages: {summary}.")
    pieces.append(f"{layout.repos_count} public repositories.")
    return " ".join(pieces)


def _defs(layout: SolarSystemLayout, theme: dict, animate: bool) -> list[str]:
    palette = theme["palette"]
    parts = ["<defs>"]

    parts.append(_tag("linearGradient", {"id": "bg", "x1": "0", "y1": "0", "x2": "0", "y2": "1"}))
    parts.append(_tag("stop", {"offset": "0", "stop-color": theme["background_top"]}, close=True))
    parts.append(_tag("stop", {"offset": "1", "stop-color": theme["background_bottom"]}, close=True))
    parts.append("</linearGradient>")

    parts.append(
        _tag("radialGradient", {"id": "sunGlow", "cx": "0.5", "cy": "0.5", "r": "0.5"})
    )
    parts.append(_tag("stop", {"offset": "0", "stop-color": theme["sun_core"], "stop-opacity": "0.16"}, close=True))
    parts.append(_tag("stop", {"offset": "0.45", "stop-color": theme["sun_mid"], "stop-opacity": "0.22"}, close=True))
    parts.append(_tag("stop", {"offset": "1", "stop-color": theme["sun_glow"], "stop-opacity": "0"}, close=True))
    parts.append("</radialGradient>")

    parts.append(
        _tag("radialGradient", {"id": "sunGrad", "cx": "0.38", "cy": "0.34", "r": "0.72"})
    )
    parts.append(_tag("stop", {"offset": "0", "stop-color": shade(str(theme["sun_core"]), 1.5)}, close=True))
    parts.append(_tag("stop", {"offset": "0.55", "stop-color": theme["sun_core"]}, close=True))
    parts.append(_tag("stop", {"offset": "1", "stop-color": theme["sun_mid"]}, close=True))
    parts.append("</radialGradient>")

    for index, _planet in enumerate(layout.planets):
        base = palette[index % len(palette)]
        parts.append(
            _tag("radialGradient", {"id": f"pg{index}", "cx": "0.36", "cy": "0.32", "r": "0.75"})
        )
        parts.append(_tag("stop", {"offset": "0", "stop-color": shade(base, 1.6)}, close=True))
        parts.append(_tag("stop", {"offset": "0.55", "stop-color": base}, close=True))
        parts.append(_tag("stop", {"offset": "1", "stop-color": shade(base, 0.45)}, close=True))
        parts.append("</radialGradient>")

    if animate:
        parts.append(
            "<style>"
            ".tw{animation:twinkle 4.2s ease-in-out infinite}"
            "@keyframes twinkle{0%,100%{opacity:.25}50%{opacity:1}}"
            "@media (prefers-reduced-motion:reduce){.tw{animation:none}}"
            "</style>"
        )

    parts.append("</defs>")
    return parts


def _stars(layout: SolarSystemLayout, theme: dict, animate: bool) -> list[str]:
    if not layout.stars:
        return []
    parts = [_tag("g", {"class": "stars", "fill": theme["star"]})]
    for star in layout.stars:
        attrs = {
            "cx": _n(star.x),
            "cy": _n(star.y),
            "r": _n(star.radius),
            "fill-opacity": _n(star.opacity),
        }
        if animate:
            attrs["class"] = "tw"
            attrs["style"] = f"animation-delay:-{_n(star.twinkle_delay)}s"
        parts.append(_tag("circle", attrs, close=True))
    parts.append("</g>")
    return parts


def _orbits(layout: SolarSystemLayout, theme: dict) -> list[str]:
    parts = []
    for planet in layout.planets:
        parts.append(
            _tag(
                "ellipse",
                {
                    "cx": _n(layout.cx),
                    "cy": _n(layout.cy),
                    "rx": _n(planet.orbit * layout.aspect),
                    "ry": _n(planet.orbit),
                    "fill": "none",
                    "stroke": theme["orbit"],
                    "stroke-width": "1",
                    "stroke-opacity": "0.22",
                    "stroke-dasharray": "3 6",
                },
                close=True,
            )
        )
    return parts


def _sun(layout: SolarSystemLayout, theme: dict) -> list[str]:
    cx = _n(layout.cx)
    cy = _n(layout.cy)
    radius = layout.sun_radius
    parts = [
        _tag("circle", {"cx": cx, "cy": cy, "r": _n(radius * 2.4), "fill": "url(#sunGlow)"}, close=True),
        _tag(
            "circle",
            {
                "cx": cx,
                "cy": cy,
                "r": _n(radius * 1.32),
                "fill": "none",
                "stroke": shade(str(theme["sun_mid"]), 1.15),
                "stroke-width": "0.8",
                "stroke-opacity": "0.35",
            },
            close=True,
        ),
        _tag("circle", {"cx": cx, "cy": cy, "r": _n(radius), "fill": "url(#sunGrad)"}, close=True),
        _tag(
            "ellipse",
            {
                "cx": _n(layout.cx - radius * 0.28),
                "cy": _n(layout.cy - radius * 0.34),
                "rx": _n(radius * 0.34),
                "ry": _n(radius * 0.22),
                "fill": "#ffffff",
                "fill-opacity": "0.4",
            },
            close=True,
        ),
    ]
    parts.extend(
        _text_tag(
            {
                "x": cx,
                "y": _n(layout.cy + radius + 18),
                "text-anchor": "middle",
                "font-size": "12.5",
                "font-weight": "600",
                "fill": theme["text"],
                "paint-order": "stroke",
                "stroke": theme["background_bottom"],
                "stroke-width": "3",
                "stroke-linejoin": "round",
            },
            f"@{layout.user.login}",
        )
    )
    return parts


def _planets(layout: SolarSystemLayout, theme: dict) -> list[str]:
    palette = theme["palette"]
    parts: list[str] = []
    for index, planet in enumerate(layout.planets):
        base = palette[index % len(palette)]
        parts.append(_tag("a", {"href": planet.url, "target": "_blank", "rel": "noopener"}))
        parts.append(_tag("g", {"transform": f"translate({_n(planet.x)} {_n(planet.y)})"}))

        for orbit in sorted({round(moon.orbit, 2) for moon in planet.moons}):
            parts.append(
                _tag(
                    "circle",
                    {
                        "cx": "0",
                        "cy": "0",
                        "r": _n(orbit),
                        "fill": "none",
                        "stroke": theme["orbit"],
                        "stroke-width": "0.8",
                        "stroke-opacity": "0.22",
                    },
                    close=True,
                )
            )

        for moon in planet.moons:
            radians = math.radians(moon.angle)
            moon_x = math.cos(radians) * moon.orbit
            moon_y = math.sin(radians) * moon.orbit
            parts.append(_tag("circle", {"cx": _n(moon_x), "cy": _n(moon_y), "r": _n(moon.radius), "fill": mix(base, "#ffffff", 0.5)}))
            parts.append(_tag("title", {}))
            parts.append(_esc(f"{moon.repo} · {moon.stars} stars"))
            parts.append("</title></circle>")

        parts.append(
            _tag(
                "circle",
                {
                    "cx": "0",
                    "cy": "0",
                    "r": _n(planet.radius),
                    "fill": f"url(#pg{index})",
                    "stroke": shade(base, 0.6),
                    "stroke-width": "0.6",
                    "stroke-opacity": "0.7",
                },
                close=True,
            )
        )
        parts.append(
            _tag(
                "ellipse",
                {
                    "cx": _n(-planet.radius * 0.3),
                    "cy": _n(-planet.radius * 0.35),
                    "rx": _n(planet.radius * 0.32),
                    "ry": _n(planet.radius * 0.2),
                    "fill": "#ffffff",
                    "fill-opacity": "0.2",
                },
                close=True,
            )
        )
        parts.append("</g></a>")
    return parts


def _labels(layout: SolarSystemLayout, theme: dict) -> list[str]:
    parts: list[str] = []
    for planet in layout.planets:
        if not planet.label.text:
            continue
        parts.extend(
            _text_tag(
                {
                    "x": _n(planet.label.x),
                    "y": _n(planet.label.y),
                    "text-anchor": planet.label.anchor,
                    "font-size": "12.5",
                    "fill": theme["text"],
                    "paint-order": "stroke",
                    "stroke": theme["background_bottom"],
                    "stroke-width": "3",
                    "stroke-linejoin": "round",
                },
                planet.label.text,
            )
        )
    return parts


def _comets(layout: SolarSystemLayout, theme: dict, animate: bool) -> list[str]:
    parts: list[str] = []
    for comet in layout.comets:
        if animate:
            parts.append(
                _tag(
                    "g",
                    {"transform": f"translate({_n(comet.origin_x)} {_n(comet.origin_y)})"},
                )
            )
            parts.append(_tag("g", {}))
            parts.append(
                _tag(
                    "line",
                    {
                        "x1": "0",
                        "y1": "0",
                        "x2": _n(comet.streak_x),
                        "y2": _n(comet.streak_y),
                        "stroke": theme["accent"],
                        "stroke-width": "1.2",
                        "stroke-opacity": "0.5",
                        "stroke-linecap": "round",
                    },
                    close=True,
                )
            )
            parts.append(_tag("circle", {"r": "2", "fill": theme["accent"]}, close=True))
            parts.append(
                _tag(
                    "animateMotion",
                    {
                        "dur": f"{_n(comet.duration)}s",
                        "begin": f"{_n(comet.begin)}s",
                        "repeatCount": "indefinite",
                        "path": comet.path,
                    },
                    close=True,
                )
            )
            parts.append("</g></g>")
        else:
            parts.append(
                _tag(
                    "line",
                    {
                        "x1": _n(comet.static_x),
                        "y1": _n(comet.static_y),
                        "x2": _n(comet.static_x + comet.streak_x),
                        "y2": _n(comet.static_y + comet.streak_y),
                        "stroke": theme["accent"],
                        "stroke-width": "1.2",
                        "stroke-opacity": "0.45",
                        "stroke-linecap": "round",
                    },
                    close=True,
                )
            )
            parts.append(
                _tag(
                    "circle",
                    {
                        "cx": _n(comet.static_x),
                        "cy": _n(comet.static_y),
                        "r": "1.8",
                        "fill": theme["accent"],
                        "fill-opacity": "0.85",
                    },
                    close=True,
                )
            )
    return parts


def _legend(layout: SolarSystemLayout, theme: dict) -> list[str]:
    palette = theme["palette"]
    if not layout.planets:
        return []
    base_x = layout.width - 240
    base_y = 36.0
    parts = [_tag("g", {"class": "legend", "font-size": "12"})]
    for index, planet in enumerate(layout.planets[:8]):
        y = base_y + index * 18
        color = palette[index % len(palette)]
        parts.append(_tag("circle", {"cx": _n(base_x), "cy": _n(y), "r": "4", "fill": color}, close=True))
        parts.extend(
            _text_tag(
                {"x": _n(base_x + 12), "y": _n(y + 4), "fill": theme["muted"]},
                f"{planet.language} {planet.percent_text}",
            )
        )
    parts.append("</g>")
    return parts


def _index(layout: SolarSystemLayout, theme: dict) -> list[str]:
    index = layout.repo_index
    if index is None:
        return []
    palette = theme["palette"]
    parts = [_tag("g", {"class": "repositories", "font-size": _n(index.font_size)})]
    parts.extend(
        _text_tag(
            {
                "x": _n(index.left),
                "y": _n(index.top + 10),
                "font-size": "8.5",
                "letter-spacing": "1.6",
                "fill": theme["muted"],
            },
            index.header,
        )
    )
    origin_y = index.top + 16.0
    for position, entry in enumerate(index.entries):
        column = position // index.rows
        row = position % index.rows
        x = index.left + column * index.column_width
        y = origin_y + row * index.row_height + 9.0
        color = palette[entry.color_index % len(palette)]
        parts.append(_tag("a", {"href": entry.url, "target": "_blank", "rel": "noopener"}))
        parts.append(
            _tag(
                "circle",
                {"cx": _n(x + 3), "cy": _n(y - 3), "r": "2.4", "fill": color},
                close=True,
            )
        )
        parts.extend(_text_tag({"x": _n(x + 10), "y": _n(y), "fill": theme["muted"]}, entry.display))
        parts.append("</a>")
    parts.append("</g>")
    return parts


def _header(layout: SolarSystemLayout, theme: dict) -> list[str]:
    parts: list[str] = []
    parts.extend(
        _text_tag(
            {"x": "32", "y": "44", "font-size": "22", "font-weight": "700", "fill": theme["text"]},
            layout.title,
        )
    )
    parts.extend(
        _text_tag({"x": "32", "y": "66", "font-size": "12.5", "fill": theme["muted"]}, layout.subtitle)
    )
    parts.extend(
        _text_tag({"x": "32", "y": "84", "font-size": "11", "fill": theme["muted"]}, layout.meta)
    )
    return parts


def _write_atomic(path: str | os.PathLike[str], content: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(
        dir=str(target.parent), prefix=".solar-", suffix=".svg"
    )
    try:
        with os.fdopen(handle, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
        os.chmod(temporary, 0o644)
        os.replace(temporary, target)
    except BaseException:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def render_svg(
    layout: SolarSystemLayout,
    output_path: str | os.PathLike[str] | None = None,
    *,
    theme: str = DEFAULT_THEME,
    animate: bool = True,
) -> str:
    palette = get_theme(theme)
    parts = [
        _tag(
            "svg",
            {
                "xmlns": "http://www.w3.org/2000/svg",
                "width": layout.width,
                "height": layout.height,
                "viewBox": f"0 0 {layout.width} {layout.height}",
                "role": "img",
                "aria-labelledby": "solar-title solar-desc",
                "font-family": FONT_STACK,
            },
        )
    ]
    parts.extend(_text_tag({"id": "solar-title"}, layout.title))
    parts.extend(_text_tag({"id": "solar-desc"}, _description(layout)))
    parts.extend(_defs(layout, palette, animate))
    parts.append(
        _tag(
            "rect",
            {
                "x": "0",
                "y": "0",
                "width": layout.width,
                "height": layout.height,
                "fill": "url(#bg)",
            },
            close=True,
        )
    )
    parts.extend(_stars(layout, palette, animate))
    parts.extend(_orbits(layout, palette))
    parts.extend(_sun(layout, palette))
    parts.extend(_planets(layout, palette))
    parts.extend(_labels(layout, palette))
    parts.extend(_comets(layout, palette, animate))
    parts.extend(_legend(layout, palette))
    parts.extend(_index(layout, palette))
    parts.extend(_header(layout, palette))
    parts.append("</svg>")

    svg = "\n".join(part for part in parts if part) + "\n"
    if output_path is not None:
        _write_atomic(output_path, svg)
    return svg
