"""Tests for the deterministic orbital layout."""

from __future__ import annotations

from src.data_models import Language, Repository, User
from src.github_client import GitHubClient
from src.layout import build_layout


def layout_for(user, repositories, **options):
    languages = GitHubClient.aggregate_languages(repositories)
    return build_layout(user, repositories, languages, **options)


def test_layout_is_deterministic(user, repos):
    first = layout_for(user, repos)
    second = layout_for(user, repos)

    assert first == second


def test_planets_reflect_languages(user, repos):
    layout = layout_for(user, repos)

    assert [planet.language for planet in layout.planets] == ["Python", "Rust"]
    assert layout.repos_count == 4
    assert layout.languages_total == 2
    assert "1 unclassified" in layout.meta


def test_every_classified_repository_becomes_a_moon(user, repos):
    layout = layout_for(user, repos)
    names = {moon.name for planet in layout.planets for moon in planet.moons}

    assert names == {"alpha", "beta", "gamma"}
    python = next(planet for planet in layout.planets if planet.language == "Python")
    assert {moon.name for moon in python.moons} == {"alpha", "beta"}


def test_planet_discs_and_moon_zones_do_not_overlap(user, repos):
    layout = layout_for(user, repos)
    ordered = sorted(layout.planets, key=lambda planet: planet.orbit)

    for first, second in zip(ordered, ordered[1:]):
        assert first.orbit + first.reach <= second.orbit - second.reach + 1e-6


def test_planets_stay_inside_the_canvas(user, repos):
    layout = layout_for(user, repos)

    for planet in layout.planets:
        assert planet.orbit + planet.reach <= layout.max_extent + 1e-6
        assert 0 < planet.x < layout.width
        assert 0 < planet.y < layout.height


def test_labels_stay_inside_canvas(user, repos):
    layout = layout_for(user, repos)

    for planet in layout.planets:
        assert 8 <= planet.label.x <= layout.width - 8
        assert 20 <= planet.label.y <= layout.height - 10
        assert planet.label.anchor in {"start", "end"}
        assert planet.label.text.startswith(planet.language)


def label_boxes(layout):
    boxes = []
    for planet in layout.planets:
        if not planet.label.text:
            continue
        width = 6.2 * len(planet.label.text) + 4.0
        if planet.label.anchor == "start":
            boxes.append(
                (planet.label.x, planet.label.y - 12.0, planet.label.x + width, planet.label.y + 3.0)
            )
        else:
            boxes.append(
                (planet.label.x - width, planet.label.y - 12.0, planet.label.x, planet.label.y + 3.0)
            )
    return boxes


def test_labels_do_not_overlap(user, repos):
    boxes = label_boxes(layout_for(user, repos))

    for index, first in enumerate(boxes):
        for second in boxes[index + 1 :]:
            assert (
                first[2] <= second[0]
                or second[2] <= first[0]
                or first[3] <= second[1]
                or second[3] <= first[1]
            )


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
    boxes = label_boxes(layout)

    for index, first in enumerate(boxes):
        for second in boxes[index + 1 :]:
            assert (
                first[2] <= second[0]
                or second[2] <= first[0]
                or first[3] <= second[1]
                or second[3] <= first[1]
            )
    assert layout.aspect >= 1.0


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
        assert planet.orbit + planet.reach <= layout.max_extent + 1e-6
        assert planet.radius >= 0.1


def test_empty_profile_produces_no_planets():
    user = User.from_api({"login": "nobody"})

    layout = build_layout(user, [], [])

    assert layout.planets == ()
    assert layout.repos_count == 0
    assert layout.languages_total == 0
    assert layout.repo_index is None
    assert layout.stars


def test_star_density_and_comets_are_configurable(user, repos):
    off = layout_for(user, repos, star_density="off")
    assert off.stars == ()

    normal = layout_for(user, repos)
    assert len(normal.stars) > len(off.stars)

    busy = layout_for(user, repos, comet_count=9)
    assert len(busy.comets) == 3
    assert off == layout_for(user, repos, star_density="off")


def test_repository_index_lists_every_repository(user, repos):
    layout = layout_for(user, repos)

    assert layout.repo_index is not None
    entries = layout.repo_index.entries
    assert {entry.name for entry in entries} == {"alpha", "beta", "gamma"}
    assert all(entry.display for entry in entries)
    assert all(entry.url.startswith("https://github.com/") for entry in entries)


def test_repository_index_scales_with_repository_count():
    user = User.from_api({"login": "many"})
    languages = [Language(name="Python", bytes=1000, repo_count=60)]
    repositories = []
    for index in range(60):
        repository = Repository.from_api(
            {
                "name": f"project-{index:02d}",
                "full_name": f"many/project-{index:02d}",
                "language": "Python",
            }
        )
        repository.apply_languages({"Python": 1000})
        repositories.append(repository)

    layout = build_layout(user, repositories, languages)

    index = layout.repo_index
    assert index is not None
    assert index.columns * index.rows >= 60
    assert index.columns > 1


def test_extreme_language_count_suppresses_overflow_labels():
    user = User.from_api({"login": "wide"})
    languages = [
        Language(name=f"Lang{index:02d}", bytes=1000 + index, repo_count=1)
        for index in range(50)
    ]
    repositories = []
    for index, language in enumerate(languages):
        repository = Repository.from_api(
            {
                "name": f"repo{index}",
                "full_name": f"wide/repo{index}",
                "language": language.name,
            }
        )
        repository.apply_languages({language.name: language.bytes})
        repositories.append(repository)

    layout = build_layout(user, repositories, languages)

    labelled = [planet for planet in layout.planets if planet.label.text]
    assert len(layout.planets) == 50
    assert 12 <= len(labelled) <= 16
    for planet in labelled:
        assert planet.label.text.startswith(planet.language)


def test_tiny_canvas_does_not_crash(user, repos):
    layout = layout_for(user, repos, width=320, height=240)

    assert layout.width == 320
    assert layout.height == 240
    assert layout.planets
