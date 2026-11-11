# GitHub Solar System

Turn a public GitHub profile into a self-contained, animated SVG solar system.

The profile picture is the sun. Programming languages become planets sized by the
code they represent. Every repository orbits its primary language as a moon, so
the moons travel with their planet while also circling it. Recent public commits
cross the field as comets, each labelled with its real repository. The only
visible words are language names and repository names — no dashboard, no legend,
no statistics panel.

<p align="center">
  <img
    src="output/solar-system.svg"
    alt="Shadow-Monarch-33 GitHub language solar system"
    width="100%"
  />
</p>

The SVG is the primary artifact. If your README host strips SVG motion or the
embedded avatar, point the same `<img>` at the animated GIF fallback instead:

```html
<img src="output/solar-system.gif" alt="Animated GitHub language solar system" width="100%" />
```

## Features

- **Avatar sun.** The configured account's real avatar is downloaded once,
  resized by GitHub's avatar CDN, embedded as a data URI, and clipped into a
  circular sun with a warm corona. No remote image request is needed to view the
  SVG. A gradient sun renders if the avatar cannot be fetched or displayed.
- **Living orbits.** Every language is a planet on its own elliptical orbit with
  a different period, direction and starting phase. Orbits glow faintly and no
  planet or moon zone overlaps the sun.
- **Nested moon motion.** Each repository is a moon inside its planet's moving
  group, so it follows the planet around the sun while revolving around the
  planet itself. Repository names stay upright and travel with their moon.
- **Real commit comets.** The generator fetches recent commits from the
  configured user's public repositories through the GitHub REST API. Each comet
  is a verified commit with its repository name beside the head, a pure-white
  glowing head and a fading white tail. Every comet travels diagonally from the
  upper-left to the lower-right. Commits are deduplicated by repository and SHA,
  sorted newest first, and rotated on one shared cycle so at most two comets are
  visible at any instant — including the loop boundary. No commits means no
  comets.
- **Deterministic snapshot.** Layout, stars, orbits and comet paths are seeded
  from the data and canvas, never from the current clock. The SVG contains no
  generation timestamp, so unchanged input produces identical bytes.
- **Pure black field.** The canvas is `#000000` with white stars and white orbit
  hairlines. Only the language planets and their moons carry colour.
- **Static fallback.** Motion is SMIL and the base transform places every planet
  and moon at its static position. A renderer that strips animation still gets a
  complete still composition. `prefers-reduced-motion: reduce` swaps in a static
  layer, and `--no-animation` removes motion entirely.
- **README-safe by construction.** One SVG with inline gradients, a system font
  stack, links, SMIL motion and a data-URI avatar. No scripts, no external fonts,
  no remote assets, no tokens.
- **Free forever.** Standard-library Python generator, MIT licensed.

## How it works

```text
GitHub REST API
      │
      ▼
src/github_client.py   user · repositories · language bytes · commits · avatar
      │                 pagination · retries · rate limits · fork filtering
      ▼
src/data_models.py     typed User / Repository / Language / Commit models
      │
      ▼
src/layout.py          deterministic geometry: orbits, nested moons, comets
      │
      ▼
src/renderer.py        self-contained SVG with atomic file writes
      │
      ▼
output/solar-system.svg
      │
      ▼
tools/render_gif.py    optional animated GIF fallback (Chrome + ffmpeg)
```

### Data sources

| Endpoint | Purpose |
| --- | --- |
| `GET /users/{login}` | Profile identity and avatar URL |
| `GET /users/{login}/repos` | Public repositories, paginated via `Link` |
| `GET /repos/{full_name}/languages` | Language byte breakdown per repository |
| `GET /repos/{full_name}/commits?since=…` | Recent real commits for comets |
| Avatar CDN | Profile image, requested at 256 px and embedded as a data URI |

Forks and archived repositories are excluded by default (both configurable).
Repositories without a detected language cannot become moons; they are not
rendered as placeholder planets and no count of them is shown in the image.

### Language weighting

A repository's primary language is the language with the most bytes in its
language breakdown, falling back to GitHub's `language` field and finally the
repository size when a breakdown is unavailable. A planet's size is a
square-root mapping of its language's share of the largest language:

```text
share  = language_bytes / largest_language_bytes
radius = clamp(8 + 26 · √share, 8, 34)   # pixels, before fit compression
```

The square root keeps a small language visible while leaving the dominant
language visibly dominant. Planet colors use GitHub's linguist palette where a
language is known, so Python, TypeScript, Ruby and friends remain recognizable.

### Layout and motion

- Planets sit on elliptical orbits (up to 1.55:1) around the avatar sun. Each
  planet has its own period, direction and phase, so the scene never marches in
  lockstep.
- Each planet group follows an elliptical relative path. Moons are children of
  that group and follow circular relative paths, which is what makes the nested
  motion work without JavaScript.
