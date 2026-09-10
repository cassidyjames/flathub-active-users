#!/usr/bin/env python3
"""Estimate active Flathub user from FreeDesktop SDK runtime update counts.
See README.md for details and caveats!

Usage:
    scripts/compute_active_users.py
"""

from __future__ import annotations

import argparse
import datetime
import json
import pathlib
import statistics
import sys

DATA_DIR = pathlib.Path(__file__).resolve().parent.parent / "data"
PUBLIC_API_DIR = pathlib.Path(__file__).resolve().parent.parent / "public" / "api"

REFS = ("org.freedesktop.Platform.GL.default", "org.freedesktop.Platform")

# Flathub reports [downloads, updates] per arch, where updates are a subset
DOWNLOADS, UPDATES = 0, 1

MIN_WINDOW_DAYS = 1

# How far back a measurement still counts towards the current estimate
TRAILING_DAYS = 180

# A release typically arrives on Flathub some days after tagged; when it does,
# updates to that branch jump roughly tenfold for a day or two
ARRIVAL_BASELINE_DAYS = 7
ARRIVAL_SEARCH_DAYS = 5
ARRIVAL_SPIKE_RATIO = 2
ARRIVAL_MIN_BASELINE = 500

def load_daily_stats(path: pathlib.Path) -> dict[str, dict]:
    records: dict[str, dict] = {}
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            records[record["date"]] = record
    return records

def load_releases(path: pathlib.Path) -> dict[str, list[dict]]:
    return json.loads(path.read_text())["branches"]

def daily_count(
    daily_stats: dict[str, dict], ref: str, branch: str, date: datetime.date, column: int = UPDATES
) -> int | None:
    """Downloads or updates served for one ref on one day, or None if that day is missing"""
    record = daily_stats.get(date.isoformat())
    if record is None:
        return None
    arch_counts = record["refs"].get(f"{ref}/{branch}", {})
    return sum(counts[column] for counts in arch_counts.values())

def sum_counts(
    daily_stats: dict[str, dict],
    ref: str,
    branch: str,
    start: datetime.date,
    days: int,
    column: int = UPDATES,
) -> tuple[int, int]:
    """Sum one column over `days` days from `start`. Returns (total, days_with_data)"""
    total = 0
    days_with_data = 0
    for offset in range(days):
        count = daily_count(daily_stats, ref, branch, start + datetime.timedelta(days=offset), column)
        if count is not None:
            days_with_data += 1
            total += count
    return total, days_with_data

def baseline_updates(
    daily_stats: dict[str, dict], ref: str, branch: str, before: datetime.date
) -> float | None:
    """Median daily updates for a ref over the week before `before`, if that week has data"""
    days = []
    for offset in range(1, ARRIVAL_BASELINE_DAYS + 1):
        updates = daily_count(daily_stats, ref, branch, before - datetime.timedelta(days=offset))
        if updates is not None:
            days.append(updates)
    if len(days) < ARRIVAL_BASELINE_DAYS // 2:
        return None
    return statistics.median(days)

def find_arrival(
    daily_stats: dict[str, dict], branch: str, tag_date: datetime.date, refs: tuple[str, ...] = REFS
) -> datetime.date:
    """The day Flathub apparently started serving a release"""
    baselines = {
        ref: baseline
        for ref in refs
        if (baseline := baseline_updates(daily_stats, ref, branch, tag_date)) is not None
    }
    if not baselines:
        return tag_date

    ref = max(baselines, key=baselines.get)
    if baselines[ref] < ARRIVAL_MIN_BASELINE:
        return tag_date

    threshold = baselines[ref] * ARRIVAL_SPIKE_RATIO
    for offset in range(ARRIVAL_SEARCH_DAYS + 1):
        day = tag_date + datetime.timedelta(days=offset)
        updates = daily_count(daily_stats, ref, branch, day)
        if updates is not None and updates >= threshold:
            return day
    return tag_date

