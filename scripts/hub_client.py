"""Client for Flathub's public per-day stats mirror at hub.flathub.org.

This module fetches those stats and keeps only the refs needed to estimate
active users: the FreeDesktop Platform runtime and its Mesa GL driver
extension.
"""

from __future__ import annotations

import datetime
import json
import re
import urllib.error
import urllib.request

HUB_BASE = "https://hub.flathub.org/stats"
USER_AGENT = "flathub-active-users/1.0 (+https://github.com/cassidyjames/flathub-active-users)"

# The first date flathub-stats has data for (also used by flathub.org's backend).
FIRST_STATS_DATE = datetime.date(2018, 4, 29)

_ref_re = re.compile(r"^(org\.freedesktop\.Platform(?:\.GL\.default)?)/([\w.\-]+)$")

class FetchError(Exception):
    pass

def day_url(date: datetime.date, channel: str = "stable") -> str:
    return f"{HUB_BASE}/{channel}/{date:%Y}/{date:%m}/{date:%d}.json"

def fetch_day(date: datetime.date, channel: str = "stable", timeout: float = 30.0) -> dict | None:
    """Fetch and return the raw JSON for one day, or None if it doesn't exist."""
    url = day_url(date, channel)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as err:
        if err.code == 404:
            return None
        raise FetchError(f"HTTP {err.code} fetching {url}") from err
    except (urllib.error.URLError, OSError, TimeoutError) as err:
        raise FetchError(f"Failed to fetch {url}: {err}") from err

def compact_record(date: datetime.date, raw: dict) -> dict:
    """Reduce a full daily stats blob to the fields we track long-term."""
    tracked_refs: dict[str, dict[str, list[int]]] = {}
    for ref_id, arch_counts in raw.get("refs", {}).items():
        if _ref_re.match(ref_id):
            tracked_refs[ref_id] = arch_counts

    return {
        "date": date.isoformat(),
        "refs": tracked_refs,
    }

def date_range(start: datetime.date, end: datetime.date):
    """Yield dates from start to end, inclusive."""
    current = start
    one_day = datetime.timedelta(days=1)
    while current <= end:
        yield current
        current += one_day
