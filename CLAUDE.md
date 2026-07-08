# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is the GitHub profile repository for @developtheweb. Its README renders on the profile page and is a live system, not a static page: an animated entropy-reversal SVG whose state is lowered by visitors ("Maxwell's demon"), plus nightly-refreshed telemetry. Do not reintroduce third-party rendering services (capsule-render, readme-typing-svg, komarev, vercel stats/quotes apps) — everything renders from this repo, GitHub, or stevenmilanese.com assets.

## Architecture

```
README.md                      profile page; contains marker-fenced generated sections
engine/generate_entropy_svg.py SMIL-animated assets/entropy.svg from state/demon.json (stdlib only)
engine/nightly.py              refreshes README marker sections + bumps entropy generation (stdlib only)
state/demon.json               bits_sorted / generation / demons / last_sorted_at
assets/entropy.svg             generated — never hand-edit; regenerate via the engine
.github/workflows/demon.yml    issues:opened, title "demon: sort 12 bits" → +12 bits, regen SVG, commit, comment, close
.github/workflows/nightly.yml  cron 17 6 * * * → engine/nightly.py, commit if changed
.github/workflows/snake.yml    cron every 12h → contribution snake SVGs on the `output` branch
```

## README marker sections (machine-written — edit the generators, not the sections)

- `<!-- FEED:START/END -->` — 4 newest Strange Quarks articles (RSS `/feed.xml` if populated, else parsed from https://stevenmilanese.com/blog HTML)
- `<!-- STATS:START/END -->` — telemetry row with live star/repo totals
- `<!-- FEATURED:START/END -->` — featured cards (anthropic-certs, slTrain, meowchi-releases, mpl) with live star counts

`engine/nightly.py` is fail-safe per section: on fetch/parse failure it leaves that section untouched and exits 0.

## Conventions

- Conventional commit messages (`feat:`, `fix:`, `chore:`, `ci:`). No attribution footers of any kind.
- Contact is `rev@moonfactory.dev` only — the old Telegram link and the old level-host email address are retired and must not reappear.
- Entropy formula: `S = max(12.7, 100 − 0.0002·bits_sorted)`; 12 bits per demon click = 34.4 zJ (12 × kT ln 2 at 300 K).
- SVG regeneration is deterministic for a given `generation` — diffs stay reviewable.
- Test locally with `python3 engine/generate_entropy_svg.py` and `GITHUB_TOKEN=$(gh auth token) python3 engine/nightly.py` (both stdlib-only; no pip installs).
