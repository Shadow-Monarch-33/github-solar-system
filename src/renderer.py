"""Self-contained SVG renderer for a solar system layout.

The animated scene uses nested SMIL motion: a planet group follows an
elliptical path around the sun, and each moon group follows a circular path
inside that moving planet. Labels are translated with their body but never
rotated, so every name stays upright.
"""

from __future__ import annotations

import math
import os
import tempfile
from pathlib import Path
from xml.sax.saxutils import escape

from .colors import mix, shade
from .layout import Comet, Moon, Planet, SolarSystemLayout
from .logos import get_planet_logo
from .styles import DEFAULT_THEME, get_theme

FONT_STACK = "'Avenir Next', 'Segoe UI', Ubuntu, 'Helvetica Neue', Arial, sans-serif"
MONO_FONT = "'SF Mono', Monaco, 'Fira Code', 'Roboto Mono', 'Cascadia Code', Menlo, Consolas, monospace"
BACKGROUND = "#000000"


def _esc(value: object) -> str:
    return escape(str(value), {'"': "&quot;", "'": "&apos;"})


def _attr(value: object) -> str:
    return escape(str(value), {'"': "&quot;"})


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


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


def _label_attrs(x: float, y: float, size: float, fill: str, anchor: str = "middle") -> dict:
    return {
        "x": _n(x),
        "y": _n(y),
        "text-anchor": anchor,
        "font-size": _n(size),
        "font-weight": "600",
        "letter-spacing": "0.4",
        "fill": fill,
        "paint-order": "stroke",
        "stroke": BACKGROUND,
        "stroke-width": _n(max(1.6, size * 0.24)),
        "stroke-linejoin": "round",
        "stroke-linecap": "round",
    }


def _description(layout: SolarSystemLayout) -> str:
    return layout.description


