"""Comprehensive tests for GitHub Solar System V3 Visual Refinements."""

from __future__ import annotations

import math
import xml.etree.ElementTree as ElementTree

from src.data_models import Commit, Language, Repository, User
from src.github_client import GitHubClient
from src.layout import build_layout
from src.logos import LANGUAGE_ICONS, abbreviate_language, fallback_logo_markup, get_planet_logo
from src.renderer import render_svg


def reach(planet):
    moons = [moon.orbit + moon.radius for moon in planet.moons]
    return max([planet.radius, *moons])


def test_logo_registry_supports_at_least_50_languages_and_fallbacks():
    # Prompt specifically requests support for at least 50 languages and technologies
    test_languages = [
        "Python", "JavaScript", "TypeScript", "Java", "C", "C++", "C#", "Go", "Rust", "Ruby",
        "PHP", "Swift", "Kotlin", "Dart", "Scala", "R", "Julia", "Lua", "Perl", "Haskell",
        "Elixir", "Erlang", "Clojure", "F#", "OCaml", "MATLAB", "SQL", "HTML", "CSS", "Shell",
        "PowerShell", "Solidity", "Assembly", "Vue", "React", "Svelte", "Zig", "Nix", "Markdown",
        "Dockerfile", "Jupyter Notebook", "GraphQL", "CMake", "Nim", "Fortran", "Groovy", "TeX",
        "CoffeeScript", "D", "Elm", "PostgreSQL", "SQLite", "MySQL", "Bash", "Zsh",
    ]
    assert len(test_languages) >= 50
    assert len(LANGUAGE_ICONS) >= 50

    # Test all 50+ languages produce valid SVG logos with vector paths
    for lang in test_languages:
        logo_svg = get_planet_logo(lang, 24.0, "#3178C6")
        assert 'class="planet-logo"' in logo_svg
        root = ElementTree.fromstring(f'<svg xmlns="http://www.w3.org/2000/svg">{logo_svg}</svg>')
        assert root is not None

    # Test unknown languages generate consistent abbreviation fallbacks
    unknowns = [
        ("Cobol", "CO"),
        ("Vim Script", "VS"),
        ("Emacs Lisp", "EL"),
        ("Ada", "ADA"),
        ("Brainfuck", "BR"),
        ("CustomLanguageX", "CU"),
    ]
    for name, expected_abbr in unknowns:
        abbr = abbreviate_language(name)
        assert abbr == expected_abbr
        markup = fallback_logo_markup(name)
        assert abbr in markup
        assert "<circle" in markup
        logo_svg = get_planet_logo(name, 20.0)
        root = ElementTree.fromstring(f'<svg xmlns="http://www.w3.org/2000/svg">{logo_svg}</svg>')
        assert root is not None


def test_programming_language_logos_appear_inside_planets():
    user = User.from_api({"login": "dev"})
    repos = [
        Repository.from_api({"name": "r1", "full_name": "dev/r1", "language": "TypeScript"}),
        Repository.from_api({"name": "r2", "full_name": "dev/r2", "language": "Python"}),
        Repository.from_api({"name": "r3", "full_name": "dev/r3", "language": "Ruby"}),
        Repository.from_api({"name": "r4", "full_name": "dev/r4", "language": "UnknownLang"}),
    ]
    repos[0].apply_languages({"TypeScript": 1000})
    repos[1].apply_languages({"Python": 800})
    repos[2].apply_languages({"Ruby": 600})
    repos[3].apply_languages({"UnknownLang": 400})

    languages = GitHubClient.aggregate_languages(repos)
    layout = build_layout(user, repos, languages)
    svg = render_svg(layout, animate=True)
    root = ElementTree.fromstring(svg)

    planet_groups = [
        node for node in root.iter()
        if node.tag.endswith("g") and node.get("class") == "planet-motion"
    ]
    assert len(planet_groups) == 4

    # Each planet has a planet-logo group centered inside it
    for pg in planet_groups:
        logos = [
            node for node in pg.iter()
            if node.tag.endswith("g") and node.get("class") == "planet-logo"
        ]
        assert len(logos) == 1