def build_measurements(
    daily_stats: dict[str, dict],
    releases: dict[str, list[dict]],
    refs: tuple[str, ...] = REFS,
    min_days: int = MIN_WINDOW_DAYS,
) -> list[dict]:
    """One measurement per (ref, branch, release), spanning the whole time that
    release was the newest one available for its branch.

    A branch's first release is measured by downloads. Patch releases are
    measured by updates.

    A release is skipped if there are no daily stats, or if there are zero
    downloads/updates. `days_with_data` helps identify when a release is missing
    days from its daily stats.
    """
    measurements = []
    for branch, points in releases.items():
        arrivals = [find_arrival(daily_stats, branch, datetime.date.fromisoformat(p["date"]), refs) for p in points]
        # zip stops at the last release, which has no successor to bound it
        for current, start, next_start in zip(points, arrivals, arrivals[1:]):
            initial = current["point"] == 0
            window = (next_start - start).days
            if window < min_days:
                continue
            end = start + datetime.timedelta(days=window)
            column = DOWNLOADS if initial else UPDATES
            for ref in refs:
                total, days_with_data = sum_counts(daily_stats, ref, branch, start, window, column)
                if days_with_data == 0 or total == 0:
                    continue
                measurements.append(
                    {
                        "date": end.isoformat(),
                        "active_users": total,
                        "kind": "downloads" if initial else "updates",
                        "ref": ref,
                        "branch": branch,
                        "release": current["version"],
                        "tag_date": current["date"],
                        "window_start": start.isoformat(),
                        "window_end": end.isoformat(),
                        "window_days": window,
                        "days_with_data": days_with_data,
                    }
                )
    measurements.sort(key=lambda m: (m["date"], m["ref"], m["branch"]))
    return measurements

def build_trend(measurements: list[dict], trailing_days: int = TRAILING_DAYS) -> list[dict]:
    """Each measurement is the new floor, then measurements older than
    `trailing_days` are dropped
    """
    trend = []
    for date in sorted({m["date"] for m in measurements}):
        cutoff = (datetime.date.fromisoformat(date) - datetime.timedelta(days=trailing_days)).isoformat()
        recent = [m for m in measurements if cutoff <= m["date"] <= date]
        trend.append({**max(recent, key=lambda m: m["active_users"]), "date": date})
    return trend

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--daily-stats", type=pathlib.Path, default=DATA_DIR / "daily-stats.jsonl")
    parser.add_argument("--releases", type=pathlib.Path, default=DATA_DIR / "releases.json")
    parser.add_argument("--out-dir", type=pathlib.Path, default=PUBLIC_API_DIR)
    args = parser.parse_args()

    daily_stats = load_daily_stats(args.daily_stats)
    releases = load_releases(args.releases)

    measurements = build_measurements(daily_stats, releases)
    trend = build_trend(measurements)
    headline = trend[-1] if trend else None

    generated_at = datetime.datetime.now(datetime.UTC).isoformat()

    active_users = {
        "generated_at": generated_at,
        "active_users": None,
        "note": "No release has been superseded yet, so there's nothing to measure.",
    }
    if headline:
        active_users |= {
            "active_users": headline["active_users"],
            "as_of": headline["date"],
            "kind": headline["kind"],
            "ref": headline["ref"],
            "branch": headline["branch"],
            "based_on_release": headline["release"],
            "window": {
                "start": headline["window_start"],
                "end": headline["window_end"],
                "days": headline["window_days"],
                "days_with_data": headline["days_with_data"],
            },
            "note": None,
        }

    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "active-users.json").write_text(json.dumps(active_users, indent=2, sort_keys=True) + "\n")
    (args.out_dir / "active-users-trend.json").write_text(
        json.dumps(
            {
                "generated_at": generated_at,
                "trailing_days": TRAILING_DAYS,
                "refs": list(REFS),
                "trend": trend,
                "measurements": measurements,
            },
            indent=2,
        )
        + "\n"
    )

    if headline:
        print(
            f"at least {headline['active_users']:,} active devices as of {headline['date']} "
            f"[{headline['ref']}/{headline['branch']}, release {headline['release']}, "
            f"{headline['window_start']} + {headline['window_days']}d, {headline['kind']}]"
        )
    else:
        print("no measurable release windows yet")
    print(f"{len(measurements)} measurements across {len(releases)} branches -> {len(trend)} trend points")
    return 0

if __name__ == "__main__":
    sys.exit(main())
