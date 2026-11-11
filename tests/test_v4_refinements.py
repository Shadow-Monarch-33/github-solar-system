"""Tests for GitHub Solar System V4 — Configurable Comets & Rounded Frame."""

import math
import subprocess
import sys
import xml.etree.ElementTree as ElementTree
from pathlib import Path

import pytest

from generate import build_parser, main
from src.data_models import Commit, Language, Repository, User
from src.github_client import GitHubClient
from src.layout import (
    DEFAULT_COMET_FLIGHT,
    DEFAULT_COMET_SPACING,
    DEFAULT_MAX_ACTIVE_COMETS,
    build_layout,
)
from src.renderer import render_svg


@pytest.fixture
def test_user():
    return User.from_api({"login": "test-v4-user"})


@pytest.fixture
def multi_repos():
    repos = [
        Repository.from_api({"name": f"repo-{i}", "full_name": f"test-v4-user/repo-{i}", "language": "TypeScript"})
        for i in range(5)
    ]
    for r in repos:
        r.apply_languages({"TypeScript": 500})
    return repos


@pytest.fixture
def multi_commits():
    return [
        Commit(
            repo=f"test-v4-user/repo-{i}",
            repo_name=f"repo-{i}",
            sha=f"{i:x}" * 40,
            committed_at=f"2026-11-10T1{i}:00:00Z",
        )
        for i in range(5)
    ]


def test_cli_default_comet_arguments():
    """Verify default comet arguments in CLI parser."""
    parser = build_parser()
    args = parser.parse_args(["--username", "test", "--output", "dummy.svg"])
    assert args.comet_flight == DEFAULT_COMET_FLIGHT == 9.0
    assert args.comet_spacing == DEFAULT_COMET_SPACING == 3.5
    assert args.max_active_comets == DEFAULT_MAX_ACTIVE_COMETS == 3


def test_cli_custom_comet_arguments(tmp_path):
    """Verify custom comet arguments are parsed and applied."""
    out = tmp_path / "custom.svg"
    code = main([
        "--fixture", "tests/fixtures/sample.json",
        "--output", str(out),
        "--comet-flight", "8.0",
        "--comet-spacing", "4.0",
        "--max-active-comets", "2",
    ])
    assert code == 0
    assert out.exists()


@pytest.mark.parametrize("flight,spacing,max_active", [
    (10.0, 3.0, 2),  # ceil(10/3) = 4 > 2
    (9.0, 3.5, 2),   # ceil(9/3.5) = 3 > 2
    (12.0, 2.0, 3),  # ceil(12/2) = 6 > 3
])
def test_cli_rejects_incompatible_comet_timing(flight, spacing, max_active, tmp_path):
    """Verify CLI rejects timing where active comets would exceed max-active-comets."""
    out = tmp_path / "incompatible.svg"
    with pytest.raises(SystemExit):
        main([
            "--fixture", "tests/fixtures/sample.json",
            "--output", str(out),
            "--comet-flight", str(flight),
            "--comet-spacing", str(spacing),
            "--max-active-comets", str(max_active),
        ])


@pytest.mark.parametrize("invalid_args", [
    ["--comet-flight", "-1"],
    ["--comet-flight", "0"],
    ["--comet-spacing", "-0.5"],
    ["--comet-spacing", "0"],
    ["--max-active-comets", "0"],
    ["--max-active-comets", "-2"],
])
def test_cli_rejects_invalid_numeric_values(invalid_args, tmp_path):
    """Verify CLI rejects non-positive or non-finite values."""
    out = tmp_path / "invalid.svg"
    with pytest.raises(SystemExit):
        main([
            "--fixture", "tests/fixtures/sample.json",
            "--output", str(out),
            *invalid_args,
        ])


