#!/usr/bin/env python3
"""Generate assets/entropy.svg — a SMIL-animated entropy-reversal field.

120 particles loop from a seeded chaos cloud into a (2,5) torus-knot
lattice, hold, and scatter back. State (bits sorted by visitors, chaos
generation) comes from state/demon.json. Stdlib only; deterministic for
a given generation so regenerated output is diffable.
"""

import hashlib
import json
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_PATH = os.path.join(ROOT, "state", "demon.json")
OUT_PATH = os.path.join(ROOT, "assets", "entropy.svg")

WIDTH, HEIGHT = 880, 260
MARGIN = 20
N_PARTICLES = 120
KNOT_R, KNOT_r = 150, 58
DUR = "11s"
KEY_TIMES = "0;0.64;0.82;1"
KEY_SPLINES = "0.25 0.1 0.25 1;0 0 1 1;0.55 0 0.45 1"

BG = "#010409"
BORDER = "#21262d"
CYAN = "#4dd4e8"
DEEP = "#1d6f7d"
GREEN = "#7ee2a8"
MUTED = "#8b949e"


def seeded_unit(index, generation, channel):
    """Deterministic float in [0, 1) from particle index + generation."""
    digest = hashlib.sha256(f"{index}:{generation}:{channel}".encode()).digest()
    return int.from_bytes(digest[:8], "big") / 2**64


def knot_points(n):
    """(2,5) torus knot sampled at n points, scaled/centered to the canvas."""
    raw = []
    for i in range(n):
        t = 2 * math.pi * i / n
        rad = KNOT_R + KNOT_r * math.cos(5 * t)
        raw.append((rad * math.cos(2 * t), 0.62 * rad * math.sin(2 * t)))
    xs, ys = [p[0] for p in raw], [p[1] for p in raw]
    span_x, span_y = max(xs) - min(xs), max(ys) - min(ys)
    scale = min((WIDTH - 2 * MARGIN) / span_x, (HEIGHT - 2 * MARGIN) / span_y)
    cx, cy = (max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2
    return [
        (WIDTH / 2 + (x - cx) * scale, HEIGHT / 2 + (y - cy) * scale)
        for x, y in raw
    ]


def main():
    with open(STATE_PATH) as fh:
        state = json.load(fh)
    bits = int(state.get("bits_sorted", 0))
    generation = int(state.get("generation", 0))
    entropy = max(12.7, 100 - 0.0002 * bits)
    s_label = f"{entropy:.1f}"

    lattice = knot_points(N_PARTICLES)
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" '
        f'viewBox="0 0 {WIDTH} {HEIGHT}" role="img" '
        f'aria-label="Entropy-reversal field: S = {s_label} k-bits">',
        f'<rect x="0.5" y="0.5" width="{WIDTH - 1}" height="{HEIGHT - 1}" '
        f'rx="8" fill="{BG}" stroke="{BORDER}"/>',
    ]

    for i, (lx, ly) in enumerate(lattice):
        chaos_x = MARGIN + seeded_unit(i, generation, "x") * (WIDTH - 2 * MARGIN)
        chaos_y = MARGIN + seeded_unit(i, generation, "y") * (HEIGHT - 2 * MARGIN)
        fill = DEEP if seeded_unit(i, generation, "depth") < 0.3 else CYAN
        cxv = f"{chaos_x:.1f};{lx:.1f};{lx:.1f};{chaos_x:.1f}"
        cyv = f"{chaos_y:.1f};{ly:.1f};{ly:.1f};{chaos_y:.1f}"
        parts.append(
            f'<circle r="3" fill="{fill}" cx="{chaos_x:.1f}" cy="{chaos_y:.1f}">'
            f'<animate attributeName="cx" dur="{DUR}" repeatCount="indefinite" '
            f'calcMode="spline" keyTimes="{KEY_TIMES}" keySplines="{KEY_SPLINES}" '
            f'values="{cxv}"/>'
            f'<animate attributeName="cy" dur="{DUR}" repeatCount="indefinite" '
            f'calcMode="spline" keyTimes="{KEY_TIMES}" keySplines="{KEY_SPLINES}" '
            f'values="{cyv}"/>'
            f'</circle>'
        )

    font = 'font-family="ui-monospace,SFMono-Regular,Menlo,monospace"'
    parts.append(
        f'<text x="16" y="26" {font} font-size="14" fill="{CYAN}">'
        f'S = {s_label} k·bits</text>'
    )
    parts.append(
        f'<text x="{WIDTH - 16}" y="26" text-anchor="end" {font} '
        f'font-size="14" fill="{GREEN}">dS/dt &lt; 0</text>'
    )
    parts.append(
        f'<text x="{WIDTH - 16}" y="{HEIGHT - 14}" text-anchor="end" {font} '
        f'font-size="11" fill="{MUTED}">bits sorted by visitors: {bits}</text>'
    )
    parts.append("</svg>")

    svg = "\n".join(parts) + "\n"
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w") as fh:
        fh.write(svg)
    size = os.path.getsize(OUT_PATH)
    print(f"wrote {OUT_PATH} ({size} bytes, S={s_label}, bits={bits}, gen={generation})")
    if size > 200 * 1024:
        print("error: SVG exceeds 200 KB budget", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
