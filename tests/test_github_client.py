"""Tests for the GitHub REST client."""

from __future__ import annotations

import io
import json
import time
import urllib.error
from email.message import Message

import pytest

from src.data_models import Repository
from src.github_client import GitHubClient, GitHubError


class FakeResponse:
    def __init__(self, payload, headers=None):
        if isinstance(payload, bytes):
            self._body = payload
        else:
            self._body = json.dumps(payload).encode("utf-8")
        self.headers = headers if headers is not None else Message()
        self.status = 200

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


def make_client(responses, *, max_retries=0):
    client = GitHubClient(max_retries=max_retries, sleeper=lambda _seconds: None)
    client.calls = []
    queue = list(responses)

    def fake_open(request, timeout=None):
        client.calls.append(request.full_url)
        if not queue:
            raise AssertionError("no more fake responses queued")
        item = queue.pop(0)
        if isinstance(item, Exception):
            raise item
        if isinstance(item, FakeResponse):
            return item
        return FakeResponse(item)

    client._open = fake_open
    return client


def link_header(next_url: str) -> Message:
    headers = Message()
    headers["Link"] = f'<{next_url}>; rel="next"'
    return headers


def test_get_user_parses_profile():
    client = make_client(
        [{"login": "octocat", "name": "The Octocat", "public_repos": 8, "followers": 100}]
    )

    user = client.get_user("octocat")

    assert user.login == "octocat"
    assert user.name == "The Octocat"
    assert user.public_repos == 8
    assert user.followers == 100
    assert client.calls == ["https://api.github.com/users/octocat"]


def test_get_repos_follows_pagination_links():
    client = make_client(
        [
            FakeResponse(
                [{"name": "one", "full_name": "octocat/one"}],
                headers=link_header("https://api.github.com/users/octocat/repos?page=2"),
            ),
            FakeResponse([{"name": "two", "full_name": "octocat/two"}]),
        ]
    )

    repositories = client.get_repos("octocat", fetch_languages=False)

    assert [repository.name for repository in repositories] == ["one", "two"]
    assert client.calls[0] == (
        "https://api.github.com/users/octocat/repos"
        "?type=owner&sort=pushed&direction=desc&per_page=100"
    )
    assert client.calls[1] == "https://api.github.com/users/octocat/repos?page=2"


def test_http_error_reports_status():
    error = urllib.error.HTTPError(
        "https://api.github.com/users/missing", 404, "Not Found", Message(), io.BytesIO(b"{}")
    )
    client = make_client([error])

    with pytest.raises(GitHubError) as info:
        client.get_user("missing")

    assert info.value.status == 404


def test_rate_limited_403_is_retried():
    headers = Message()
    headers["X-RateLimit-Remaining"] = "0"
    headers["X-RateLimit-Reset"] = "0"
    error = urllib.error.HTTPError(
        "https://api.github.com/users/octocat", 403, "Forbidden", headers, io.BytesIO(b"{}")
    )
    client = make_client([error, {"login": "octocat"}], max_retries=1)

    user = client.get_user("octocat")

    assert user.login == "octocat"
    assert len(client.calls) == 2


def test_far_future_rate_limit_fails_fast():
    headers = Message()
    headers["X-RateLimit-Remaining"] = "0"
    headers["X-RateLimit-Reset"] = str(int(time.time()) + 3600)
    error = urllib.error.HTTPError(
        "https://api.github.com/users/octocat", 403, "Forbidden", headers, io.BytesIO(b"{}")
    )
    client = make_client([error], max_retries=3)

    with pytest.raises(GitHubError) as info:
        client.get_user("octocat")

    assert info.value.status == 403
    assert len(client.calls) == 1


def test_network_error_is_retried():
    client = make_client(
        [urllib.error.URLError("network down"), {"login": "octocat"}], max_retries=1
    )

    user = client.get_user("octocat")

    assert user.login == "octocat"
    assert len(client.calls) == 2


def test_invalid_json_is_rejected():
    client = make_client([FakeResponse(b"not json")])

    with pytest.raises(GitHubError):
        client.get_user("octocat")


def test_forks_and_archived_are_filtered_by_default():
    payload = [
        {"name": "live", "full_name": "tester/live"},
        {"name": "old-fork", "full_name": "tester/old-fork", "fork": True},
        {"name": "museum", "full_name": "tester/museum", "archived": True},
    ]
    client = make_client([payload])

    default = client.get_repos("tester", fetch_languages=False)

    assert [repository.name for repository in default] == ["live"]

    client = make_client([payload])
    inclusive = client.get_repos(
        "tester", fetch_languages=False, include_forks=True, include_archived=True
    )

    assert [repository.name for repository in inclusive] == ["live", "old-fork", "museum"]


def test_language_fetch_failure_is_isolated():
    error = urllib.error.HTTPError(
        "https://api.github.com/repos/tester/one/languages",
        500,
        "Server Error",
        Message(),
        io.BytesIO(b"{}"),
    )
    client = make_client(
        [[{"name": "one", "full_name": "tester/one", "language": "Python"}], error]
    )

    repositories = client.get_repos("tester")

    assert repositories[0].language_bytes == {}
    assert repositories[0].primary_language == "Python"


def test_malformed_language_payload_yields_empty_mapping():
    client = make_client(
        [[{"name": "one", "full_name": "tester/one"}], ["not", "a", "dict"]]
    )

    repositories = client.get_repos("tester")

    assert repositories[0].language_bytes == {}


def test_aggregate_languages_weights_by_primary_language(repo_factory):
    repositories = [
        repo_factory("a", "Python", {"Python": 800, "Shell": 200}),
        repo_factory("b", "Python", {"Python": 400}),
        repo_factory("c", "Rust", {"Rust": 1200}),
    ]

    languages = GitHubClient.aggregate_languages(repositories)

    assert [language.name for language in languages] == ["Python", "Rust"]
    assert languages[0].repo_count == 2
    assert languages[0].bytes == 1200
    assert languages[1].bytes == 1200


def test_aggregate_languages_falls_back_to_repo_size(repo_factory):
    repository = repo_factory("solo", "Go", {}, size=2048)

    languages = GitHubClient.aggregate_languages([repository])

    assert [language.name for language in languages] == ["Go"]
    assert languages[0].bytes == 2048


def test_aggregate_languages_ignores_unclassified_repositories(repo_factory):
    repositories = [
        Repository(name="blank", full_name="tester/blank"),
        repo_factory("typed", "Python", {"Python": 10}),
    ]

    languages = GitHubClient.aggregate_languages(repositories)

    assert [language.name for language in languages] == ["Python"]
