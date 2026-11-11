---
name: GitHub Solar System
description: A near-black, self-contained animated SVG portrait of a GitHub profile as a solar system.
colors:
  void: "#03040A"
  deep-navy: "#070B18"
  star: "#FFFFFF"
  orbit: "#8EA0C9"
  text: "#EEF2FF"
  muted: "#9AA4C4"
  sun-core: "#FFE9A8"
  sun-mid: "#FFB84D"
  sun-glow: "#FF7A18"
  accent: "#7DD3FC"
typography:
  planet-label:
    fontFamily: "Avenir Next, Segoe UI, Ubuntu, Helvetica Neue, Arial, sans-serif"
    fontSize: "12.2px"
    fontWeight: 600
    letterSpacing: "0.4px"
  moon-label:
    fontFamily: "Avenir Next, Segoe UI, Ubuntu, Helvetica Neue, Arial, sans-serif"
    fontSize: "8.2px"
    fontWeight: 600
    letterSpacing: "0.4px"
  comet-label:
    fontFamily: "Avenir Next, Segoe UI, Ubuntu, Helvetica Neue, Arial, sans-serif"
    fontSize: "9.4px"
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
    backgroundColor: "{colors.deep-navy}"
    textColor: "{colors.text}"
    typography: "{typography.planet-label}"
    rounded: "{rounded.full}"
  moon:
    backgroundColor: "{colors.orbit}"
    textColor: "{colors.muted}"
    typography: "{typography.moon-label}"
    rounded: "{rounded.full}"
  comet:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.text}"
    typography: "{typography.comet-label}"
    rounded: "{rounded.full}"
---

## Overview

A deep-space snapshot of a GitHub profile. The avatar is the sun, languages are
planets sized by real code bytes, repositories are moons, and recent verified
commits are comets. The scene is composed to feel like an astronomy poster, not
a statistics dashboard. The only visible words are language names and repository
names.

## Colors

The field is near-black (`#03040A`) with a navy bottom and low-opacity nebula
washes. Stars are white at low opacity. Orbits use a cool desaturated blue at
thin, low opacity. Planet colors come from GitHub's linguist palette where
known, so the language is recognizable before the label is read. The sun is warm:
`#FFE9A8` core through `#FFB84D` to a `#FF7A18` corona.

## Typography

One system sans stack, three small sizes. Planet labels are 12.2 px / 600 with
0.4 px tracking; moon labels are 8.2 px / 600 in the muted color; comet labels
are 9.4 px / 600. Every label uses a dark `paint-order: stroke` outline so it
stays readable over glows and other bodies. Never rotate label glyphs.

## Layout

A 1200×675 landscape field with the sun at the exact center. Orbits are
ellipses up to 1.55:1, spaced by the planet's disc plus its moon zone so discs
and moon rings never overlap. The outermost orbit leaves room for labels and
moons inside the canvas. Planets start on a spread phase; each has its own
period (34–75 s), direction and negative begin offset. Moons are children of
the planet group, orbit at 13–31 s with staggered phases, and keep upright
labels. Comets traverse bounded cubic paths and fade at both ends.

## Elevation & Depth

Depth comes from radial gradients, a soft sun corona, faint orbital glows and
layered planet shading — not from card shadows or borders. Stars and nebulae
sit behind everything. The static fallback duplicates the same composition at
the base transforms.

## Shapes

Everything is circular or elliptical: sun, planets, moons, comet heads,
orbit paths. The avatar is clipped to a circle with `preserveAspectRatio`
`xMidYMid slice`. No rectangles, panels, cards or dashboard chrome.

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
