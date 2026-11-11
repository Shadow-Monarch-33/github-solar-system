"""Tests for the SVG renderer."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ElementTree

from src.github_client import GitHubClient
from src.layout import build_layout
from src.renderer import render_svg


def render(user, repositories, *, commits=(), avatar_uri="", comet_limit=2, **options):
    languages = GitHubClient.aggregate_languages(repositories)
    layout = build_layout(
        user,
        repositories,
        languages,
        commits=commits,
        avatar_uri=avatar_uri,
        comet_limit=comet_limit,
        **options,
    )
    return layout, render_svg(layout, animate=options.get("animate", True))


def visible_texts(svg):
    root = ElementTree.fromstring(svg)
    texts = []
    for node in root.iter():
        tag = node.tag.rsplit("}", 1)[-1]
        if tag != "text":
            continue
        if node.get("id") in {"solar-title", "solar-desc"}:
            continue
        texts.append("".join(node.itertext()))
    return texts


def test_svg_is_valid_xml(user, repos, commits, avatar_uri):
    _, svg = render(user, repos, commits=commits, avatar_uri=avatar_uri)

    assert svg.startswith("<svg")
    root = ElementTree.fromstring(svg)
    assert root.tag.endswith("svg")
    assert 'xmlns="http://www.w3.org/2000/svg"' in svg
    assert "viewBox=" in svg


def test_svg_contains_no_scripts_or_external_assets(user, repos, commits, avatar_uri):
    _, svg = render(user, repos, commits=commits, avatar_uri=avatar_uri)
    lowered = svg.lower()

    assert "<script" not in lowered
    assert "<foreignobject" not in lowered
    assert "@import" not in lowered
    assert "url(http" not in lowered
    assert "xlink:href" not in lowered
    assert "javascript:" not in lowered
    for href in re.findall(r'href="([^"]+)"', svg):
        assert href.startswith("data:image/") or href.startswith("https://github.com/")


def test_visible_text_is_only_language_and_repository_names(user, repos, commits, avatar_uri):
    _, svg = render(user, repos, commits=commits, avatar_uri=avatar_uri)
    allowed = {"Python", "Rust", "alpha", "beta", "gamma", "delta", "Test User"}

    for text in visible_texts(svg):
        value = text.strip()
        assert value in allowed or value.startswith("Axiom-"), value


def test_removed_dashboard_text_does_not_remain(user, repos, commits, avatar_uri):
    _, svg = render(user, repos, commits=commits, avatar_uri=avatar_uri)

    assert "REPOSITORIES" not in svg
    assert "GitHub Solar System" not in svg
    assert "Testing things" not in svg
    assert "unclassified" not in svg
    assert "languages ·" not in svg
    for text in visible_texts(svg):
        assert not text.strip().endswith("%")


def test_text_is_xml_escaped(user, repo_factory):
    hostile = repo_factory("<script>", "Python", {"Python": 10})
    languages = GitHubClient.aggregate_languages([hostile])
    layout = build_layout(user, [hostile], languages)
    svg = render_svg(layout)

    assert "<script>" not in svg
    assert "&lt;script&gt;" in svg
    ElementTree.fromstring(svg)


def test_apostrophes_in_font_stack_are_not_escaped(user, repos):
    _, svg = render(user, repos)

    assert "font-family=\"'Avenir Next', 'Segoe UI', Ubuntu, 'Helvetica Neue', Arial, sans-serif\"" in svg


def test_render_is_deterministic(user, repos, commits, avatar_uri):
    _, first = render(user, repos, commits=commits, avatar_uri=avatar_uri)
    _, second = render(user, repos, commits=commits, avatar_uri=avatar_uri)

    assert first == second


def test_output_file_matches_returned_svg(user, repos, commits, tmp_path):
    languages = GitHubClient.aggregate_languages(repos)
    layout = build_layout(user, repos, languages, commits=commits)
    target = tmp_path / "nested" / "solar.svg"

    svg = render_svg(layout, target)

    assert target.read_text(encoding="utf-8") == svg


def test_animation_toggle(user, repos, commits):
    languages = GitHubClient.aggregate_languages(repos)
    layout = build_layout(user, repos, languages, commits=commits)

    animated = render_svg(layout, animate=True)
    static = render_svg(layout, animate=False)

    assert "animateMotion" in animated
    assert "prefers-reduced-motion" in animated
    assert "animateMotion" not in static
    assert "prefers-reduced-motion" not in static
    ElementTree.fromstring(static)


def test_planets_are_nested_parents_of_moons(user, repos, commits):
    _, svg = render(user, repos, commits=commits)
    root = ElementTree.fromstring(svg)

    planet_groups = [
        node
        for node in root.iter()
        if node.tag.endswith("g") and node.get("class") == "planet-motion"
    ]
    assert planet_groups
    moon_count = 0
    for planet in planet_groups:
        moons = [
            node
            for node in planet.iter()
            if node.tag.endswith("g") and node.get("class") == "moon-motion"
        ]
        assert moons
        moon_count += len(moons)
    assert moon_count == 3
    assert svg.count("<animateMotion") == 2 + 3  # planets + moons; comets use animateTransform


def test_comets_are_white_and_diagonal(user, repos, commits):
    _, svg = render(user, repos, commits=commits, comet_limit=4)

    assert svg.count('class="comet"') == 4
    assert svg.count('type="translate"') == 4
    assert svg.count("<animateMotion") == 2 + 3
    assert svg.count('type="rotate"') == 2 * (2 + 3)  # every label ring + upright counter-rotation
    assert 'stroke="#000000"' in svg  # label halo only
    assert 'fill="url(#cometGlow)"' in svg
    assert '#ffffff' in svg
    for forbidden in ("Older alpha commit", "Add orbit maths", "Render rings"):
        assert forbidden not in svg


def test_static_fallback_shows_at_most_two_comets(user, repos, commits):
    _, svg = render(user, repos, commits=commits, comet_limit=4)

    assert svg.count('class="comet-static"') == 2
    assert svg.count('class="comet"') == 4


def test_background_is_pure_black_and_stars_are_white(user, repos):
    _, svg = render(user, repos, commits=())

    assert 'width="1200"' in svg
    assert 'fill="#000000"' in svg
    assert "url(#bg)" not in svg
    assert "nebula" not in svg.lower()
    assert 'class="stars" fill="#ffffff"' in svg
    assert "#03040a" not in svg.lower()


def test_language_colors_survive_on_the_black_background(user, repos):
    layout, svg = render(user, repos, commits=())

    assert layout.planets
    for planet in layout.planets:
        assert planet.color.lower() in svg.lower()


def test_avatar_embedding_and_fallback(user, repos, avatar_uri):
    _, with_avatar = render(user, repos, avatar_uri=avatar_uri)
    _, fallback = render(user, repos, avatar_uri="")

    assert with_avatar.count("<image") == 1
    assert avatar_uri in with_avatar
    assert 'preserveAspectRatio="xMidYMid slice"' in with_avatar
    assert "url(#avatarClip)" in with_avatar

    assert "<image" not in fallback
    assert "url(#sunFallback)" in fallback


def test_empty_profile_renders(user):
    layout, svg = render(user, [], comet_limit=0)

    assert layout.planets == ()
    root = ElementTree.fromstring(svg)
    assert root.tag.endswith("svg")
    assert "REPOSITORIES" not in svg
