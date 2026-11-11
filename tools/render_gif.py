#!/usr/bin/env python3
"""Render an animated GIF fallback from the generated SVG.

The SVG remains the primary artifact. This helper samples the SMIL timeline in
headless Chrome and assembles the frames with ffmpeg for hosts that strip SVG
animation. It is optional tooling: the generator itself stays standard-library
only.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ElementTree
from pathlib import Path

CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "google-chrome",
    "google-chrome-stable",
    "chromium",
    "chromium-browser",
]


def find_chrome(explicit: str | None) -> str:
    if explicit:
        return explicit
    for candidate in CHROME_CANDIDATES:
        if os.path.isabs(candidate) and Path(candidate).exists():
            return candidate
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
    raise SystemExit("error: Chrome/Chromium was not found; pass --chrome PATH")


def find_ffmpeg() -> str:
    resolved = shutil.which("ffmpeg")
    if not resolved:
        raise SystemExit("error: ffmpeg was not found on PATH")
    return resolved


def svg_size(path: Path) -> tuple[int, int]:
    root = ElementTree.parse(path).getroot()
    width = int(float(str(root.get("width") or "1200").replace("px", "")))
    height = int(float(str(root.get("height") or "675").replace("px", "")))
    return max(1, width), max(1, height)


def render_frames(
    chrome: str,
    svg: Path,
    directory: Path,
    *,
    duration: float,
    fps: int,
    width: int,
    height: int,
) -> list[Path]:
    profile = directory / "chrome-profile"
    total = max(2, int(round(duration * fps)))
    frames: list[Path] = []
    url = svg.resolve().as_uri()
    for index in range(total):
        virtual_ms = 1000 + int(round(index * 1000.0 / fps))
        target = directory / f"frame_{index:04d}.png"
        command = [
            chrome,
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--no-first-run",
            "--hide-scrollbars",
            "--run-all-compositor-stages-before-draw",
            f"--user-data-dir={profile}",
            f"--window-size={width},{height}",
            f"--virtual-time-budget={virtual_ms}",
            f"--screenshot={target}",
            url,
        ]
        result = subprocess.run(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=45,
            check=False,
        )
        if result.returncode != 0 or not target.exists():
            raise SystemExit(f"error: Chrome failed to render frame {index}")
        frames.append(target)
        print(f"frame {index + 1}/{total}", file=sys.stderr)
    return frames


def encode_gif(ffmpeg: str, directory: Path, frames: list[Path], output: Path, duration: float, fps: int) -> None:
    fade = min(0.7, max(0.3, duration * 0.08))
    filter_graph = (
        f"fade=t=in:st=0:d={fade:.2f},"
        f"fade=t=out:st={max(0.0, duration - fade):.2f}:d={fade:.2f},"
        "scale=1000:-1:flags=lanczos,"
        "split[s0][s1];[s0]palettegen=max_colors=128[p];"
        "[s1][p]paletteuse=dither=bayer:bayer_scale=3"
    )
    command = [
        ffmpeg,
        "-y",
        "-loglevel",
        "error",
        "-framerate",
        str(fps),
        "-i",
        str(directory / "frame_%04d.png"),
        "-vf",
        filter_graph,
        "-loop",
        "0",
        str(output),
    ]
    subprocess.run(command, check=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Render an animated GIF fallback from the solar-system SVG.")
    parser.add_argument("--svg", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--duration", type=float, default=8.0)
    parser.add_argument("--fps", type=int, default=8)
    parser.add_argument("--chrome", default=None)
    parser.add_argument("--keep-frames", action="store_true")
    args = parser.parse_args(argv)

    svg = Path(args.svg)
    if not svg.exists():
        parser.error(f"SVG not found: {svg}")
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    chrome = find_chrome(args.chrome)
    ffmpeg = find_ffmpeg()
    width, height = svg_size(svg)

    directory = Path(tempfile.mkdtemp(prefix="solar-gif-"))
    try:
        frames = render_frames(
            chrome,
            svg,
            directory,
            duration=args.duration,
            fps=args.fps,
            width=width,
            height=height,
        )
        encode_gif(ffmpeg, directory, frames, output, args.duration, args.fps)
        print(f"Wrote {output} ({len(frames)} frames)")
    finally:
        if not args.keep_frames:
            shutil.rmtree(directory, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