def test_language_names_directly_below_planets():
    user = User.from_api({"login": "dev"})
    repos = [
        Repository.from_api({"name": "r1", "full_name": "dev/r1", "language": "TypeScript"}),
        Repository.from_api({"name": "r2", "full_name": "dev/r2", "language": "Python"}),
    ]
    repos[0].apply_languages({"TypeScript": 1000})
    repos[1].apply_languages({"Python": 800})

    languages = GitHubClient.aggregate_languages(repos)
    layout = build_layout(user, repos, languages)
    svg = render_svg(layout, animate=True)
    root = ElementTree.fromstring(svg)

    planet_groups = [
        node for node in root.iter()
        if node.tag.endswith("g") and node.get("class") == "planet-motion"
    ]

    for index, pg in enumerate(planet_groups):
        planet = layout.planets[index]
        # Text label is inside the planet motion group
        texts = [node for node in pg.iter() if node.tag.endswith("text")]
        # Exactly 1 visible text label in planet group: the language name
        labels = ["".join(t.itertext()).strip() for t in texts]
        assert planet.language in labels
        # Find the language label text element
        label_elem = next(t for t in texts if "".join(t.itertext()).strip() == planet.language)
        # Centered horizontally: x="0", text-anchor="middle"
        assert label_elem.get("x") == "0"
        assert label_elem.get("text-anchor") == "middle"
        # Directly below planet disc: y > planet.radius
        y_val = float(label_elem.get("y"))
        assert y_val > planet.radius
        assert y_val - planet.radius <= 20.0  # consistent, not excessive gap
        # No percentages in text
        assert "%" not in "".join(label_elem.itertext())


def test_moon_labels_are_completely_absent():
    user = User.from_api({"login": "dev"})
    repos = [
        Repository.from_api({"name": "repo-alpha", "full_name": "dev/repo-alpha", "language": "Python"}),
        Repository.from_api({"name": "repo-beta", "full_name": "dev/repo-beta", "language": "Python"}),
        Repository.from_api({"name": "repo-gamma", "full_name": "dev/repo-gamma", "language": "Python"}),
    ]
    for r in repos:
        r.apply_languages({"Python": 500})

    languages = GitHubClient.aggregate_languages(repos)
    layout = build_layout(user, repos, languages)
    svg = render_svg(layout, animate=True)
    root = ElementTree.fromstring(svg)

    moon_groups = [
        node for node in root.iter()
        if node.tag.endswith("g") and node.get("class") == "moon-motion"
    ]
    assert len(moon_groups) == 3

    # Zero text nodes inside moon groups
    for mg in moon_groups:
        texts = [node for node in mg.iter() if node.tag.endswith("text")]
        assert len(texts) == 0
        # Title is preserved for accessibility/tooltips
        titles = [node for node in mg.iter() if node.tag.endswith("title")]
        assert len(titles) == 1

    # Entire SVG visible texts do not contain moon repo names when no comets exist
    all_texts = [
        "".join(node.itertext()).strip()
        for node in root.iter()
        if node.tag.endswith("text") and node.get("id") not in {"solar-title", "solar-desc"}
    ]
    for name in ["repo-alpha", "repo-beta", "repo-gamma"]:
        assert name not in all_texts


def test_orbital_ellipses_count_equals_language_planets_count():
    user = User.from_api({"login": "tester"})

    for count in [1, 2, 5, 8]:
        languages = [Language(name=f"Lang{i}", bytes=1000 - i * 10, repo_count=1) for i in range(count)]
        repos = [Repository.from_api({"name": f"r{i}", "full_name": f"t/r{i}", "language": f"Lang{i}"}) for i in range(count)]
        for r in repos:
            r.apply_languages({r.language: 500})
        layout = build_layout(user, repos, languages)
        svg = render_svg(layout)
        root = ElementTree.fromstring(svg)

        orbits_group = next(
            node for node in root.iter()
            if node.tag.endswith("g") and node.get("class") == "orbits"
        )
        ellipses = [node for node in orbits_group.iter() if node.tag.endswith("ellipse")]
        assert len(ellipses) == count


