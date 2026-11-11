"""Shared fixtures for the solar system test suite."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.data_models import Repository, User  # noqa: E402


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
