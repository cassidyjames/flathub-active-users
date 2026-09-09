#!/usr/bin/env python3
"""Fetch FreeDesktop SDK patch release dates from GitLab tags. Stable point
releases are tagged `freedesktop-sdk-<branch>.<point>`; release candidates and
betas use suffixes like `rc.N` and are skipped. Tag commit dates are recorded to
be used by compute_active_users.py.

Usage:
    scripts/fetch_releases.py
    scripts/fetch_releases.py --out data/releases.json
"""

from __future__ import annotations

import argparse
import datetime
import json
import pathlib
import re
import sys
import urllib.error
import urllib.request

GITLAB_API = "https://gitlab.com/api/v4/projects/freedesktop-sdk%2Ffreedesktop-sdk/repository/tags"
USER_AGENT = "flathub-active-users/1.0 (+https://github.com/cassidyjames/flathub-active-users)"

# Exclude pre-releases
TAG_RE = re.compile(r"^freedesktop-sdk-(\d+\.\d+)\.(\d+)$")

DEFAULT_OUT = pathlib.Path(__file__).resolve().parent.parent / "data" / "releases.json"

def fetch_all_tags() -> list[dict]:
    tags = []
    page = 1
    while True:
        url = f"{GITLAB_API}?per_page=100&page={page}&order_by=name&sort=desc"
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                batch = json.loads(resp.read())
        except urllib.error.URLError as err:
            raise RuntimeError(f"Failed to fetch {url}: {err}") from err

        if not batch:
            break
        tags.extend(batch)
        page += 1
    return tags

def build_releases(tags: list[dict]) -> dict[str, list[dict]]:
    branches: dict[str, list[dict]] = {}
    for tag in tags:
        match = TAG_RE.match(tag["name"])
        if not match:
            continue
        branch, point_str = match.groups()
        point = int(point_str)
        commit_date = tag["commit"]["created_at"][:10]  # YYYY-MM-DD, UTC-ish per GitLab
        branches.setdefault(branch, []).append(
            {"version": f"{branch}.{point}", "point": point, "date": commit_date}
        )

    for points in branches.values():
        points.sort(key=lambda p: p["point"])

    return dict(sorted(branches.items(), key=lambda kv: kv[1][0]["date"]))

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=pathlib.Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    branches = build_releases(fetch_all_tags())

    args.out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.datetime.now(datetime.UTC).isoformat(),
        "source": "https://gitlab.com/freedesktop-sdk/freedesktop-sdk/-/tags",
        "branches": branches,
    }
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

    total_releases = sum(len(points) for points in branches.values())
    print(f"wrote {len(branches)} branches, {total_releases} point releases to {args.out}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