def _defs(layout: SolarSystemLayout, theme: dict, animate: bool) -> list[str]:
    parts = ["<defs>"]

    parts.append(
        _tag("radialGradient", {"id": "sunGlow", "cx": "0.5", "cy": "0.5", "r": "0.5"})
    )
    parts.append(_tag("stop", {"offset": "0", "stop-color": "#ffd166", "stop-opacity": "0.18"}, close=True))
    parts.append(_tag("stop", {"offset": "0.25", "stop-color": "#ffd166", "stop-opacity": "0.18"}, close=True))
    parts.append(_tag("stop", {"offset": "0.45", "stop-color": "#ffd166", "stop-opacity": "0.13"}, close=True))
    parts.append(_tag("stop", {"offset": "0.65", "stop-color": "#ffd166", "stop-opacity": "0.07"}, close=True))
    parts.append(_tag("stop", {"offset": "0.82", "stop-color": "#ffd166", "stop-opacity": "0.025"}, close=True))
    parts.append(_tag("stop", {"offset": "1", "stop-color": "#ffd166", "stop-opacity": "0"}, close=True))
    parts.append("</radialGradient>")

    parts.append(
        _tag("radialGradient", {"id": "sunFallback", "cx": "0.38", "cy": "0.32", "r": "0.78"})
    )
    parts.append(_tag("stop", {"offset": "0", "stop-color": "#fff7d9"}, close=True))
    parts.append(_tag("stop", {"offset": "0.42", "stop-color": "#ffd27a"}, close=True))
    parts.append(_tag("stop", {"offset": "0.78", "stop-color": "#ff9a3d"}, close=True))
    parts.append(_tag("stop", {"offset": "1", "stop-color": "#d9541b"}, close=True))
    parts.append("</radialGradient>")

    parts.append(
        _tag("radialGradient", {"id": "sunWarm", "cx": "0.5", "cy": "0.5", "r": "0.5"})
    )
    parts.append(_tag("stop", {"offset": "0.75", "stop-color": "#ffc477", "stop-opacity": "0"}, close=True))
    parts.append(_tag("stop", {"offset": "1", "stop-color": "#ff9a3d", "stop-opacity": "0.12"}, close=True))
    parts.append("</radialGradient>")

    parts.append(
        _tag("radialGradient", {"id": "cometGlow", "cx": "0.5", "cy": "0.5", "r": "0.5"})
    )
    parts.append(_tag("stop", {"offset": "0", "stop-color": "#ffffff", "stop-opacity": "0.65"}, close=True))
    parts.append(_tag("stop", {"offset": "0.45", "stop-color": "#ffffff", "stop-opacity": "0.26"}, close=True))
    parts.append(_tag("stop", {"offset": "1", "stop-color": "#ffffff", "stop-opacity": "0"}, close=True))
    parts.append("</radialGradient>")

    parts.append(_tag("clipPath", {"id": "avatarClip", "clipPathUnits": "userSpaceOnUse"}))
    parts.append(
        _tag(
            "circle",
            {"cx": _n(layout.cx), "cy": _n(layout.cy), "r": _n(layout.sun_radius)},
            close=True,
        )
    )
    parts.append("</clipPath>")

    parts.append(_tag("clipPath", {"id": "roundedFrame", "clipPathUnits": "userSpaceOnUse"}))
    parts.append(
        _tag(
            "rect",
            {
                "x": "0",
                "y": "0",
                "width": layout.width,
                "height": layout.height,
                "rx": "16",
                "ry": "16",
            },
            close=True,
        )
    )
    parts.append("</clipPath>")

    for index, planet in enumerate(layout.planets):
        base = planet.color
        parts.append(
            _tag("radialGradient", {"id": f"pg{index}", "cx": "0.35", "cy": "0.30", "r": "0.78"})
        )
        parts.append(_tag("stop", {"offset": "0", "stop-color": shade(base, 1.62)}, close=True))
        parts.append(_tag("stop", {"offset": "0.46", "stop-color": shade(base, 1.08)}, close=True))
        parts.append(_tag("stop", {"offset": "0.82", "stop-color": base}, close=True))
        parts.append(_tag("stop", {"offset": "1", "stop-color": shade(base, 0.28)}, close=True))
        parts.append("</radialGradient>")
        parts.append(
            _tag("radialGradient", {"id": f"ph{index}", "cx": "0.5", "cy": "0.5", "r": "0.5"})
        )
        parts.append(_tag("stop", {"offset": "0", "stop-color": base, "stop-opacity": "0.34"}, close=True))
        parts.append(_tag("stop", {"offset": "0.65", "stop-color": base, "stop-opacity": "0.10"}, close=True))
        parts.append(_tag("stop", {"offset": "1", "stop-color": base, "stop-opacity": "0"}, close=True))
        parts.append("</radialGradient>")

    if animate:
        parts.append(
            "<style>"
            ".tw{animation:twinkle 5.5s ease-in-out infinite}"
            "@keyframes twinkle{0%,100%{opacity:1}50%{opacity:.35}}"
            "@media (prefers-reduced-motion:reduce){"
            ".animated{display:none}"
            ".static-fallback{display:block}"
            ".tw{animation:none}"
            "}"
            "</style>"
        )

    parts.append("</defs>")
    return parts


def _background(layout: SolarSystemLayout, theme: dict) -> list[str]:
    return [
        _tag(
            "rect",
            {
                "x": "0",
                "y": "0",
                "width": layout.width,
                "height": layout.height,
                "fill": "#000000",
            },
            close=True,
        )
    ]


def _stars(layout: SolarSystemLayout, theme: dict) -> list[str]:
    if not layout.stars:
        return []
    parts = [_tag("g", {"class": "stars", "fill": "#ffffff"})]
    for index, star in enumerate(layout.stars):
        delay = round((star.x * 0.013 + star.y * 0.017) % 5.5, 2)
        parts.append(
            _tag(
                "circle",
                {
                    "class": "tw",
                    "cx": _n(star.x),
                    "cy": _n(star.y),
                    "r": _n(star.radius),
                    "fill-opacity": _n(star.opacity),
                    "style": f"animation-delay:-{_n(delay)}s",
                },
                close=True,
            )
        )
    parts.append("</g>")
    return parts


