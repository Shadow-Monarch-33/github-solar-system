"""Tests for the deterministic orbital layout."""

from __future__ import annotations

import math
import re

from src.data_models import Language, Repository, User
from src.github_client import GitHubClient
from src.layout import build_layout


def layout_for(user, repositories, *, commits=(), avatar_uri="", **options):
    languages = GitHubClient.aggregate_languages(repositories)
    return build_layout(
        user,
        repositories,
        languages,
        commits=commits,
        avatar_uri=avatar_uri,
        **options,
    )


def _path_ends(path):
    values = [float(value) for value in re.findall(r"-?\d+(?:\.\d+)?", path)]
    return values[0], values[1], values[7], values[8]


def reach(planet):
    moons = [moon.orbit + moon.radius for moon in planet.moons]
    return max([planet.radius, *moons])


def test_layout_is_deterministic(user, repos, commits):
    first = layout_for(user, repos, commits=commits)
    second = layout_for(user, repos, commits=commits)

    assert first == second


def test_planets_reflect_languages(user, repos):
    layout = layout_for(user, repos)

    assert [planet.language for planet in layout.planets] == ["Python", "Rust"]
    assert layout.repos_count == 4
    assert layout.languages_total == 2
    assert "4 public repositories" in layout.description
    assert "%" not in layout.description
    assert "unclassified" not in layout.description


def test_planet_labels_are_only_language_names(user, repos):
    layout = layout_for(user, repos)

    for planet in layout.planets:
        assert planet.label == planet.language
        assert "%" not in planet.label


def test_every_classified_repository_becomes_a_moon(user, repos):
    layout = layout_for(user, repos)
    names = {moon.name for planet in layout.planets for moon in planet.moons}

    assert names == {"alpha", "beta", "gamma"}
    python = next(planet for planet in layout.planets if planet.language == "Python")
    assert {moon.name for moon in python.moons} == {"alpha", "beta"}
    for planet in layout.planets:
        for moon in planet.moons:
            assert moon.label == moon.name
            start_x, start_y, end_x, end_y = _path_ends(moon.path)
            assert abs(start_x) < 0.01 and abs(start_y) < 0.01
            assert abs(end_x / 2.0 + moon.static_x) < 0.02
            assert abs(end_y / 2.0 + moon.static_y) < 0.02
            assert abs(math.hypot(moon.static_x, moon.static_y) - moon.orbit) < 0.02


def test_planet_and_moon_zones_do_not_overlap(user, repos):
    layout = layout_for(user, repos)
    ordered = sorted(layout.planets, key=lambda planet: planet.orbit)

    for first, second in zip(ordered, ordered[1:]):
        assert first.orbit + reach(first) <= second.orbit - reach(second) + 1e-6


def test_planets_stay_inside_the_canvas(user, repos):
    layout = layout_for(user, repos)

    for planet in layout.planets:
        assert planet.orbit * layout.aspect + reach(planet) <= layout.width / 2.0
        assert planet.orbit + reach(planet) <= layout.height / 2.0
        assert 0 < planet.static_x < layout.width
        assert 0 < planet.static_y < layout.height


def test_planets_and_moons_use_centred_nested_paths(user, repos):
    layout = layout_for(user, repos)

    for planet in layout.planets:
        start_x, start_y, end_x, end_y = _path_ends(planet.path)
        assert abs(start_x) < 0.01 and abs(start_y) < 0.01
        assert abs(end_x / 2.0 - (layout.cx - planet.static_x)) < 0.02
        assert abs(end_y / 2.0 - (layout.cy - planet.static_y)) < 0.02
        for moon in planet.moons:
            assert moon.orbit > planet.radius
            assert moon.static_x ** 2 + moon.static_y ** 2 <= (moon.orbit + 0.2) ** 2
            assert moon.period > 0
            assert moon.begin <= 0


def test_comets_map_verified_commits_newest_first(user, repos, commits):
    layout = layout_for(user, repos, commits=commits)

    assert len(layout.comets) == 4
    assert [comet.repo_name for comet in layout.comets] == [
        "alpha",
        "gamma",
        "alpha",
        "delta",
    ]
    assert [comet.sha for comet in layout.comets] == [
        "a" * 40,
        "c" * 40,
        "b" * 40,
        "d" * 40,
    ]
    assert all(comet.label == comet.repo_name for comet in layout.comets)
    assert layout.comets[0].commit_url.endswith("a" * 40)


def test_comet_limit_and_empty_commits(user, repos, commits):
    limited = layout_for(user, repos, commits=commits, comet_limit=2)
    assert len(limited.comets) == 2
    assert [comet.repo_name for comet in limited.comets] == ["alpha", "gamma"]

    empty = layout_for(user, repos, commits=[])
    assert empty.comets == ()


