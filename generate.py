#!/usr/bin/env python3
"""Command-line entry point for the GitHub Solar System generator."""

from __future__ import annotations

import argparse
import json
import os
import sys
import xml.etree.ElementTree as ElementTree

from src.data_models import Repository, User
from src.github_client import GitHubClient, GitHubError
from src.layout import DEFAULT_HEIGHT, DEFAULT_WIDTH, STAR_DENSITY, build_layout
from src.renderer import render_svg
from src.styles import DEFAULT_THEME, THEMES

DEFAULT_MAX_LANGUAGE_FETCHES = 15
AUTHENTICATED_MAX_LANGUAGE_FETCHES = 50
FORBIDDEN_TAGS = {"script", "image", "foreignObject"}


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


def load_fixture(path: str) -> tuple[User, list[Repository], list[dict]]:
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
    return user, repositories, events


def _comet_count(events: list[dict], enabled: bool) -> int:
    if not enabled:
        return 0
    pushed: set[str] = set()
    for event in events:
        if event.get("type") != "PushEvent":
            continue
        repo = event.get("repo")
        if isinstance(repo, dict):
            name = str(repo.get("name") or "")
            if name:
                pushed.add(name)
    return min(3, len(pushed))


def _fetch(args: argparse.Namespace) -> tuple[User, list[Repository], list, list[dict]]:
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
    try:
        events = client.get_events(args.username)
    except GitHubError:
        events = []
    return user, repositories, languages, events


def _validate_svg(svg: str) -> None:
    root = ElementTree.fromstring(svg)
    for node in root.iter():
        tag = node.tag.rsplit("}", 1)[-1]
        if tag in FORBIDDEN_TAGS:
            raise ValueError(f"generated SVG contains a forbidden <{tag}> element")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="generate.py",
        description="Render a GitHub profile as a self-contained SVG solar system.",
    )
    parser.add_argument("--username", help="GitHub username to visualise.")
    parser.add_argument("--output", required=True, help="Path of the SVG file to write.")
    parser.add_argument(
        "--fixture",
        help="Read user, repositories and events from a JSON fixture instead of the API.",
    )
    parser.add_argument("--theme", choices=sorted(THEMES), default=DEFAULT_THEME)
    parser.add_argument("--include-forks", action="store_true", help="Include forked repositories.")
    parser.add_argument(
        "--include-archived", action="store_true", help="Include archived repositories."
    )
    parser.add_argument("--no-animation", action="store_true", help="Render a fully static SVG.")
    parser.add_argument("--no-comets", action="store_true", help="Skip comet decoration.")
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

    try:
        if args.fixture:
            user, repositories, events = load_fixture(args.fixture)
            languages = GitHubClient.aggregate_languages(repositories)
        else:
            user, repositories, languages, events = _fetch(args)

        layout = build_layout(
            user,
            repositories,
            languages,
            width=args.width,
            height=args.height,
            star_density=args.star_density,
            comet_count=_comet_count(events, not args.no_comets),
        )
        svg = render_svg(
            layout,
            args.output,
            theme=args.theme,
            animate=not args.no_animation,
        )
        _validate_svg(svg)
    except (GitHubError, OSError, ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(
        f"Wrote {args.output} with {len(layout.planets)} languages "
        f"from {layout.repos_count} repositories."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
