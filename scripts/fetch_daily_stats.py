#!/usr/bin/env python3
"""Incrementally fetch Flathub's public daily stats into data/daily-stats.jsonl.
Skips cached dates so it's safe to re-run.

Usage:
    scripts/fetch_daily_stats.py
    scripts/fetch_daily_stats.py --start 2018-04-29 --end 2026-09-06
    scripts/fetch_daily_stats.py --max-days 30   # for quick testing
"""

from __future__ import annotations

import argparse
import datetime
import json
import pathlib
import sys
import time

import hub_client

DEFAULT_DATA_FILE = pathlib.Path(__file__).resolve().parent.parent / "data" / "daily-stats.jsonl"

def load_existing_dates(path: pathlib.Path) -> set[str]:
    if not path.exists():
        return set()
    dates = set()
    with path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            dates.add(json.loads(line)["date"])
    return dates

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start", type=datetime.date.fromisoformat, default=hub_client.FIRST_STATS_DATE)
    parser.add_argument(
        "--end",
        type=datetime.date.fromisoformat,
        default=datetime.datetime.now(datetime.UTC).date() - datetime.timedelta(days=1),
        help="last date to fetch, inclusive (default: yesterday UTC)",
    )
    parser.add_argument("--channel", default="stable")
    parser.add_argument("--data-file", type=pathlib.Path, default=DEFAULT_DATA_FILE)
    parser.add_argument("--delay", type=float, default=0.05, help="seconds to sleep between requests")
    parser.add_argument("--max-days", type=int, default=None, help="stop after fetching this many new days")
    args = parser.parse_args()

    args.data_file.parent.mkdir(parents=True, exist_ok=True)
    existing = load_existing_dates(args.data_file)

    fetched = 0
    missing = 0
    errors = 0

    with args.data_file.open("a") as out:
        for date in hub_client.date_range(args.start, args.end):
            if date.isoformat() in existing:
                continue
            if args.max_days is not None and fetched >= args.max_days:
                break

            raw = None
            last_err = None
            for attempt in range(3):
                try:
                    raw = hub_client.fetch_day(date, channel=args.channel)
                    last_err = None
                    break
                except hub_client.FetchError as err:
                    last_err = err
                    time.sleep(1.0 * (attempt + 1))
            if last_err is not None:
                print(f"error: {last_err}", file=sys.stderr)
                errors += 1
                continue

            if raw is None:
                missing += 1
                continue

            record = hub_client.compact_record(date, raw)
            out.write(json.dumps(record, sort_keys=True) + "\n")
            out.flush()
            fetched += 1

            if fetched % 100 == 0:
                print(f"...fetched {fetched} days (up to {date.isoformat()})")

            time.sleep(args.delay)

    print(f"done: fetched {fetched} new days, {missing} missing, {errors} errors")
    return 1 if errors else 0

if __name__ == "__main__":
    sys.exit(main())