- Every label rides a radial ring around its planet or moon: the label rotates
  outward with its body while an opposite rotation keeps the text upright. Moons
  of one planet share a single period, so their staggered phases never collapse
  into a cluster and their labels stay fanned out. A black outline keeps every
  name legible over stars, orbits and the sun.
- Labels are only language names and repository names. There is no title,
  subtitle, quote, count, percentage legend, repository index or statistics
  panel.
- Stars, orbits, planet phases and comet trajectories are seeded from
  `sha256(canvas + login)` plus stable commit identities, never from
  `random.seed()` defaults or the clock.

### Comet window

The default lookback is **7 days** and is configurable with
`--commit-lookback-days`. The generator queries the commits endpoint for the
most recently pushed public repositories, deduplicates by repository and SHA,
sorts newest first, and keeps up to `--max-comets` entries (default 6). All
entries share one cycle: each comet flies for 8 seconds, entries start 5.5
seconds apart, so two neighbours may overlap briefly but a third never appears.
The cycle length is padded so the final comet finishes before the loop restarts.
Each comet links to its commit and shows the repository name; no SHA, timestamp
or commit message is displayed. When there are no qualifying commits, no comet
is drawn. The SVG is a snapshot; the scheduled workflow refreshes it.

## Quick start

```bash
git clone https://github.com/Shadow-Monarch-33/github-solar-system.git
cd github-solar-system
python generate.py --username Shadow-Monarch-33 --output output/solar-system.svg
```

Python 3.10+ is required. Generation uses only the standard library. Open the
SVG in any browser, or preview it as a PNG:

```bash
qlmanage -t -s 1200 -o /tmp output/solar-system.svg     # macOS
```

### Offline fixture mode

No network, no API quota:

```bash
python generate.py --fixture tests/fixtures/sample.json --output output/solar-system-fixture.svg
```

The bundled fixture is a real snapshot of `Shadow-Monarch-33` — profile, eight
public repositories, language bytes and recent commits — with a local avatar
image (`tests/fixtures/avatar.jpg`). It exercises the same layout, avatar and
comet paths as a live run.

### Options

| Option | Default | Description |
| --- | --- | --- |
| `--username` | — | GitHub login to visualise |
| `--output` | — (required) | Destination SVG path |
| `--fixture` | — | Read `{user, repos, commits}` JSON instead of calling the API |
| `--theme` | `nebula` | `nebula`, `midnight`, `light`, `mono` |
| `--width` / `--height` | `1200` / `675` | Canvas size (minimum 320×240) |
| `--star-density` | `normal` | `off`, `low`, `normal`, `high` |
| `--include-forks` | off | Include forks |
| `--include-archived` | off | Include archived repositories |
| `--no-animation` | off | Static-only SVG |
| `--no-comets` | off | Omit the commit comet layer |
| `--commit-lookback-days` | `7` | Recent commit window |
| `--max-comets` | `6` | Comets in the rotation (at most two visible at once) |
| `--avatar` | — | Use a local image file for the sun |
| `--no-avatar` | off | Use the fallback gradient sun |
| `--max-language-fetches` | 15 (50 with token) | Repositories to query for language bytes |

Set `GITHUB_TOKEN` to raise the API limit from 60 to 5,000 requests per hour.
The token is sent only in the `Authorization` header — it never reaches the SVG,
the logs, or the repository.

## Animated GIF fallback

The SVG is the primary output. Some hosts suppress SMIL animation or sanitize
embedded data-URI images, so the repository also ships an optional GIF:

```bash
python tools/render_gif.py \
  --svg output/solar-system.svg \
  --output output/solar-system.gif \
  --duration 8 --fps 8
```

The helper samples the SVG timeline in headless Chrome and assembles the frames
with `ffmpeg`. It is optional tooling; the generator itself stays
standard-library only. The GIF is 1000 px wide, loops with a short fade, and
does not need any JavaScript at view time.

## Automate with GitHub Actions

The bundled workflow (`.github/workflows/update.yml`) runs daily at
`04:17 UTC`, can be triggered manually from the Actions tab, regenerates the
SVG with the repository's `GITHUB_TOKEN`, validates it, optionally regenerates
the GIF fallback, and commits only when bytes changed.

```yaml
permissions:
  contents: write

on:
  schedule:
    - cron: "17 4 * * *"
  workflow_dispatch:
```

Because the workflow only reacts to `schedule` and `workflow_dispatch`, the
`[skip ci]` commit cannot retrigger it. If GitHub data cannot be fetched, the
command exits non-zero and the previously committed SVG stays untouched.

## Embed in your profile README

Replace the username and repository if you are using your own fork:

