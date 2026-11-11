"""Integration tests for the command-line interface."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ElementTree
from pathlib import Path

import pytest

from generate import _comet_count, load_fixture, main

FIXTURE = {
    "user": {"login": "tester", "name": "Test User", "bio": "Testing things"},
    "repos": [
        {
            "name": "alpha",
            "full_name": "tester/alpha",
            "html_url": "https://github.com/tester/alpha",
            "language": "Python",
            "language_bytes": {"Python": 800},
            "stargazers_count": 3,
        },
        {
            "name": "beta",
            "full_name": "tester/beta",
            "html_url": "https://github.com/tester/beta",
            "language": None,
            "language_bytes": {},
        },
    ],
    "events": [
        {"type": "PushEvent", "repo": {"name": "tester/alpha"}},
        {"type": "PushEvent", "repo": {"name": "tester/alpha"}},
        {"type": "PushEvent", "repo": {"name": "tester/beta"}},
        {"type": "WatchEvent", "repo": {"name": "someone/else"}},
    ],
}


def write_fixture(tmp_path, payload=None):
    target = tmp_path / "fixture.json"
    target.write_text(json.dumps(payload if payload is not None else FIXTURE), encoding="utf-8")
    return target


def test_fixture_mode_writes_svg(tmp_path):
    fixture = write_fixture(tmp_path)
    output = tmp_path / "dist" / "solar.svg"

    code = main(["--fixture", str(fixture), "--output", str(output), "--no-animation"])

    assert code == 0
    assert output.exists()
    svg = output.read_text(encoding="utf-8")
    assert svg.startswith("<svg")
    ElementTree.fromstring(svg)
    assert "animateMotion" not in svg


def test_fixture_loader_parses_repositories(tmp_path):
    fixture = write_fixture(tmp_path)

    user, repositories, events = load_fixture(str(fixture))

    assert user.login == "tester"
    assert [repository.name for repository in repositories] == ["alpha", "beta"]
    assert repositories[0].primary_language == "Python"
    assert repositories[1].primary_language is None
    assert len(events) == 4


def test_comet_count_uses_distinct_push_repositories():
    events = [{"type": "PushEvent", "repo": {"name": f"tester/repo-{index}"}} for index in range(10)]

    assert _comet_count(events, True) == 3
    assert _comet_count(events, False) == 0
    assert _comet_count([{"type": "WatchEvent", "repo": {"name": "a/b"}}], True) == 0


def test_fixture_mode_renders_comets(tmp_path):
    fixture = write_fixture(tmp_path)
    output = tmp_path / "solar.svg"

    assert main(["--fixture", str(fixture), "--output", str(output)]) == 0

    svg = output.read_text(encoding="utf-8")
    assert "animateMotion" in svg


def test_no_comets_flag_removes_animation(tmp_path):
    fixture = write_fixture(tmp_path)
    output = tmp_path / "solar.svg"

    assert main(["--fixture", str(fixture), "--output", str(output), "--no-comets"]) == 0

    svg = output.read_text(encoding="utf-8")
    assert "animateMotion" not in svg


def test_theme_and_size_options(tmp_path):
    fixture = write_fixture(tmp_path)
    output = tmp_path / "solar.svg"

    code = main(
        [
            "--fixture",
            str(fixture),
            "--output",
            str(output),
            "--theme",
            "midnight",
            "--width",
            "960",
            "--height",
            "540",
            "--star-density",
            "low",
        ]
    )

    assert code == 0
    svg = output.read_text(encoding="utf-8")
    assert 'viewBox="0 0 960 540"' in svg


def test_bundled_sample_fixture_renders(tmp_path):
    sample = Path(__file__).parent / "fixtures" / "sample.json"
    output = tmp_path / "sample.svg"

    assert main(["--fixture", str(sample), "--output", str(output)]) == 0

    svg = output.read_text(encoding="utf-8")
    ElementTree.fromstring(svg)
    assert "Shadow-Monarch-33" in svg
    assert "REPOSITORIES" in svg


def test_missing_user_object_is_reported(tmp_path):
    fixture = write_fixture(tmp_path, {"repos": []})
    output = tmp_path / "solar.svg"

    assert main(["--fixture", str(fixture), "--output", str(output)]) == 1
    assert not output.exists()


def test_invalid_json_is_reported(tmp_path):
    target = tmp_path / "broken.json"
    target.write_text("{not json", encoding="utf-8")
    output = tmp_path / "solar.svg"

    assert main(["--fixture", str(target), "--output", str(output)]) == 1
    assert not output.exists()


def test_missing_username_without_fixture_exits_with_usage_error():
    with pytest.raises(SystemExit) as info:
        main(["--output", "out.svg"])

    assert info.value.code == 2


def test_invalid_dimensions_exit_with_usage_error():
    with pytest.raises(SystemExit) as info:
        main(["--username", "someone", "--output", "out.svg", "--width", "100"])

    assert info.value.code == 2
