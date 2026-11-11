# 🪐 GitHub Solar System

**Your GitHub activity, reimagined as a living solar system.**

Turn any public GitHub profile into an animated universe where programming languages are planets, repositories are moons, and recent commits become shooting comets.

Built with Python and SVG. No paid APIs, no JavaScript runtime, and no external rendering services.

<p align="center">
  <img src="output/solar-system.svg" alt="Animated GitHub Solar System for Shadow-Monarch-33" width="100%" />
</p>

<p align="center">
  <a href="#getting-started">Get Started</a> ·
  <a href="#how-it-works">How It Works</a> ·
  <a href="#customization">Customize</a> ·
  <a href="#automation">Automation</a>
</p>

## A little universe made from code

GitHub profiles already tell us a lot about what people build. I wanted to see that information in a different way — something more visual, a little playful, and actually fun to look at.

That's where GitHub Solar System comes in.

Your GitHub avatar becomes the sun. The languages you've written become orbiting planets, complete with their recognizable logos. Your repositories become moons revolving around those planets, while recent development activity occasionally streaks across the screen as comets.

And because the data comes directly from GitHub, the solar system changes as your projects grow.

## Features

- **Your avatar is the sun.** Your actual GitHub profile picture sits at the center, surrounded by a subtle golden glow.
- **Languages become planets.** Each detected language receives its own planet, sized according to its share of your codebase.
- **Recognizable language logos.** Built-in support for 55+ languages and technologies, with automatic fallbacks for unfamiliar ones.
- **Repositories become moons.** Each repository orbits the planet representing its primary language.
- **Real activity becomes comets.** Recent verified commits produce white shooting comets, labelled with the repository they came from.
- **Continuous orbital animation.** Planets revolve around the sun while moons independently revolve around their moving planets.
- **A clean space aesthetic.** Pure black background, white stars, subtle orbital paths, and no unnecessary statistics panels.
- **Automatic daily updates.** GitHub Actions refreshes the visualization using live public GitHub data.
- **Deterministic output.** The same input produces the same SVG, avoiding unnecessary commits.
- **Self-contained SVG.** No JavaScript, external fonts, remotely loaded artwork, or paid services.

The whole thing is designed to work as a GitHub profile README graphic, but you can also open the SVG directly in a browser.

## How it works

The generator reads your public GitHub profile using the GitHub REST API and turns that information into a visual scene.

| GitHub data | Solar system |
|---|---|
| Profile picture | Sun |
| Programming languages | Planets |
| Language code-byte totals | Planet sizes |
| Public repositories | Moons |
| Primary repository language | Moon's parent planet |
| Recent eligible commits | Comets |

Each repository contributes to its detected language totals, but appears as a moon around only its primary language planet.

Languages aren't limited to Python, JavaScript, TypeScript, or any particular set. Whenever GitHub detects a new supported language, the generator can create a planet for it automatically.

### The animation

Planets follow wide, elliptical orbits around the sun, each with its own speed and starting position.

Moons are attached to their parent planets, so they move around the sun alongside them while maintaining their own local revolution.

Comets enter from the left, travelling toward the lower-right with long white trails. Their repository names appear beside them and disappear when they leave the scene.

Comets follow a round-robin rotation of repositories with eligible recent activity. A repository won't appear twice before the other eligible repositories have had their turn, and no more than two comets are visible at once.

No eligible recent commits means no comets. Nothing is fabricated to make the scene look busier.

## Getting started

### Requirements

- Python 3.10 or newer
- Internet access to fetch public GitHub data
- An optional GitHub token for higher API limits

The SVG generator uses Python's standard library.

### 1. Clone the repository

```bash
git clone https://github.com/Shadow-Monarch-33/github-solar-system.git
cd github-solar-system
```

### 2. Generate your solar system

Replace `YOUR_USERNAME` with your GitHub username.

```bash
python3 generate.py \
  --username YOUR_USERNAME \
  --output output/solar-system.svg
```

That's it. Open `output/solar-system.svg` in a browser to see your solar system.

### 3. Try it without the GitHub API

The repository includes a sample dataset for offline testing.

```bash
python3 generate.py \
  --fixture tests/fixtures/sample.json \
  --output output/solar-system.svg
```

Fixture mode is useful when experimenting with the layout or when you've hit GitHub's API rate limit.

**Note:** Fixture data is a saved snapshot. For your latest repositories and languages, generate using `--username` instead.

## Add it to your GitHub profile

Once your generated SVG is committed to a public repository, you can embed it directly into your profile README.

```html
<p align="center">
  <img
    src="https://raw.githubusercontent.com/YOUR_USERNAME/github-solar-system/main/output/solar-system.svg"
    alt="My GitHub Solar System"
    width="100%"
  />
</p>
```

Replace `YOUR_USERNAME` with your account name.

The repository hosting the SVG needs to be public for other visitors to access the image reliably.

GitHub may cache the image, so updates aren't always visible immediately.

### Optional animated GIF

Some environments don't fully support SVG animation or embedded avatar images. An animated GIF can be used as a fallback.

```bash
python3 tools/render_gif.py \
  --svg output/solar-system.svg \
  --output output/solar-system.gif
```

The GIF renderer uses headless Chrome and FFmpeg. These aren't required for normal SVG generation.