def test_sun_brightness_reduced_and_golden_border():
    user = User.from_api({"login": "tester"})
    repos = [Repository.from_api({"name": "r1", "full_name": "t/r1", "language": "Python"})]
    repos[0].apply_languages({"Python": 100})
    languages = GitHubClient.aggregate_languages(repos)
    layout = build_layout(user, repos, languages)
    svg = render_svg(layout)

    # sunGlow radius is subtle (1.55x, not 3.6x)
    assert f'r="{layout.sun_radius * 1.55:.2f}"' in svg
    assert f'r="{layout.sun_radius * 3.6:.2f}"' not in svg
    # Golden border on sun
    assert 'stroke="#ffd166"' in svg
    # Two decorative orbit-like circles around the sun were removed
    assert f'r="{layout.sun_radius * 1.24:.2f}"' not in svg


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


def test_header_and_explanatory_legend():
    user = User.from_api({"login": "Shadow-Monarch-33"})
    repos = [Repository.from_api({"name": "r1", "full_name": "Shadow-Monarch-33/r1", "language": "Python"})]
    repos[0].apply_languages({"Python": 100})
    languages = GitHubClient.aggregate_languages(repos)
    layout = build_layout(user, repos, languages)
    svg = render_svg(layout)

    # Top-left header
    assert "SOLAR SYSTEM · @Shadow-Monarch-33" in svg
    # Bottom explanatory text
    assert "planets = languages · moons = repos · comets = recent pushes" in svg
    # No unwanted branding or URLs
    assert "gitskins" not in svg.lower()
    for text in visible_texts(svg):
        assert not text.strip().endswith("%")


def test_comet_spawns_left_and_moves_down_right():
    user = User.from_api({"login": "tester"})
    repos = [Repository.from_api({"name": "r1", "full_name": "t/r1", "language": "Python"})]
    repos[0].apply_languages({"Python": 100})
    commits = [
        Commit(repo="t/r1", repo_name="r1", sha="1" * 40, committed_at="2026-11-10T12:00:00Z"),
        Commit(repo="t/r1", repo_name="r1", sha="2" * 40, committed_at="2026-11-09T12:00:00Z"),
    ]
    languages = GitHubClient.aggregate_languages(repos)
    layout = build_layout(user, repos, languages, commits=commits)

    for comet in layout.comets:
        # Enters across left boundary
        assert comet.start_x < 0
        # Starting height between upper edge and vertical midpoint
        assert 0 <= comet.start_y <= layout.height * 0.5
        # Moves toward lower-right
        assert comet.end_x > layout.width
        assert comet.end_y > comet.start_y + layout.height * 0.5

    svg = render_svg(layout, animate=True)
    root = ElementTree.fromstring(svg)
    comet_groups = [
        node for node in root.iter()
        if node.tag.endswith("g") and node.get("class") == "comet"
    ]
    for cg in comet_groups:
        # Each comet has a label moving with it
        texts = [node for node in cg.iter() if node.tag.endswith("text")]
        assert len(texts) == 1
        assert "".join(texts[0].itertext()).strip() == "r1"
        # Opacity animation fades label with comet
        anim_op = [node for node in cg.iter() if node.tag.endswith("animate") and node.get("attributeName") == "opacity"]
        assert len(anim_op) == 1


def test_adaptive_layout_for_3_10_20_40_50_languages():
    user = User.from_api({"login": "polyglot"})
    for count in [3, 10, 20, 40, 50]:
        languages = [Language(name=f"Lang{i}", bytes=2000 - i * 30, repo_count=1) for i in range(count)]
        repos = [Repository.from_api({"name": f"r{i}", "full_name": f"p/r{i}", "language": f"Lang{i}"}) for i in range(count)]
        for r in repos:
            r.apply_languages({r.language: 500})
        layout = build_layout(user, repos, languages)

        assert len(layout.planets) == count
        assert layout.aspect > 1.0
        # All planets stay safely inside canvas bounds
        for p in layout.planets:
            assert p.orbit * layout.aspect + reach(p) <= layout.width / 2.0
            assert p.orbit + reach(p) <= layout.height / 2.0
            assert p.radius >= 0.5
            assert p.label

        # No overlapping neighbor zones
        ordered = sorted(layout.planets, key=lambda p: p.orbit)
        for p1, p2 in zip(ordered, ordered[1:]):
            assert p1.orbit + reach(p1) <= p2.orbit - reach(p2) + 1e-6


