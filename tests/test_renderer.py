"""Tests for the SVG renderer."""

from __future__ import annotations

import dataclasses
import re
import xml.etree.ElementTree as ElementTree

from src.github_client import GitHubClient
from src.layout import build_layout
from src.renderer import render_svg


def render(user, repositories, *, comet_count=2, **options):
    languages = GitHubClient.aggregate_languages(repositories)
    layout = build_layout(user, repositories, languages, comet_count=comet_count, **options)
    return layout, render_svg(layout, animate=options.get("animate", True))


def test_svg_is_valid_xml(user, repos):
    _, svg = render(user, repos)

    assert svg.startswith("<svg")
    root = ElementTree.fromstring(svg)
    assert root.tag.endswith("svg")
    assert 'xmlns="http://www.w3.org/2000/svg"' in svg
    assert "viewBox=" in svg


def test_svg_contains_no_scripts_or_external_assets(user, repos):
    _, svg = render(user, repos)
    lowered = svg.lower()

    assert "<script" not in lowered
    assert "<image" not in lowered
    assert "<foreignobject" not in lowered
    assert "@import" not in lowered
    assert "url(http" not in lowered
    assert "xlink:href" not in lowered


def test_text_is_xml_escaped(user, repos):
    hostile = dataclasses.replace(user, name="<script>alert(1)</script>")

    _, svg = render(hostile, repos)

    assert "<script>alert(1)</script>" not in svg
    assert "&lt;script&gt;" in svg
    ElementTree.fromstring(svg)


def test_only_link_references_point_off_svg(user, repos):
    _, svg = render(user, repos)

    references = re.findall(r'(?:href|src)="([^"]+)"', svg)

    assert references
    for reference in references:
        assert reference.startswith("https://github.com/")


def test_apostrophes_in_font_stack_are_not_escaped(user, repos):
    _, svg = render(user, repos)

    assert "font-family=\"'Segoe UI', Ubuntu, 'Helvetica Neue', Arial, sans-serif\"" in svg


def test_render_is_deterministic(user, repos):
    _, first = render(user, repos)
    _, second = render(user, repos)

    assert first == second


def test_output_file_matches_returned_svg(user, repos, tmp_path):
    languages = GitHubClient.aggregate_languages(repos)
    layout = build_layout(user, repos, languages, comet_count=1)
    target = tmp_path / "nested" / "solar.svg"

    svg = render_svg(layout, target)

    assert target.read_text(encoding="utf-8") == svg


def test_animation_toggle(user, repos):
    languages = GitHubClient.aggregate_languages(repos)
    layout = build_layout(user, repos, languages, comet_count=2)

    animated = render_svg(layout, animate=True)
    static = render_svg(layout, animate=False)

    assert animated.count("animateMotion") == 2
    assert "@keyframes" in animated
    assert "animateMotion" not in static
    assert "@keyframes" not in static
    ElementTree.fromstring(static)


def test_comet_motion_path_is_not_drawn_as_a_visible_curve(user, repos):
    _, svg = render(user, repos)

    assert "<path" not in svg
    assert svg.count('<line x1="') == 2


def test_repository_and_language_links_are_present(user, repos):
    _, svg = render(user, repos)

    assert "https://github.com/tester/alpha" in svg
    assert "tab=repositories&amp;language=python" in svg


def test_empty_profile_renders(user):
    layout, svg = render(user, [], comet_count=0)

    assert layout.planets == ()
    root = ElementTree.fromstring(svg)
    assert root.tag.endswith("svg")
    assert "REPOSITORIES" not in svg
