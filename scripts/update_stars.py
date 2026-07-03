#!/usr/bin/env python3
"""Refresh star counts in README.md and assets/hero-*.svg.

Runs daily via .github/workflows/update-stars.yml. Formats numbers the way
GitHub's own star counter does (33683 -> 33.7k) so the profile never shows
a rounded-up "34k" or a flaky badge's "invalid".
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import urllib.request
from datetime import date

REPOS = [
    "VectifyAI/PageIndex",
    "VectifyAI/OpenKB",
    "microsoft/graphrag",
    "sgl-project/sglang",
]
# repo -> label used in the hero SVG's right column
HERO_LABELS = {"VectifyAI/PageIndex": "PageIndex", "VectifyAI/OpenKB": "OpenKB"}

ROOT = pathlib.Path(__file__).resolve().parent.parent


def fetch_stars(repo: str) -> int:
    req = urllib.request.Request(f"https://api.github.com/repos/{repo}")
    req.add_header("Accept", "application/vnd.github+json")
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return int(json.load(resp)["stargazers_count"])


def fmt(n: int) -> str:
    """GitHub-style: 987 -> '987', 2836 -> '2.8k', 33683 -> '33.7k'."""
    if n < 1000:
        return str(n)
    v = round(n / 100) / 10
    text = f"{v:.1f}".rstrip("0").rstrip(".")
    return f"{text}k"


def main() -> None:
    stars = {repo: fmt(fetch_stars(repo)) for repo in REPOS}
    print("fetched:", stars)

    changed_files: list[str] = []

    readme = ROOT / "README.md"
    text = readme.read_text(encoding="utf-8")
    original = text
    for repo, value in stars.items():
        pattern = re.compile(
            rf"(<!--star:{re.escape(repo)}-->)\*\*★ [^*]+\*\*(<!--/star-->)"
        )
        text = pattern.sub(lambda m: f"{m.group(1)}**★ {value}**{m.group(2)}", text)
    svg_changed = False
    for svg_path in sorted((ROOT / "assets").glob("hero-*.svg")):
        svg = svg_path.read_text(encoding="utf-8")
        svg_orig = svg
        for repo, label in HERO_LABELS.items():
            svg = re.sub(
                rf"(>{label} <tspan[^>]*>★)[0-9.k]+",
                lambda m: f"{m.group(1)}{stars[repo]}",
                svg,
            )
        if svg != svg_orig:
            svg_path.write_text(svg, encoding="utf-8")
            changed_files.append(svg_path.name)
            svg_changed = True
    if svg_changed:
        # bust GitHub's camo image cache so the new numbers show promptly
        stamp = date.today().strftime("%Y%m%d")
        text = re.sub(r"(hero-(?:dark|light)\.svg)\?v=[0-9a-z]+", rf"\1?v={stamp}", text)
    if text != original:
        readme.write_text(text, encoding="utf-8")
        changed_files.append("README.md")

    print("changed:", changed_files or "nothing (already current)")


if __name__ == "__main__":
    main()