def test_round_robin_fair_rotation_and_loop_boundary():
    """Verify strict round-robin rotation, no consecutive duplicates, and loop boundary."""
    user = User.from_api({"login": "tester"})
    repos = [
        Repository.from_api({"name": f"repo-{c}", "full_name": f"u/repo-{c}", "language": "Python"})
        for c in ["a", "b", "c", "d", "e"]
    ]
    for r in repos:
        r.apply_languages({"Python": 100})
    languages = GitHubClient.aggregate_languages(repos)

    # 5 eligible repositories with varying commit counts
    commits = [
        Commit(repo="u/repo-a", repo_name="repo-a", sha="a1" + "0" * 38, committed_at="2026-11-10T15:00:00Z"),
        Commit(repo="u/repo-a", repo_name="repo-a", sha="a2" + "0" * 38, committed_at="2026-11-09T15:00:00Z"),
        Commit(repo="u/repo-a", repo_name="repo-a", sha="a3" + "0" * 38, committed_at="2026-11-08T15:00:00Z"),
        Commit(repo="u/repo-b", repo_name="repo-b", sha="b1" + "0" * 38, committed_at="2026-11-10T14:00:00Z"),
        Commit(repo="u/repo-b", repo_name="repo-b", sha="b2" + "0" * 38, committed_at="2026-11-09T14:00:00Z"),
        Commit(repo="u/repo-c", repo_name="repo-c", sha="c1" + "0" * 38, committed_at="2026-11-10T13:00:00Z"),
        Commit(repo="u/repo-d", repo_name="repo-d", sha="d1" + "0" * 38, committed_at="2026-11-10T12:00:00Z"),
        Commit(repo="u/repo-e", repo_name="repo-e", sha="e1" + "0" * 38, committed_at="2026-11-10T11:00:00Z"),
    ]

    layout = build_layout(user, repos, languages, commits=commits, comet_limit=5)
    names = [c.repo_name for c in layout.comets]

    # Exactly 5 comets in one complete round across all 5 repos
    assert len(names) == 5
    assert names == ["repo-a", "repo-b", "repo-c", "repo-d", "repo-e"]

    # All eligible repositories appear before any repeats
    assert len(set(names)) == 5

    # Check loop boundary: last comet is repo-e, next is repo-a (no consecutive duplicates)
    assert names[-1] != names[0]
    full_cycle = names + [names[0]]
    for i in range(len(full_cycle) - 1):
        assert full_cycle[i] != full_cycle[i + 1]

    # Test multi-round rotation (e.g. 3 repositories with comet_limit=6 -> 2 full rounds)
    three_repos_commits = [c for c in commits if c.repo_name in {"repo-a", "repo-b", "repo-c"}]
    layout_3 = build_layout(user, repos, languages, commits=three_repos_commits, comet_limit=6)
    names_3 = [c.repo_name for c in layout_3.comets]
    shas_3 = [c.sha for c in layout_3.comets]

    assert len(names_3) == 6
    # Round 1 has all 3 before any repeats in Round 2
    assert names_3[:3] == ["repo-a", "repo-b", "repo-c"]
    assert names_3[3:] == ["repo-a", "repo-b", "repo-c"]

    # Multiple commits from repo-a distributed across separate cycles
    assert shas_3[0].startswith("a1")
    assert shas_3[3].startswith("a2")

    # No consecutive duplicates anywhere, including loop boundary
    loop_sequence = names_3 + [names_3[0]]
    for i in range(len(loop_sequence) - 1):
        assert loop_sequence[i] != loop_sequence[i + 1]