def test_build_layout_validation(test_user, multi_repos):
    """Verify build_layout validates comet parameters."""
    languages = GitHubClient.aggregate_languages(multi_repos)

    with pytest.raises(ValueError, match="comet_flight must be a positive finite number"):
        build_layout(test_user, multi_repos, languages, comet_flight=-5.0)

    with pytest.raises(ValueError, match="comet_spacing must be a positive finite number"):
        build_layout(test_user, multi_repos, languages, comet_spacing=0.0)

    with pytest.raises(ValueError, match="max_active_comets must be an integer >= 1"):
        build_layout(test_user, multi_repos, languages, max_active_comets=0)

    with pytest.raises(ValueError, match="exceeding max_active_comets"):
        build_layout(
            test_user, multi_repos, languages,
            comet_flight=9.0, comet_spacing=2.0, max_active_comets=2
        )


def test_up_to_three_simultaneous_comets(test_user, multi_repos, multi_commits):
    """Verify default timing allows 2-3 simultaneous comets without ever exceeding 3."""
    languages = GitHubClient.aggregate_languages(multi_repos)
    layout = build_layout(
        test_user, multi_repos, languages,
        commits=multi_commits,
        comet_limit=5,
    )
    assert len(layout.comets) == 5
    cycle = layout.comets[0].cycle

    active_counts = []
    # Sample 1000 points across the cycle including loop boundary
    for step in range(1000):
        t = cycle * step / 1000.0
        vis = sum(
            1 for c in layout.comets
            if (t - c.window_start) % c.cycle < c.flight
        )
        assert vis <= 3
        active_counts.append(vis)

    # Verify that during active periods, 2 or 3 comets are visible
    assert 3 in active_counts
    assert 2 in active_counts


def test_comet_spatial_lane_separation(test_user, multi_repos, multi_commits):
    """Verify simultaneously active comets are placed in distinct vertical lanes."""
    languages = GitHubClient.aggregate_languages(multi_repos)
    layout = build_layout(
        test_user, multi_repos, languages,
        commits=multi_commits,
        comet_limit=5,
        max_active_comets=3,
    )
    # Check that adjacent comets (0, 1, 2) which can be simultaneously active
    # spawn in distinct vertical regions
    for i in range(len(layout.comets) - 2):
        y0 = layout.comets[i].start_y
        y1 = layout.comets[i + 1].start_y
        y2 = layout.comets[i + 2].start_y
        # All three must have distinct spawn heights
        assert abs(y0 - y1) >= 15.0
        assert abs(y1 - y2) >= 15.0
        assert abs(y0 - y2) >= 15.0


def test_rounded_corners_and_subtle_border(test_user, multi_repos, multi_commits):
    """Verify 16px corner radius clipPath and 1px 0.35 opacity inset border."""
    languages = GitHubClient.aggregate_languages(multi_repos)
    layout = build_layout(
        test_user, multi_repos, languages,
        commits=multi_commits,
        width=1200,
        height=675,
    )
    svg = render_svg(layout, animate=True)
    root = ElementTree.fromstring(svg)

    # 1. Verify clipPath definition exists with rx="16" ry="16"
    clip = root.find(".//{http://www.w3.org/2000/svg}clipPath[@id='roundedFrame']")
    assert clip is not None
    clip_rect = clip.find("{http://www.w3.org/2000/svg}rect")
    assert clip_rect is not None
    assert clip_rect.get("rx") == "16"
    assert clip_rect.get("ry") == "16"
    assert clip_rect.get("width") == "1200"
    assert clip_rect.get("height") == "675"

    # 2. Verify scene elements are wrapped in a group with clip-path="url(#roundedFrame)"
    scene_g = root.find(".//{http://www.w3.org/2000/svg}g[@clip-path='url(#roundedFrame)']")
    assert scene_g is not None

    # Inside scene_g, background rect is present
    bg_rect = scene_g.find("{http://www.w3.org/2000/svg}rect")
    assert bg_rect is not None
    assert bg_rect.get("fill") == "#000000"

    # 3. Verify subtle white inset border
    border = root.find(".//{http://www.w3.org/2000/svg}rect[@class='frame-border']")
    assert border is not None
    assert border.get("x") == "0.5"
    assert border.get("y") == "0.5"
    assert border.get("width") == "1199"
    assert border.get("height") == "674"
    assert border.get("rx") == "15.5"
    assert border.get("ry") == "15.5"
    assert border.get("fill") == "none"
    assert border.get("stroke") == "#ffffff"
    assert border.get("stroke-width") == "1"
    assert border.get("stroke-opacity") == "0.35"