The SVG is the primary output; the GIF is optional.

## Automation

You don't need to regenerate your solar system manually every time you create a repository or learn a new language.

The included GitHub Actions workflow can do that for you.

It:

1. Fetches your latest public GitHub data.
2. Regenerates the solar system.
3. Validates the generated SVG.
4. Commits and pushes updated output only when something has changed.

The workflow runs daily at **04:17 UTC** and also supports manual execution.

### Setting it up

Fork the repository or publish your own copy, then:

1. Open `.github/workflows/update.yml`.
2. Replace the configured GitHub username with yours.
3. Ensure GitHub Actions has permission to write repository contents.
4. Open **Actions → Update solar system → Run workflow**.
5. Check the job logs to confirm generation and publishing succeeded.

The workflow uses the built-in `GITHUB_TOKEN` for authenticated requests.

If GitHub's API is temporarily unavailable, the generator exits without overwriting the last successfully generated SVG.

### API limits

Unauthenticated GitHub API requests typically have a limit of 60 requests per hour. Authenticated requests using a standard GitHub token generally have a much higher limit.

For profiles with many repositories, using a token is recommended so the generator can fetch detailed language statistics more reliably.

Only public repository information is displayed.

## Customization

You can change the appearance and behavior without rewriting the generator.

| Option | What it changes |
|---|---|
| `--username` | GitHub account to visualize |
| `--theme` | Available visual theme |
| `--width`, `--height` | SVG dimensions |
| `--star-density` | Number of background stars |
| `--include-forks` | Include forked repositories |
| `--include-archived` | Include archived repositories |
| `--commit-lookback-days` | How far back to search for recent commits |
| `--max-comets` | Number of comet entries |
| `--no-comets` | Disable comet visualization |
| `--no-animation` | Generate a static solar system |
| `--avatar` | Use a local image for the sun |
| `--no-avatar` | Use the fallback sun |

Run `python3 generate.py --help` for the complete list.

### Changing the design

The main files you'll want to explore are:

- `src/layout.py` — Orbit geometry, planet sizes, moon placement, and comet motion.
- `src/renderer.py` — SVG generation, labels, stars, gradients, and visual effects.
- `src/logos.py` — Language logos and fallbacks.
- `src/colors.py` — Language colors.
- `src/styles.py` — Theme definitions.

The default design uses a pure-black background, white stars, a subtle golden sun, and colored language planets.

## Project structure

```text
github-solar-system/
├── .github/
│   └── workflows/
│       └── update.yml
├── src/
│   ├── avatar.py
│   ├── colors.py
│   ├── data_models.py
│   ├── github_client.py
│   ├── layout.py
│   ├── logos.py
│   ├── renderer.py
│   └── styles.py
├── tests/
│   └── fixtures/
├── tools/
│   └── render_gif.py
├── output/
│   └── solar-system.svg
├── generate.py
├── requirements.txt
├── LICENSE
└── README.md
```

### Under the hood

The project is split into a few straightforward stages.

**GitHub client:** Fetches profile information, repositories, language statistics, and recent commits. Handles pagination, retries, filtering, and rate limits.

**Data models:** Organizes the retrieved information into typed objects that the layout engine can use.

**Layout engine:** Calculates planet orbits, relative moon positions, labels, and comet trajectories. Uses deterministic values so repeated generations remain consistent.

**SVG renderer:** Produces the finished, self-contained visualization with embedded assets and animation.

**Optional GIF renderer:** Captures animation frames in a headless browser and assembles them into a looping GIF.

## Tests

Install the development dependencies:

```bash
python3 -m pip install -r requirements.txt
```

Then run:

```bash
python3 -m pytest -q
```

The tests cover GitHub API behavior, language aggregation, repository assignment, orbital geometry, nested animation, comet scheduling, avatar handling, SVG validity, CLI behavior, and offline fixture generation.

They also check important edge cases, including empty profiles, unknown languages, dense layouts, and API failures.

## Things to know

A few limitations are worth keeping in mind.

**GitHub language detection:** The generator relies on GitHub's language statistics. Technologies used through dependencies, database connections, or configuration don't necessarily appear as separate languages. For example, using PostgreSQL doesn't automatically create a PostgreSQL planet.

**Repository assignment:** Each repository contributes language statistics, but its moon belongs to only one primary language planet.

**SVG compatibility:** Native SVG animations work in supported browsers, but GitHub and other README hosts may handle animation or embedded images differently. The static composition and optional GIF provide alternatives.

**Crowded profiles:** The layout adapts to profiles with many languages and repositories, though very dense systems may have occasional visual crowding.

**Recent activity:** Comets represent eligible commits within the configured lookback and API request limits. They aren't a complete history of every contribution.

**Public data only:** Private repositories and their commit histories are not exposed.

## Contributing

Contributions are welcome.

Whether it's adding language logos, improving orbital layouts, fixing edge cases, optimizing rendering, or making the project easier to customize, feel free to open an issue or submit a pull request.

If you're changing the generator, please run the tests before submitting your changes.

## License

Released under the [MIT License](LICENSE).

Free to use, modify, fork, and build upon.

---

<p align="center">
  <strong>Made for developers who like watching their projects grow.</strong>
</p>
