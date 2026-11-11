#!/usr/bin/env python3
"""Command-line entry point for the GitHub Solar System generator."""

from __future__ import annotations

import argparse
import json
import os
import sys
import xml.etree.ElementTree as ElementTree
from dataclasses import dataclass, field
from pathlib import Path

from src.avatar import AvatarError, read_avatar_file, to_data_uri
from src.data_models import Commit, Repository, User
from src.github_client import GitHubClient, GitHubError
from src.layout import (
    DEFAULT_COMET_LIMIT,
    DEFAULT_HEIGHT,
    DEFAULT_WIDTH,
    STAR_DENSITY,
    build_layout,
)
from src.renderer import render_svg
from src.styles import DEFAULT_THEME, THEMES

DEFAULT_MAX_LANGUAGE_FETCHES = 15
AUTHENTICATED_MAX_LANGUAGE_FETCHES = 50
FORBIDDEN_TAGS = {"script", "foreignObject"}


@dataclass
class FixtureData:
    user: User
    repositories: list[Repository] = field(default_factory=list)
    events: list[dict] = field(default_factory=list)
    commits: list[Commit] = field(default_factory=list)
    avatar_uri: str = ""


def _coerce_languages(payload: object) -> dict[str, int]:
    if not isinstance(payload, dict):
        return {}
    clean: dict[str, int] = {}
    for name, value in payload.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        if value > 0:
            clean[str(name)] = int(value)
    return clean


def _dedupe_commits(commits: list[Commit]) -> list[Commit]:
    unique: dict[tuple[str, str], Commit] = {}
    for commit in commits:
        if commit.sha:
            unique.setdefault(commit.identity, commit)
    return list(unique.values())


def _fixture_commits(payload: dict, events: list[dict]) -> list[Commit]:
    commits: list[Commit] = []
    entries = payload.get("commits")
    if isinstance(entries, list):
        for entry in entries:
            if isinstance(entry, dict):
                commit = Commit.from_fixture(entry)
                if commit.sha:
                    commits.append(commit)

    for event in events:
        if event.get("type") != "PushEvent":
            continue
        repo = event.get("repo")
        repo_name = ""
        if isinstance(repo, dict):
            repo_name = str(repo.get("name") or "")
        event_payload = event.get("payload")
        if not isinstance(event_payload, dict):
            continue
        for entry in event_payload.get("commits") or []:
            if not isinstance(entry, dict):
                continue
            commit = Commit.from_fixture(
                {
                    "repo": repo_name,
                    "sha": entry.get("sha"),
                    "message": entry.get("message"),
                    "html_url": entry.get("url"),
                    "committed_at": entry.get("date") or event.get("created_at"),
                    "author": (entry.get("author") or {}).get("name")
                    if isinstance(entry.get("author"), dict)
                    else None,
                }
            )
            if commit.sha:
                commits.append(commit)
    return _dedupe_commits(commits)


