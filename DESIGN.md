---
name: GitHub Solar System V3
description: A pure-black, self-contained animated SVG portrait of a GitHub profile as a solar system with vector language logos, subtle orbits, and commit comets.
colors:
  void: "#000000"
  star: "#FFFFFF"
  orbit: "#FFFFFF"
  text: "#FFFFFF"
  muted: "#888888"
  sun-core: "#FFE9A8"
  sun-mid: "#FFD27A"
  sun-halo: "#FFE3B3"
  sun-rim: "#FF9A3D"
  sun-border: "#FFD166"
  comet-head: "#FFFFFF"
  comet-glow: "#FFFFFF"
typography:
  mono-header:
    fontFamily: "ui-monospace, 'SF Mono', Consolas, 'Liberation Mono', Menlo, monospace"
    fontSize: "10.5px"
    fontWeight: 400
    letterSpacing: "2.0px"
  mono-legend:
    fontFamily: "ui-monospace, 'SF Mono', Consolas, 'Liberation Mono', Menlo, monospace"
    fontSize: "9.5px"
    fontWeight: 400
    letterSpacing: "1.2px"
  planet-label:
    fontFamily: "'Avenir Next', 'Segoe UI', Ubuntu, 'Helvetica Neue', Arial, sans-serif"
    fontSize: "10.0px"
    fontWeight: 600
    letterSpacing: "0.4px"
  comet-label:
    fontFamily: "'Avenir Next', 'Segoe UI', Ubuntu, 'Helvetica Neue', Arial, sans-serif"
    fontSize: "9.8px"
    fontWeight: 600
    letterSpacing: "0.4px"
rounded:
  full: "999px"
  none: "0"
spacing:
  canvas: "1200x675"
  side-margin: "66px"
  vertical-margin: "34px"
components:
  planet:
    textColor: "{colors.text}"
    typography: "{typography.planet-label}"
    rounded: "{rounded.full}"
  moon:
    rounded: "{rounded.full}"
  comet:
    backgroundColor: "{colors.comet-head}"
    textColor: "{colors.text}"
    typography: "{typography.comet-label}"
    rounded: "{rounded.full}"
---

## Overview

A refined deep-space snapshot of a GitHub profile (V3). The avatar is the central sun
with a softened glow, dominant languages are planets bearing vector logos and name labels,
repositories are small luminous moons revolving around their language planet, and recent
verified commits are comets crossing diagonally from the left boundary.

## Colors

The field is pure black (`#000000`). Stars are white at subtle opacity variations.
Orbits use neutral white at low opacity (0.08) for minimal visual clutter.
Planet colors derive from GitHub's linguist palette with each planet housing its
crisp vector logo. The sun's glow is softened with a warm golden border (`#FFD166`)
and rim light (`#FF9A3D`). Comets and comet tails are pure white (`#FFFFFF`).

## Typography

- Minimal monospace header (`SOLAR SYSTEM · @USERNAME`) in upper-left and
  legend (`planets = languages · moons = repos · comets = recent pushes`) in lower-right.
- Planet labels use sans-serif bold, centered directly below each planet without percentages.
- Moon labels are omitted entirely for visual minimalism.
- Comet labels are attached directly to each moving comet.

## Layout & Orbit Geometry

- 1200×675 canvas with the sun at exact center.
- Orbits are wide, flattened horizontal ellipses (aspect ratio up to 2.15:1).
- Adaptive orbital geometry adjusts radii, scaling, and spacing so profiles with
  3 to 50+ languages render without clipping or overlap.
- Exactly one orbital ellipse per language planet (no empty or decorative orbits).

## Motion

- SMIL native SVG animations: continuous planet revolution, nested moon orbits,
  and left-to-right diagonal comet trajectories.
- Comets enter across the left boundary and move toward the lower-right; at most two
  comets are active at any single instant.
- Upright orientation: logos and planet labels maintain an upright posture throughout orbits.

## Components

- **Sun:** avatar data URI clipped to a circle over a gradient fallback, with a
  warm radial halo, two thin corona rings and a rim light.
- **Planet:** radial-shaded disc, subtle halo, specular highlight, terminator
  arc, language label above, and a nested moon group.
- **Moon:** small gradient disc with a halo, repository label placed by a
  deterministic candidate search, and a relative circular motion path.
- **Comet:** glowing head, two-line fading tail, repository label, and a link to
  the exact commit.

## Do's and Don'ts

- **Do** keep the field near-black and let the bodies carry the color.
- **Do** use native SVG motion (SMIL) only; no JavaScript.
- **Do** embed the avatar as a self-contained data URI and keep a gradient sun
  underneath it.
- **Do** keep all labels upright, outlined and attached to their moving body.
- **Do** prefer one comet per repository so duplicate labels do not crowd the
  scene.
- **Don't** add a heading, quote, count, percentage legend, repository index or
  statistics panel.
- **Don't** invent commits, fabricate activity or use decorative comets.
- **Don't** use synchronized periods or a single shared start phase.
- **Don't** use remote images, external fonts, scripts or tokens at view time.