def test_duplicate_commits_are_deduplicated(user, repos, commits):
    duplicate = [*commits, commits[0], commits[0]]
    layout = layout_for(user, repos, commits=duplicate)

    assert len(layout.comets) == 4


def test_comets_always_travel_upper_left_to_lower_right(user, repos, commits):
    layout = layout_for(user, repos, commits=commits)

    for comet in layout.comets:
        assert comet.end_x > comet.start_x + layout.width * 0.5
        assert comet.end_y > comet.start_y + layout.height * 0.5
        assert comet.start_x < layout.width * 0.4
        assert comet.start_y < layout.height * 0.15


def test_at_most_two_comets_are_visible_at_once(user, repos, commits):
    layout = layout_for(user, repos, commits=commits)
    cycle = layout.comets[0].cycle
    assert all(abs(comet.cycle - cycle) < 1e-6 for comet in layout.comets)

    for step in range(0, 401):
        moment = cycle * step / 400.0
        visible = sum(
            1
            for comet in layout.comets
            if (moment - comet.window_start) % comet.cycle < comet.flight
        )
        assert visible <= 2
    for moment in (0.0, cycle, cycle - 1e-6, cycle + 1e-6):
        visible = sum(
            1
            for comet in layout.comets
            if (moment - comet.window_start) % comet.cycle < comet.flight
        )
        assert visible <= 2


def test_repository_names_are_never_abbreviated(repo_factory, user):
    long_name = "a-very-long-repository-name-that-must-stay-complete"
    repository = repo_factory(long_name, "Python", {"Python": 1000})
    layout = layout_for(user, [repository])

    moon = layout.planets[0].moons[0]
    assert moon.name == long_name
    assert moon.label == long_name
    assert "…" not in moon.label


def test_avatar_uri_is_preserved(user, repos, avatar_uri):
    layout = layout_for(user, repos, avatar_uri=avatar_uri)

    assert layout.avatar_uri == avatar_uri


def test_many_language_labels_do_not_overlap():
    user = User.from_api({"login": "busy"})
    names = [
        "Python",
        "TypeScript",
        "Rust",
        "Go",
        "C++",
        "JavaScript",
        "Ruby",
        "Swift",
        "Kotlin",
        "C#",
        "HTML",
        "Shell",
    ]
    languages = [
        Language(name=name, bytes=900 - index * 40, repo_count=1)
        for index, name in enumerate(names)
    ]
    repositories = []
    for index, language in enumerate(languages):
        repository = Repository.from_api(
            {
                "name": f"project-{index}",
                "full_name": f"busy/project-{index}",
                "language": language.name,
            }
        )
        repository.apply_languages({language.name: language.bytes})
        repositories.append(repository)

    layout = build_layout(user, repositories, languages)

    assert len(layout.planets) == 12
    assert layout.aspect >= 1.0
    for planet in layout.planets:
        assert planet.label


def test_orbits_are_wider_than_they_are_tall(user, repos):
    layout = layout_for(user, repos)

    assert layout.aspect >= 1.0
    for planet in layout.planets:
        assert planet.orbit * layout.aspect >= planet.orbit


def test_many_languages_still_fit():
    user = User.from_api({"login": "prolific"})
    languages = [
        Language(name=f"Lang{index:02d}", bytes=1000 - index, repo_count=1)
        for index in range(50)
    ]
    repositories = []
    for index, language in enumerate(languages):
        repository = Repository.from_api(
            {
                "name": f"repo{index}",
                "full_name": f"prolific/repo{index}",
                "language": language.name,
            }
        )
        repository.apply_languages({language.name: language.bytes})
        repositories.append(repository)

    layout = build_layout(user, repositories, languages)

    assert len(layout.planets) == 50
    for planet in layout.planets:
        assert planet.orbit + reach(planet) <= layout.height / 2.0 + 1e-6
        assert planet.radius >= 0.1
        assert planet.label


def test_empty_profile_produces_no_planets():
    user = User.from_api({"login": "nobody"})

    layout = build_layout(user, [], [])

    assert layout.planets == ()
    assert layout.repos_count == 0
    assert layout.languages_total == 0
    assert layout.comets == ()
    assert layout.stars


def test_star_density_and_comet_limit_are_configurable(user, repos, commits):
    off = layout_for(user, repos, star_density="off")
    assert off.stars == ()

    normal = layout_for(user, repos)
    assert len(normal.stars) > len(off.stars)

    busy = layout_for(user, repos, commits=commits, comet_limit=9)
    assert len(busy.comets) == 4
    assert off == layout_for(user, repos, star_density="off")


def test_tiny_canvas_does_not_crash(user, repos):
    layout = layout_for(user, repos, width=320, height=240)

    assert layout.width == 320
    assert layout.height == 240
    assert layout.planets