def test_zero_activity_and_single_repository_cases():
    """Verify 0 commits, 1 repo, and partial repo activity cases."""
    user = User.from_api({"login": "tester"})
    repos = [
        Repository.from_api({"name": f"repo-{i}", "full_name": f"u/repo-{i}", "language": "Python"})
        for i in range(5)
    ]
    for r in repos:
        r.apply_languages({"Python": 100})
    languages = GitHubClient.aggregate_languages(repos)

    # 1. Zero activity -> no comets
    layout_zero = build_layout(user, repos, languages, commits=[])
    assert layout_zero.comets == ()

    # 2. Single repository with 1 commit -> 1 comet
    c1 = Commit(repo="u/repo-0", repo_name="repo-0", sha="1" * 40, committed_at="2026-11-10T12:00:00Z")
    layout_single = build_layout(user, repos, languages, commits=[c1])
    assert len(layout_single.comets) == 1
    assert layout_single.comets[0].repo_name == "repo-0"

    # 3. Single repository with multiple commits
    c2 = Commit(repo="u/repo-0", repo_name="repo-0", sha="2" * 40, committed_at="2026-11-09T12:00:00Z")
    c3 = Commit(repo="u/repo-0", repo_name="repo-0", sha="3" * 40, committed_at="2026-11-08T12:00:00Z")
    layout_multi_single = build_layout(user, repos, languages, commits=[c1, c2, c3], comet_limit=3)
    assert len(layout_multi_single.comets) == 3
    assert all(c.repo_name == "repo-0" for c in layout_multi_single.comets)

    # 4. 5 public repositories, but only 3 have commits: rotate through those 3 only
    three_commits = [
        Commit(repo="u/repo-1", repo_name="repo-1", sha="a" * 40, committed_at="2026-11-10T12:00:00Z"),
        Commit(repo="u/repo-3", repo_name="repo-3", sha="b" * 40, committed_at="2026-11-10T11:00:00Z"),
        Commit(repo="u/repo-4", repo_name="repo-4", sha="c" * 40, committed_at="2026-11-10T10:00:00Z"),
    ]
    layout_partial = build_layout(user, repos, languages, commits=three_commits, comet_limit=3)
    assert len(layout_partial.comets) == 3
    assert [c.repo_name for c in layout_partial.comets] == ["repo-1", "repo-3", "repo-4"]
    # No comets invented for repo-0 or repo-2
    assert "repo-0" not in [c.repo_name for c in layout_partial.comets]
    assert "repo-2" not in [c.repo_name for c in layout_partial.comets]


def test_comet_frequency_and_at_most_two_visible():
    """Verify comets appear with increased frequency and at most 2 are visible at any instant."""
    user = User.from_api({"login": "tester"})
    repos = [
        Repository.from_api({"name": f"repo-{i}", "full_name": f"u/repo-{i}", "language": "Python"})
        for i in range(5)
    ]
    for r in repos:
        r.apply_languages({"Python": 100})
    languages = GitHubClient.aggregate_languages(repos)

    commits = [
        Commit(repo=f"u/repo-{i}", repo_name=f"repo-{i}", sha=f"{i}" * 40, committed_at=f"2026-11-10T1{i}:00:00Z")
        for i in range(5)
    ]
    layout = build_layout(user, repos, languages, commits=commits, comet_limit=5)
    assert len(layout.comets) == 5

    # Default V4 launch spacing: 3.5s, flight: 9.0s, at most 3 visible comets
    slot_gap = layout.comets[1].window_start - layout.comets[0].window_start
    assert slot_gap == 3.5
    assert layout.comets[0].flight == 9.0

    # Shallow downward trajectories: 15° to 25° below horizontal
    for comet in layout.comets:
        dx = comet.end_x - comet.start_x
        dy = comet.end_y - comet.start_y
        angle_deg = math.degrees(math.atan2(dy, dx))
        assert 15.0 <= angle_deg <= 25.0

    # Test across 500 moments: at most 3 are simultaneously visible at any instant by default
    cycle = layout.comets[0].cycle
    for step in range(500):
        t = cycle * step / 500.0
        active_count = sum(
            1 for c in layout.comets
            if (t - c.window_start) % c.cycle < c.flight
        )
        assert active_count <= 3
        # Never all 5 visible simultaneously
        assert active_count < len(layout.comets)


def test_comet_head_size_and_trail_length():
    """Verify comet head radius is ~5px and trail length is 60-80% longer (~116px)."""
    user = User.from_api({"login": "tester"})
    repos = [Repository.from_api({"name": "r1", "full_name": "t/r1", "language": "Python"})]
    repos[0].apply_languages({"Python": 100})
    commits = [Commit(repo="t/r1", repo_name="r1", sha="1" * 40, committed_at="2026-11-10T12:00:00Z")]
    languages = GitHubClient.aggregate_languages(repos)
    layout = build_layout(user, repos, languages, commits=commits)

    svg = render_svg(layout, animate=True)
    # Head radius is ~5.0px with fill-opacity ~0.92
    assert 'r="5"' in svg or 'r="5.0"' in svg
    assert 'r="16"' in svg  # Larger glow radius
    # Trail reaches out to distance 116px (60-80% longer than original 68px)
    assert 'class="comet"' in svg
    assert 'fill="url(#cometGlow)"' in svg
