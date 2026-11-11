"""Shared fixtures for the solar system test suite."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data_models import Commit, Repository, User  # noqa: E402

TINY_PNG = (
    "data:image/png;base64,"
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PzWvWQAAAABJRU5ErkJggg=="
)


@pytest.fixture
def user() -> User:
    return User.from_api(
        {
            "login": "tester",
            "name": "Test User",
            "bio": "Testing things",
            "public_repos": 4,
        }
    )


@pytest.fixture
def avatar_uri() -> str:
    return TINY_PNG


@pytest.fixture
def repo_factory():
    def _make(name, language=None, languages=None, stars=0, size=1000, **kwargs):
        mapping = dict(languages if languages is not None else ({} if language is None else {language: size}))
        payload = {
            "name": name,
            "full_name": f"tester/{name}",
            "html_url": f"https://github.com/tester/{name}",
            "language": language,
            "languages": list(mapping),
            "language_bytes": mapping,
            "stargazers_count": stars,
            "size": size,
            "id": sum(ord(character) for character in name),
        }
        payload.update(kwargs)
        repository = Repository.from_api(payload)
        repository.apply_languages(mapping)
        return repository

    return _make


@pytest.fixture
def repos(repo_factory):
    return [
        repo_factory("alpha", "Python", {"Python": 800, "Shell": 200}, stars=12),
        repo_factory("beta", "Python", {"Python": 400}),
        repo_factory("gamma", "Rust", {"Rust": 1200}, stars=5),
        repo_factory("delta", None, {}),
    ]


@pytest.fixture
def commits() -> list[Commit]:
    return [
        Commit(
            repo="tester/alpha",
            repo_name="alpha",
            sha="a" * 40,
            url="https://github.com/tester/alpha/commit/" + "a" * 40,
            message="Add orbit maths",
            committed_at="2026-11-10T12:00:00Z",
        ),
        Commit(
            repo="tester/alpha",
            repo_name="alpha",
            sha="b" * 40,
            url="https://github.com/tester/alpha/commit/" + "b" * 40,
            message="Older alpha commit",
            committed_at="2026-11-08T12:00:00Z",
        ),
        Commit(
            repo="tester/gamma",
            repo_name="gamma",
            sha="c" * 40,
            url="https://github.com/tester/gamma/commit/" + "c" * 40,
            message="Render rings",
            committed_at="2026-11-09T12:00:00Z",
        ),
        Commit(
            repo="tester/delta",
            repo_name="delta",
            sha="d" * 40,
            url="https://github.com/tester/delta/commit/" + "d" * 40,
            message="Unclassified commit",
            committed_at="2026-11-07T12:00:00Z",
        ),
    ]