def _orbits(layout: SolarSystemLayout, theme: dict) -> list[str]:
    parts = [_tag("g", {"class": "orbits", "fill": "none"})]
    for planet in layout.planets:
        parts.append(
            _tag(
                "ellipse",
                {
                    "cx": _n(layout.cx),
                    "cy": _n(layout.cy),
                    "rx": _n(planet.orbit * layout.aspect),
                    "ry": _n(planet.orbit),
                    "stroke": "#ffffff",
                    "stroke-width": "1.2",
                    "stroke-opacity": "0.40",
                },
                close=True,
            )
        )
    parts.append("</g>")
    return parts


def _sun_glow(layout: SolarSystemLayout) -> list[str]:
    cx = _n(layout.cx)
    cy = _n(layout.cy)
    glow_radius = layout.sun_radius * 2.8
    return [
        _tag(
            "circle",
            {
                "cx": cx,
                "cy": cy,
                "r": _n(glow_radius),
                "fill": "url(#sunGlow)",
            },
            close=True,
        )
    ]


def _sun(layout: SolarSystemLayout, theme: dict) -> list[str]:
    cx = _n(layout.cx)
    cy = _n(layout.cy)
    radius = layout.sun_radius
    parts = [
        _tag("circle", {"cx": cx, "cy": cy, "r": _n(radius), "fill": "url(#sunFallback)"}, close=True),
    ]
    if layout.avatar_uri:
        parts.append(_tag("g", {"clip-path": "url(#avatarClip)"}))
        parts.append(
            _tag(
                "image",
                {
                    "x": _n(layout.cx - radius),
                    "y": _n(layout.cy - radius),
                    "width": _n(radius * 2),
                    "height": _n(radius * 2),
                    "href": layout.avatar_uri,
                    "preserveAspectRatio": "xMidYMid slice",
                },
                close=True,
            )
        )
        parts.append(
            _tag(
                "circle",
                {"cx": cx, "cy": cy, "r": _n(radius), "fill": "url(#sunWarm)"},
                close=True,
            )
        )
        parts.append("</g>")
    else:
        parts.append(
            _tag(
                "ellipse",
                {
                    "cx": _n(layout.cx - radius * 0.28),
                    "cy": _n(layout.cy - radius * 0.32),
                    "rx": _n(radius * 0.34),
                    "ry": _n(radius * 0.22),
                    "fill": "#ffffff",
                    "fill-opacity": "0.30",
                },
                close=True,
            )
        )
    parts.append(
        _tag(
            "circle",
            {
                "cx": cx,
                "cy": cy,
                "r": _n(radius),
                "fill": "none",
                "stroke": "#ffd166",
                "stroke-width": "1.3",
                "stroke-opacity": "0.75",
            },
            close=True,
        )
    )
    parts.append(
        _tag(
            "circle",
            {
                "cx": cx,
                "cy": cy,
                "r": _n(radius + 1.8),
                "fill": "none",
                "stroke": "#ff9a3d",
                "stroke-width": "0.6",
                "stroke-opacity": "0.25",
            },
            close=True,
        )
    )
    return parts


def _motion(path: str, duration: float, begin: float, *, rotate: bool = False) -> str:
    attrs = {
        "path": path,
        "dur": f"{_n(duration)}s",
        "begin": f"{_n(begin)}s",
        "repeatCount": "indefinite",
        "fill": "freeze",
    }
    if rotate:
        attrs["rotate"] = "auto"
    return _tag("animateMotion", attrs, close=True)