def load_fixture(path: str) -> FixtureData:
    with open(path, encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("fixture must be a JSON object")
    user_data = payload.get("user")
    if not isinstance(user_data, dict):
        raise ValueError("fixture must contain a 'user' object")

    user = User.from_api(user_data)
    repositories: list[Repository] = []
    for entry in payload.get("repos") or []:
        if not isinstance(entry, dict):
            continue
        repository = Repository.from_api(entry)
        mapping = entry.get("language_bytes")
        if mapping is None:
            mapping = entry.get("languages")
        repository.apply_languages(_coerce_languages(mapping))
        repositories.append(repository)
    events = [event for event in (payload.get("events") or []) if isinstance(event, dict)]

    avatar_uri = ""
    inline_avatar = payload.get("avatar_data_uri")
    if isinstance(inline_avatar, str) and inline_avatar.startswith("data:image/"):
        avatar_uri = inline_avatar
    else:
        avatar_file = payload.get("avatar_file")
        if isinstance(avatar_file, str) and avatar_file:
            candidate = Path(avatar_file)
            if not candidate.is_absolute():
                candidate = Path(path).resolve().parent / candidate
            try:
                avatar_uri = read_avatar_file(candidate)
            except AvatarError as exc:
                print(f"note: {exc}; using fallback sun", file=sys.stderr)

    return FixtureData(
        user=user,
        repositories=repositories,
        events=events,
        commits=_fixture_commits(payload, events),
        avatar_uri=avatar_uri,
    )


def _fetch_avatar(args: argparse.Namespace, user: User, client: GitHubClient) -> str:
    if args.no_avatar:
        return ""
    if args.avatar:
        return read_avatar_file(args.avatar)
    if not user.avatar_url:
        return ""
    try:
        return to_data_uri(client.get_avatar(user.avatar_url))
    except (GitHubError, AvatarError) as exc:
        print(f"note: avatar unavailable ({exc}); using fallback sun", file=sys.stderr)
        return ""


def _fetch(args: argparse.Namespace) -> tuple[User, list[Repository], list, list[Commit], str]:
    token = os.environ.get("GITHUB_TOKEN") or None
    client = GitHubClient(token=token)
    limit = args.max_language_fetches
    if limit is None:
        limit = (
            AUTHENTICATED_MAX_LANGUAGE_FETCHES
            if token
            else DEFAULT_MAX_LANGUAGE_FETCHES
        )
    user = client.get_user(args.username)
    repositories = client.get_repos(
        args.username,
        include_forks=args.include_forks,
        include_archived=args.include_archived,
        max_language_fetches=limit,
    )
    languages = client.aggregate_languages(repositories)
    commits: list[Commit] = []
    if not args.no_comets:
        try:
            commits = client.get_commits(
                repositories,
                lookback_days=args.commit_lookback_days,
                max_commits=max(20, args.max_comets * 6),
            )
        except GitHubError as exc:
            print(f"note: recent commits unavailable ({exc}); no comets", file=sys.stderr)
    avatar_uri = _fetch_avatar(args, user, client)
    return user, repositories, languages, commits, avatar_uri


def _validate_svg(svg: str) -> None:
    root = ElementTree.fromstring(svg)
    for node in root.iter():
        tag = node.tag.rsplit("}", 1)[-1]
        if tag in FORBIDDEN_TAGS:
            raise ValueError(f"generated SVG contains a forbidden <{tag}> element")
        if tag == "image":
            href = node.get("href") or node.get("{http://www.w3.org/1999/xlink}href") or ""
            if not href.startswith("data:image/"):
                raise ValueError("generated SVG contains an external or invalid image")
    lowered = svg.lower()
    for forbidden in ("@import", "url(http", "xlink:href", "javascript:"):
        if forbidden in lowered:
            raise ValueError(f"generated SVG contains forbidden content: {forbidden}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="generate.py",
        description="Render a GitHub profile as a self-contained SVG solar system.",
    )
    parser.add_argument("--username", help="GitHub username to visualise.")
    parser.add_argument("--output", required=True, help="Path of the SVG file to write.")
    parser.add_argument(
        "--fixture",
        help="Read user, repositories, commits and avatar hints from a JSON fixture instead of the API.",
    )
    parser.add_argument("--theme", choices=sorted(THEMES), default=DEFAULT_THEME)
    parser.add_argument("--include-forks", action="store_true", help="Include forked repositories.")
    parser.add_argument(
        "--include-archived", action="store_true", help="Include archived repositories."
    )
    parser.add_argument("--no-animation", action="store_true", help="Render a fully static SVG.")
    parser.add_argument("--no-comets", action="store_true", help="Skip recent-commit comets.")
    parser.add_argument(
        "--commit-lookback-days",
        type=int,
        default=7,
        help="How many days of recent commits feed the comet layer (default: 7).",
    )
    parser.add_argument(
        "--max-comets",
        type=int,
        default=DEFAULT_COMET_LIMIT,
        help=f"Maximum simultaneous commit comets (default: {DEFAULT_COMET_LIMIT}).",
    )
    parser.add_argument(
        "--avatar",
        help="Use a local image file for the sun instead of fetching the GitHub avatar.",
    )
    parser.add_argument("--no-avatar", action="store_true", help="Use the fallback gradient sun.")
    parser.add_argument("--width", type=int, default=DEFAULT_WIDTH, help="Canvas width in pixels.")
    parser.add_argument("--height", type=int, default=DEFAULT_HEIGHT, help="Canvas height in pixels.")
    parser.add_argument(
        "--star-density",
        choices=sorted(STAR_DENSITY),
        default="normal",
        help="Procedural starfield density.",
    )
    parser.add_argument(
        "--max-language-fetches",
        type=int,
        default=None,
        help="Maximum repositories to query for language bytes (default: 15, or 50 with a token).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.fixture and not args.username:
        parser.error("--username is required unless --fixture is used")
    if args.width < 320:
        parser.error("--width must be at least 320")
    if args.height < 240:
        parser.error("--height must be at least 240")
    if args.max_language_fetches is not None and args.max_language_fetches < 0:
        parser.error("--max-language-fetches must be zero or greater")
    if args.commit_lookback_days < 1:
        parser.error("--commit-lookback-days must be at least 1")
    if args.max_comets < 0:
        parser.error("--max-comets must be zero or greater")

    try:
        if args.fixture:
            fixture = load_fixture(args.fixture)
            user = fixture.user
            repositories = fixture.repositories
            languages = GitHubClient.aggregate_languages(repositories)
            commits = [] if args.no_comets else fixture.commits
            avatar_uri = "" if args.no_avatar else fixture.avatar_uri
        else:
            user, repositories, languages, commits, avatar_uri = _fetch(args)

        layout = build_layout(
            user,
            repositories,
            languages,
            commits=commits,
            avatar_uri=avatar_uri,
            width=args.width,
            height=args.height,
            star_density=args.star_density,
            comet_limit=args.max_comets,
        )
        svg = render_svg(
            layout,
            args.output,
            theme=args.theme,
            animate=not args.no_animation,
        )
        _validate_svg(svg)
    except (GitHubError, AvatarError, OSError, ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    moons = sum(len(planet.moons) for planet in layout.planets)
    print(
        f"Wrote {args.output} with {len(layout.planets)} languages, "
        f"{moons} moons and {len(layout.comets)} comets "
        f"from {layout.repos_count} repositories."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