```html
<p align="center">
  <img
    src="https://raw.githubusercontent.com/Shadow-Monarch-33/github-solar-system/main/output/solar-system.svg"
    alt="Shadow-Monarch-33 GitHub language solar system"
    width="100%"
  />
</p>
```

If GitHub suppresses the SVG animation or the embedded avatar, use the GIF:

```html
<p align="center">
  <img
    src="https://raw.githubusercontent.com/Shadow-Monarch-33/github-solar-system/main/output/solar-system.gif"
    alt="Animated GitHub language solar system"
    width="100%"
  />
</p>
```

GitHub's image proxy caches assets, so a freshly regenerated image may take a
while to appear in a profile README. Nothing in the file itself is stale.

### What is verified, and what GitHub controls

- The SVG is validated as XML, contains no scripts or external assets, and every
  `<image>` reference is a `data:image/…` URI.
- The avatar is embedded as a JPEG/PNG data URI and rendered through a circular
  clip in headless Chrome; the fallback gradient sun is present underneath.
- Planetary, moon and comet motion is rendered at multiple points in the SMIL
  timeline in headless Chrome.
- GitHub's SVG sanitizer and image proxy are outside local control. If a future
  sanitizer strips SMIL or the data-URI avatar, the SVG degrades to a still
  composition with the fallback sun, and the GIF fallback remains available.

## Use it for your own profile

1. Fork this repository.
2. Edit the username in `.github/workflows/update.yml`.
3. Run the workflow once (`Actions → Update solar system → Run workflow`).
4. Point the `<img>` snippet at your fork.
5. Optionally change `--theme`, dimensions, `--star-density` or
   `--commit-lookback-days` in the workflow.

The generator itself is generic: it works for any public GitHub account.

## Customization

- **Themes** live in `src/styles.py` (`THEMES`). Add a palette to `THEMES` and
  pass `--theme your-name`.
- **Language colors** live in `src/colors.py` (`LANGUAGE_COLORS`).
- **Dimensions, star density, forks, archived repos, animation, comets,
  lookback and avatar source** are CLI flags and workflow arguments.
- **Planet scaling** is `_planet_radius` in `src/layout.py`.
- **Orbit spacing** is `_fit_orbits` in `src/layout.py`.
- **Moon density** is `MOONS_PER_RING` (12) in `src/layout.py`.
- **Orbit ellipticity** is `ASPECT_CAP` (1.55) in `src/layout.py`.
- **Comet count** is `DEFAULT_COMET_LIMIT` (6) in `src/layout.py`.

Every default is tuned so the first run already looks finished.

## Tests

```bash
pip install -r requirements.txt
python -m pytest -q
```

The suite covers API parsing and pagination, retries, rate-limit handling,
language aggregation and fallback, primary-language selection, planet/moon
assignment, nested relative motion paths, canvas bounds, extreme repository and
language counts, commit deduplication and comet mapping, avatar embedding and
fallback, XML escaping, SVG validity, absence of scripts and external assets,
comet direction and two-comet concurrency limits, white comet styling, pure
black background, permanent repository names, animation toggling, fixture mode
and CLI exit codes.

## Known limitations

- GitHub caches rendered images; updates are not instant in profile READMEs.
- Unauthenticated requests are limited to 60 per hour, so only the first 15
  repositories get precise language-byte data unless a token is provided. The
  rest fall back to GitHub's primary language and repository size.
- Comets use the most recently pushed public repositories up to a bounded
  request budget; a repository that has not been pushed within the lookback
  window contributes no comet.
- Labels ride a radial ring around their body and stay upright. Adjacent planets
  can still bring two labels close as their orbits cross, and a moon label on the
  inner side of a planet may pass over the sun's glow. Black outlines keep every
  name readable, and `--no-animation` renders a clean still frame.
- SMIL animation and data-URI `<image>` support vary across README hosts. The
  static fallback and GIF fallback cover hosts that suppress either.
- Repositories with no detected language cannot become moons; there is no
  language planet to attach them to.
- Only public data is accessible. Private repositories are never fetched.

## Project structure

```text
github-solar-system/
├── .github/workflows/update.yml
├── src/
│   ├── __init__.py
│   ├── avatar.py
│   ├── colors.py
│   ├── data_models.py
│   ├── github_client.py
│   ├── layout.py
│   ├── renderer.py
│   └── styles.py
├── tests/
│   ├── conftest.py
│   ├── fixtures/avatar.jpg
│   ├── fixtures/sample.json
│   ├── test_avatar.py
│   ├── test_cli.py
│   ├── test_github_client.py
│   ├── test_layout.py
│   └── test_renderer.py
├── tools/render_gif.py
├── output/solar-system.svg
├── output/solar-system.gif
├── generate.py
├── requirements.txt
├── LICENSE
└── README.md
```

## License

MIT © 2026 Shadow-Monarch-33. Use it, fork it, restyle it, ship it.