def _moon_group(moon: Moon, theme: dict, animated: bool) -> list[str]:
    parts = [
        _tag("a", {"href": moon.url, "target": "_blank", "rel": "noopener"}),
        _tag(
            "g",
            {
                "class": "moon-motion" if animated else "moon-static",
                "transform": f"translate({_n(moon.static_x)} {_n(moon.static_y)})",
            },
        ),
    ]
    if animated:
        parts.append(_motion(moon.path, moon.period, moon.begin))
    parts.append(_tag("title", {}))
    parts.append(_esc(moon.name))
    parts.append("</title>")
    parts.append(
        _tag(
            "circle",
            {"r": _n(moon.radius * 2.2), "fill": moon.color, "fill-opacity": "0.22"},
            close=True,
        )
    )
    parts.append(_tag("circle", {"r": _n(moon.radius), "fill": moon.color}, close=True))
    parts.append(
        _tag(
            "circle",
            {
                "cx": _n(-moon.radius * 0.28),
                "cy": _n(-moon.radius * 0.30),
                "r": _n(moon.radius * 0.34),
                "fill": "#ffffff",
                "fill-opacity": "0.75",
            },
            close=True,
        )
    )
    parts.append("</g></a>")
    return parts


def _planet_group(planet: Planet, index: int, theme: dict, animated: bool) -> list[str]:
    parts = [
        _tag("a", {"href": planet.url, "target": "_blank", "rel": "noopener"}),
        _tag(
            "g",
            {
                "class": "planet-motion" if animated else "planet-static",
                "transform": f"translate({_n(planet.static_x)} {_n(planet.static_y)})",
            },
        ),
    ]
    if animated:
        parts.append(_motion(planet.path, planet.period, planet.begin))
    parts.append(_tag("title", {}))
    parts.append(_esc(planet.language))
    parts.append("</title>")

    # Subtle circular orbit rings for moons around the parent planet
    drawn_moon_orbits: set[float] = set()
    for moon in planet.moons:
        if moon.orbit not in drawn_moon_orbits:
            drawn_moon_orbits.add(moon.orbit)
            parts.append(
                _tag(
                    "circle",
                    {
                        "r": _n(moon.orbit),
                        "fill": "none",
                        "stroke": "#ffffff",
                        "stroke-width": "0.5",
                        "stroke-opacity": "0.07",
                    },
                    close=True,
                )
            )

    back_moons = [moon for moon in planet.moons if moon.static_y <= 0]
    front_moons = [moon for moon in planet.moons if moon.static_y > 0]
    for moon in back_moons:
        parts.extend(_moon_group(moon, theme, animated))

    parts.append(
        _tag(
            "circle",
            {"r": _n(planet.radius * 2.3), "fill": f"url(#ph{index})"},
            close=True,
        )
    )
    parts.append(
        _tag(
            "circle",
            {
                "r": _n(planet.radius),
                "fill": f"url(#pg{index})",
                "stroke": shade(str(planet.color), 1.25),
                "stroke-width": "0.7",
                "stroke-opacity": "0.32",
            },
            close=True,
        )
    )
    parts.append(
        _tag(
            "ellipse",
            {
                "cx": _n(-planet.radius * 0.27),
                "cy": _n(-planet.radius * 0.33),
                "rx": _n(planet.radius * 0.34),
                "ry": _n(planet.radius * 0.20),
                "fill": "#ffffff",
                "fill-opacity": "0.22",
            },
            close=True,
        )
    )
    parts.append(
        _tag(
            "path",
            {
                "d": (
                    f"M {_n(-planet.radius * 0.92)} {_n(planet.radius * 0.22)} "
                    f"A {_n(planet.radius)} {_n(planet.radius)} 0 0 0 "
                    f"{_n(planet.radius * 0.92)} {_n(planet.radius * 0.20)}"
                ),
                "fill": "none",
                "stroke": shade(str(planet.color), 0.24),
                "stroke-width": "0.7",
                "stroke-opacity": "0.55",
            },
            close=True,
        )
    )

    # Programming language vector logo inside the planet
    parts.append(get_planet_logo(planet.language, planet.radius, planet.color))

    for moon in front_moons:
        parts.extend(_moon_group(moon, theme, animated))

    # Language name directly underneath its planet
    label_gap = max(9.0, min(15.0, planet.radius * 0.35 + 7.0))
    label_y = planet.radius + label_gap
    label_size = max(8.5, min(12.2, planet.radius * 0.4 + 6.0))
    parts.extend(
        _text_tag(
            _label_attrs(0, label_y, label_size, "#ffffff", "middle"),
            planet.language,
        )
    )
    parts.append("</g></a>")
    return parts


