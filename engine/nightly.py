#!/usr/bin/env python3
"""Nightly telemetry refresh for the profile README.

Updates the marker-fenced sections of README.md:
  FEED     — 4 newest Strange Quarks articles (RSS if populated, else the
             server-rendered blog HTML)
  STATS    — telemetry row with live star/repo totals
  FEATURED — star counts on the featured project cards
and bumps the entropy field's chaos generation so the field differs daily.

Every section is fail-safe: if a fetch or parse fails, that section is left
untouched and the script still exits 0. Stdlib only.
"""

import datetime
import html as htmllib
import json
import os
import re
import subprocess
import sys
import urllib.request
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
README = os.path.join(ROOT, "README.md")
STATE_PATH = os.path.join(ROOT, "state", "demon.json")

SITE = "https://stevenmilanese.com"
FEED_URL = f"{SITE}/feed.xml"
BLOG_URL = f"{SITE}/blog"

FEATURED_REPOS = [
    ("anthropic-certs", "Verified Anthropic certifications — Claude, API, Claude Code CLI, MCP."),
    ("slTrain", "A steam locomotive for your terminal, smoke trail included."),
    ("meowchi-releases", "A desktop pet that evolves when you actually get work done."),
    ("mpl", "Mathematics Programming Language — write the equation, run the equation."),
]


def fetch(url, accept=None):
    req = urllib.request.Request(url, headers={"User-Agent": "developtheweb-nightly/1.0"})
    if accept:
        req.add_header("Accept", accept)
    token = os.environ.get("GITHUB_TOKEN")
    if token and url.startswith("https://api.github.com"):
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def gh_api(path):
    return json.loads(fetch(f"https://api.github.com{path}", accept="application/vnd.github+json"))


def replace_section(text, marker, body):
    start, end = f"<!-- {marker}:START -->", f"<!-- {marker}:END -->"
    if start not in text or end not in text:
        raise ValueError(f"missing {marker} markers")
    pre = text.split(start)[0]
    post = text.split(end)[1]
    return f"{pre}{start}\n{body}\n{end}{post}"


def articles_from_rss():
    root = ET.fromstring(fetch(FEED_URL))
    items = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub = (item.findtext("pubDate") or "").strip()
        date = None
        try:
            date = datetime.datetime.strptime(pub[:16].strip(), "%a, %d %b %Y")
        except ValueError:
            pass
        if title and link:
            items.append({"title": title, "url": link, "date": date, "meta": ""})
    return items


def articles_from_html():
    page = fetch(BLOG_URL)
    skip = ("/blog/tag/", "/blog/author/")
    anchors = [
        m for m in re.finditer(r'<a[^>]+href="(/blog/[a-z0-9][a-z0-9-]*)"', page)
        if not m.group(1).startswith(skip)
    ]
    seen, articles = set(), []
    for idx, m in enumerate(anchors):
        slug = m.group(1)
        if slug in seen:
            continue
        seen.add(slug)
        stop = len(page)
        for nxt in anchors[idx + 1:]:
            if nxt.group(1) != slug:
                stop = nxt.start()
                break
        window = page[m.start():stop]
        title_m = re.search(r'alt="([^"]+)"', window)
        stripped = re.sub(r"<[^>]+>", " ", window)
        stripped = htmllib.unescape(re.sub(r"<!--.*?-->", "", stripped))
        date_m = re.search(r"([A-Z][a-z]+ \d{1,2}, \d{4})", stripped)
        mins_m = re.search(r"(\d+)\s*min", stripped)
        views_m = re.search(r"([\d,]+)\s*views", stripped)
        if not (title_m and date_m):
            continue
        date = datetime.datetime.strptime(date_m.group(1), "%B %d, %Y")
        meta = f"{mins_m.group(1)} min read" if mins_m else (
            f"{views_m.group(1)} views" if views_m else ""
        )
        articles.append({
            "title": htmllib.unescape(title_m.group(1)),
            "url": f"{SITE}{slug}",
            "date": date,
            "meta": meta,
        })
    return articles


def update_feed(text):
    articles = []
    try:
        articles = articles_from_rss()
    except Exception as exc:
        print(f"feed: rss unusable ({exc}); falling back to html")
    if not articles:
        articles = articles_from_html()
    dated = [a for a in articles if a["date"]]
    dated.sort(key=lambda a: a["date"], reverse=True)
    newest = dated[:4]
    if len(newest) < 4:
        raise ValueError(f"only {len(newest)} parseable articles")
    rows = ["| Article | |", "|:---|---:|"]
    for a in newest:
        title = a["title"].replace("|", "\\|")
        when = a["date"].strftime("%b %d, %Y").replace(" 0", " ")
        meta = f"{when} · {a['meta']}" if a["meta"] else when
        rows.append(f"| [{title}]({a['url']}) | {meta} |")
    return replace_section(text, "FEED", "\n".join(rows))


def update_stats(text):
    repos = gh_api("/users/developtheweb/repos?per_page=100&type=owner")
    public = [r for r in repos if not r["private"]]
    stars = sum(r["stargazers_count"] for r in public)
    line = (
        "<div align=\"center\">\n\n"
        "`10¹⁰⁶ yr until heat death — the deadline` · "
        "`2.9 zJ of order per bit sorted (kT ln 2, 300 K)` · "
        f"`★ {stars} stars across {len(public)} public repos`\n\n"
        "</div>"
    )
    return replace_section(text, "STATS", line)


def update_featured(text):
    cards = []
    for name, blurb in FEATURED_REPOS:
        repo = gh_api(f"/repos/developtheweb/{name}")
        cards.append(
            f'<td width="50%" valign="top">\n'
            f'<h3 align="center"><a href="{repo["html_url"]}">{name}</a></h3>\n'
            f'<p align="center"><code>★ {repo["stargazers_count"]}</code></p>\n'
            f'<p align="center">{blurb}</p>\n'
            f'</td>'
        )
    table = (
        '<div align="center">\n<table>\n'
        f'<tr>\n{cards[0]}\n{cards[1]}\n</tr>\n'
        f'<tr>\n{cards[2]}\n{cards[3]}\n</tr>\n'
        '</table>\n</div>'
    )
    return replace_section(text, "FEATURED", table)


def bump_entropy():
    with open(STATE_PATH) as fh:
        state = json.load(fh)
    state["generation"] += 1
    with open(STATE_PATH, "w") as fh:
        json.dump(state, fh, indent=2)
        fh.write("\n")
    subprocess.run(
        [sys.executable, os.path.join(ROOT, "engine", "generate_entropy_svg.py")],
        check=True,
    )


def main():
    with open(README) as fh:
        text = fh.read()
    for label, fn in (("FEED", update_feed), ("STATS", update_stats), ("FEATURED", update_featured)):
        try:
            text = fn(text)
            print(f"{label}: updated")
        except Exception as exc:
            print(f"{label}: left untouched ({exc})")
    with open(README, "w") as fh:
        fh.write(text)
    try:
        bump_entropy()
        print("ENTROPY: regenerated")
    except Exception as exc:
        print(f"ENTROPY: left untouched ({exc})")


if __name__ == "__main__":
    main()