def test_static_svg_also_has_rounded_corners_and_border(test_user, multi_repos):
    """Verify static SVG (animate=False) also gets clipPath and border."""
    languages = GitHubClient.aggregate_languages(multi_repos)
    layout = build_layout(test_user, multi_repos, languages, width=800, height=500)
    svg = render_svg(layout, animate=False)
    root = ElementTree.fromstring(svg)

    clip = root.find(".//{http://www.w3.org/2000/svg}clipPath[@id='roundedFrame']")
    assert clip is not None

    scene_g = root.find(".//{http://www.w3.org/2000/svg}g[@clip-path='url(#roundedFrame)']")
    assert scene_g is not None

    border = root.find(".//{http://www.w3.org/2000/svg}rect[@class='frame-border']")
    assert border is not None
    assert border.get("width") == "799"
    assert border.get("height") == "499"
    assert border.get("rx") == "15.5"
    assert border.get("ry") == "15.5"


def test_workflow_has_v4_comet_arguments():
    """Verify .github/workflows/update.yml contains the V4 comet arguments."""
    workflow = Path(".github/workflows/update.yml").read_text(encoding="utf-8")
    assert "--comet-flight 9" in workflow
    assert "--comet-spacing 3.5" in workflow
    assert "--max-active-comets 3" in workflow


def test_orbit_stroke_visibility_and_dimensions(test_user, multi_repos):
    """Verify orbital paths are 1.2px stroke-width and 0.40 opacity."""
    languages = GitHubClient.aggregate_languages(multi_repos)
    layout = build_layout(test_user, multi_repos, languages)
    svg = render_svg(layout, animate=True)
    root = ElementTree.fromstring(svg)

    orbits_group = root.find(".//{http://www.w3.org/2000/svg}g[@class='orbits']")
    assert orbits_group is not None
    ellipses = orbits_group.findall("{http://www.w3.org/2000/svg}ellipse")
    assert len(ellipses) == len(layout.planets)
    for ellipse in ellipses:
        assert ellipse.get("stroke") == "#ffffff"
        assert ellipse.get("stroke-width") == "1.2"
        assert ellipse.get("stroke-opacity") == "0.40"


def test_improved_star_visibility_radii_and_opacities(test_user, multi_repos):
    """Verify improved starfield radii (>=0.8px, up to 1.8px) and higher opacities."""
    languages = GitHubClient.aggregate_languages(multi_repos)
    layout = build_layout(test_user, multi_repos, languages)
    assert len(layout.stars) > 0

    radii = [star.radius for star in layout.stars]
    opacities = [star.opacity for star in layout.stars]

    # Minimum radius >= 0.8px
    assert min(radii) >= 0.80
    # Maximum radius up to 1.8px
    assert max(radii) <= 1.80
    assert any(r >= 1.30 for r in radii)

    # Opacities
    assert min(opacities) >= 0.35
    assert max(opacities) <= 0.95
    # Average opacity is significantly higher than old 0.43
    avg_opacity = sum(opacities) / len(opacities)
    assert avg_opacity >= 0.50

    # Verify distribution tiers: most stars in 0.35-0.70, some brighter in 0.80-0.95
    tier_mid = [op for op in opacities if 0.35 <= op <= 0.70]
    tier_bright = [op for op in opacities if 0.80 <= op <= 0.95]
    assert len(tier_mid) > len(tier_bright)
    assert len(tier_bright) > 0