def _comet_tail(comet: Comet) -> list[str]:
    dx = comet.end_x - comet.start_x
    dy = comet.end_y - comet.start_y
    length = math.hypot(dx, dy) or 1.0
    unit_x = dx / length
    unit_y = dy / length
    parts: list[str] = []
    # Elongated trail (60-80% longer) with smooth taper and gradual opacity fade
    for distance, radius, opacity in (
        (116.0, 1.2, "0.03"),
        (100.0, 1.5, "0.05"),
        (86.0, 1.9, "0.08"),
        (72.0, 2.3, "0.12"),
        (59.0, 2.8, "0.17"),
        (47.0, 3.3, "0.23"),
        (36.0, 3.8, "0.30"),
        (26.0, 4.3, "0.39"),
        (17.0, 4.7, "0.49"),
        (10.0, 5.0, "0.60"),
        (4.0, 5.2, "0.74"),
    ):
        parts.append(
            _tag(
                "circle",
                {
                    "cx": _n(-unit_x * distance),
                    "cy": _n(-unit_y * distance),
                    "r": _n(radius),
                    "fill": "#ffffff",
                    "fill-opacity": opacity,
                },
                close=True,
            )
        )
    # Larger comet head (radius ~5.0) with stronger white glow
    parts.append(_tag("circle", {"r": "16", "fill": "url(#cometGlow)"}, close=True))
    parts.append(_tag("circle", {"r": "5.0", "fill": "#ffffff", "fill-opacity": "0.92"}, close=True))
    parts.append(_tag("circle", {"r": "2.8", "fill": "#ffffff"}, close=True))
    return parts


def _comet_group(comet: Comet, theme: dict, animated: bool) -> list[str]:
    """A pure-white comet that always travels upper-left to lower-right."""

    label = _text_tag(
        _label_attrs(15, 4, 9.8, "#ffffff", "start"),
        comet.label,
    )

    if not animated:
        parts = [
            _tag("a", {"href": comet.commit_url, "target": "_blank", "rel": "noopener"}),
            _tag(
                "g",
                {
                    "class": "comet-static",
                    "transform": f"translate({_n(comet.static_x)} {_n(comet.static_y)})",
                },
            ),
            _tag("title", {}),
            _esc(comet.repo_name),
            "</title>",
        ]
        parts.extend(_comet_tail(comet))
        parts.extend(label)
        parts.append("</g></a>")
        return parts

    cycle = max(0.001, comet.cycle)
    a = _clamp(comet.window_start / cycle, 0.0, 0.98)
    b = _clamp((comet.window_start + comet.flight) / cycle, a + 0.005, 1.0)
    fade = min(0.035, (b - a) * 0.22)
    start_xy = f"{_n(comet.start_x)} {_n(comet.start_y)}"
    end_xy = f"{_n(comet.end_x)} {_n(comet.end_y)}"
    duration = f"{_n(cycle)}s"

    parts = [
        _tag("a", {"href": comet.commit_url, "target": "_blank", "rel": "noopener"}),
        _tag(
            "g",
            {
                "class": "comet",
                "transform": f"translate({_n(comet.start_x)} {_n(comet.start_y)})",
                "opacity": "0",
            },
        ),
        _tag("title", {}),
        _esc(comet.repo_name),
        "</title>",
        _tag(
            "animateTransform",
            {
                "attributeName": "transform",
                "type": "translate",
                "dur": duration,
                "begin": "0s",
                "repeatCount": "indefinite",
                "calcMode": "linear",
                "keyTimes": f"0;{_n(a)};{_n(b)};1",
                "values": f"{start_xy};{start_xy};{end_xy};{end_xy}",
            },
            close=True,
        ),
        _tag(
            "animate",
            {
                "attributeName": "opacity",
                "dur": duration,
                "begin": "0s",
                "repeatCount": "indefinite",
                "keyTimes": (
                    f"0;{_n(a)};{_n(a + fade)};{_n(b - fade)};{_n(b)};1"
                ),
                "values": "0;0;1;1;0;0",
            },
            close=True,
        ),
    ]
    parts.extend(_comet_tail(comet))
    parts.extend(label)
    parts.append("</g></a>")
    return parts


