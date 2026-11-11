"""Integration tests for the command-line interface."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ElementTree
from pathlib import Path

import pytest

from generate import load_fixture, main

TINY_PNG = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PzWvWQAAAABJRU5ErkJggg=="
)

FIXTURE = {
    "user": {"login": "tester", "name": "Test User", "bio": "Testing things"},
    "avatar_data_uri": TINY_PNG,
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
    "commits": [
        {
            "repo": "tester/alpha",
            "repo_name": "alpha",
            "sha": "a" * 40,
            "html_url": "https://github.com/tester/alpha/commit/" + "a" * 40,
            "message": "Add orbits",
            "committed_at": "2026-11-10T12:00:00Z",
        },
        {
            "repo": "tester/alpha",
            "repo_name": "alpha",
            "sha": "b" * 40,
            "html_url": "https://github.com/tester/alpha/commit/" + "b" * 40,
            "message": "Older",
            "committed_at": "2026-11-08T12:00:00Z",
        },
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


def test_fixture_loader_parses_repositories_commits_and_avatar(tmp_path):
    fixture = write_fixture(tmp_path)

    data = load_fixture(str(fixture))

    assert data.user.login == "tester"
    assert [repository.name for repository in data.repositories] == ["alpha", "beta"]
    assert data.repositories[0].primary_language == "Python"
    assert data.repositories[1].primary_language is None
    assert len(data.commits) == 2
    assert data.avatar_uri == TINY_PNG


def test_fixture_loader_reads_events_with_commit_payloads(tmp_path):
    payload = {
        "user": {"login": "tester"},
        "repos": [{"name": "alpha", "full_name": "tester/alpha", "language": "Python"}],
        "events": [
            {
                "type": "PushEvent",
                "repo": {"name": "tester/alpha"},
                "payload": {
                    "commits": [
                        {
                            "sha": "e" * 40,
                            "message": "From event",
                            "url": "https://github.com/tester/alpha/commit/" + "e" * 40,
                            "date": "2026-11-10T12:00:00Z",
                        }
                    ]
                },
            }
        ],
    }
    fixture = write_fixture(tmp_path, payload)

    data = load_fixture(str(fixture))

    assert len(data.commits) == 1
    assert data.commits[0].repo == "tester/alpha"


def test_fixture_mode_renders_comets_and_avatar(tmp_path):
    fixture = write_fixture(tmp_path)
    output = tmp_path / "solar.svg"

    assert main(["--fixture", str(fixture), "--output", str(output)]) == 0

    svg = output.read_text(encoding="utf-8")
    assert "animateMotion" in svg
    assert 'class="comet"' in svg
    assert TINY_PNG in svg


def test_no_comets_flag_removes_comet_scene(tmp_path):
    fixture = write_fixture(tmp_path)
    output = tmp_path / "solar.svg"

    assert main(["--fixture", str(fixture), "--output", str(output), "--no-comets"]) == 0

    svg = output.read_text(encoding="utf-8")
    assert 'class="comet"' not in svg
    assert 'class="comet-static"' not in svg


def test_no_avatar_flag_uses_fallback_sun(tmp_path):
    fixture = write_fixture(tmp_path)
    output = tmp_path / "solar.svg"

    assert main(["--fixture", str(fixture), "--output", str(output), "--no-avatar"]) == 0

    svg = output.read_text(encoding="utf-8")
    assert "<image" not in svg
    assert "url(#sunFallback)" in svg


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
            "--max-comets",
            "1",
            "--commit-lookback-days",
            "3",
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
    assert "data:image/jpeg;base64," in svg
    assert "REPOSITORIES" not in svg
    assert "GitHub Solar System" not in svg
    assert "Python" in svg
    assert "TypeScript" in svg


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


def test_invalid_commit_options_exit_with_usage_error():
    with pytest.raises(SystemExit) as info:
        main(["--username", "someone", "--output", "out.svg", "--commit-lookback-days", "0"])
    assert info.value.code == 2

    with pytest.raises(SystemExit) as info:
        main(["--username", "someone", "--output", "out.svg", "--max-comets", "-1"])
    assert info.value.code == 2
