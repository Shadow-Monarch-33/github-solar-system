# GitHub Solar System — PRODUCT.md

## Overview

An open-source Python tool that turns any public GitHub profile into a
self-contained animated SVG "solar system": the profile picture is the sun, the
user's dominant programming languages are planets sized by real usage, every
repository orbits its primary language as a moon, and recent verified commits
cross the field as comets labelled with their repository. The owner's profile
(Shadow-Monarch-33) is the showcase; anyone can point the tool at their own
username and get the same result. The SVG is embedded in a profile README and
kept current by a daily GitHub Actions refresh.

## Platform

- `web`

## Audience

1. Developers who want a live visual signature of their GitHub activity in
   their profile README.
2. Developers who fork or adapt the tool for their own profile — open-source
   reuse is a first-class path, not an afterthought.

## Data

- Source: the official GitHub REST API, public endpoints only, fetched by a
  daily scheduled job. An optional `GITHUB_TOKEN` (env var) raises rate limits
  when present; the tool works without it.
- Profile identity and avatar, the paginated repo list (name, primary language,
  language byte breakdown, fork flag, pushed_at, archived flag), and recent
  commits per public repository.
- Every failure mode is graceful: API errors, rate limits, missing avatars or
  partial data never destroy the last good SVG — a failed refresh leaves the
  previous output untouched. If the avatar cannot be fetched, a gradient sun is
  used; if no commits qualify, no comets are drawn.

## Core behavior

- The profile avatar is the sun, embedded as a self-contained data URI.
- Planets are the profile's dominant languages, sized by aggregated language
  bytes; each repo orbits as a moon around its primary language's planet.
- Moons follow their moving planet through nested SVG groups while revolving
  around it. No JavaScript is used.
- Comets are real public commits from a configurable window (7 days by default),
  deduplicated by repository and SHA and limited to the newest commits. One
  comet per repository keeps labels legible. Activity is never fabricated.
- The only visible text is programming language names and repository names.
  There is no heading, quote, count, percentage legend, repository index or
  statistics dashboard.
- New repos are picked up automatically on the next run; forks are excluded by
  default, with a config flag to include them.
- Language colors stay recognizable to developers who know GitHub's palette.
- Output is deterministic: identical input data yields a byte-identical SVG.

## Refresh model

- A daily GitHub Actions cron (plus manual `workflow_dispatch`) regenerates the
  SVG, validates it, optionally regenerates the animated GIF fallback, and
  commits only when content actually changed.
- No timestamps or nondeterministic metadata in the output, so unchanged input
  never produces spurious commits.

## Constraints

- 100% free to run and host; official GitHub REST API only; no paid services, no
  always-on server.
- The SVG is fully self-contained — no JavaScript, no remote assets at view
  time — needs no auth to view, and embeds in any README. The avatar is a data
  URI; every other visual is inline SVG.
- An animated GIF fallback is generated for hosts that suppress SVG animation.
- No tokens or secrets in any generated asset, log line, or commit.
- Python, preferring the standard library; a plain `python generate.py …`
  invocation is the interface. GIF rendering is optional tooling.

## Decisions confirmed by the user

- Visual direction: near-black (`#03040A`) deep-space field, subtle navy depth,
  small stars, glowing planets, thin low-opacity orbits, soft gradients, no
  dashboard chrome.
- The avatar is the sun; no username or caption appears beside it.
- Every visible label is a language name or a repository name.
- Comets are real commits from the last 7 days by default, labelled with their
  repository; no decorative comets and no invented activity.
- Planets and moons animate continuously with native SVG motion; moons must
  follow their moving planets.
- The SVG is the primary output; a generated animated GIF is the fallback when a
  README host suppresses SVG animation.

## Inferred assumptions

- Animation is progressive enhancement: the static composition is complete and
  attractive on its own.
- Dynamic label collisions are acceptable when unavoidable; initial placement
  and label outlines keep names readable.

## Success criteria

- `python generate.py --username <any-public-user> --output output/solar-system.svg`
  produces a valid SVG for any public username, including an offline
  fixture-data mode with no network.
- The embed snippet renders reliably in a profile README, with the GIF fallback
  documented for hosts that strip SVG motion or data-URI images.
- Tests cover API parsing and pagination, language aggregation and
  primary-language selection, nested planet/moon motion, commit deduplication
  and comet mapping, avatar embedding and fallback, deterministic layout,
  empty/edge-case repos, extreme repo counts, XML escaping, SVG validity,
  absence of removed dashboard text, and API-failure fallback — and they pass.