def _header_text(layout: SolarSystemLayout) -> list[str]:
    attrs = {
        "x": "38",
        "y": "40",
        "font-family": MONO_FONT,
        "font-size": "11.5",
        "font-weight": "500",
        "letter-spacing": "1.4",
        "fill": "#888888",
    }
    content = f"SOLAR SYSTEM · @{layout.user.login}"
    return _text_tag(attrs, content)


def _legend_text(layout: SolarSystemLayout) -> list[str]:
    attrs = {
        "x": _n(layout.width - 38),
        "y": _n(layout.height - 28),
        "text-anchor": "end",
        "font-family": MONO_FONT,
        "font-size": "10.5",
        "font-weight": "400",
        "letter-spacing": "1.2",
        "fill": "#666666",
    }
    content = "planets = languages · moons = repos · comets = recent pushes"
    return _text_tag(attrs, content)


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


def _frame_border(layout: SolarSystemLayout) -> list[str]:
    return [
        _tag(
            "rect",
            {
                "class": "frame-border",
                "x": "0.5",
                "y": "0.5",
                "width": _n(layout.width - 1),
                "height": _n(layout.height - 1),
                "rx": "15.5",
                "ry": "15.5",
                "fill": "none",
                "stroke": "#ffffff",
                "stroke-width": "1",
                "stroke-opacity": "0.35",
            },
            close=True,
        )
    ]


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
    parts.append(_tag("title", {"id": "solar-title"}))
    parts.append(_esc(layout.title))
    parts.append("</title>")
    parts.append(_tag("desc", {"id": "solar-desc"}))
    parts.append(_esc(_description(layout)))
    parts.append("</desc>")
    parts.extend(_defs(layout, palette, animate))
    parts.append(_tag("g", {"clip-path": "url(#roundedFrame)"}))
    parts.extend(_background(layout, palette))
    parts.extend(_stars(layout, palette))
    parts.extend(_sun_glow(layout))
    parts.extend(_orbits(layout, palette))
    parts.extend(_sun(layout, palette))
    parts.extend(_header_text(layout))
    parts.extend(_legend_text(layout))

    if animate:
        parts.append(_tag("g", {"class": "animated"}))
        for index, planet in enumerate(layout.planets):
            parts.extend(_planet_group(planet, index, palette, True))
        for comet in layout.comets:
            parts.extend(_comet_group(comet, palette, True))
        parts.append("</g>")
        parts.append(_tag("g", {"class": "static-fallback", "display": "none"}))
        for index, planet in enumerate(layout.planets):
            parts.extend(_planet_group(planet, index, palette, False))
        for comet in layout.comets[:2]:
            parts.extend(_comet_group(comet, palette, False))
        parts.append("</g>")
    else:
        for index, planet in enumerate(layout.planets):
            parts.extend(_planet_group(planet, index, palette, False))
        for comet in layout.comets[:2]:
            parts.extend(_comet_group(comet, palette, False))

    parts.append("</g>")
    parts.extend(_frame_border(layout))
    parts.append("</svg>")

    svg = "\n".join(part for part in parts if part) + "\n"
    if output_path is not None:
        _write_atomic(output_path, svg)
    return svg
