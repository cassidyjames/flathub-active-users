# Estimated Active Flathub Users

For the [over one million active users](https://docs.flathub.org/blog/over-one-million-active-users-and-growing) and [2 billion downloads](https://docs.flathub.org/blog/2-billion-downloads-2024) posts on the Flathub blog, I hand-estimated the active-user figure by cross-referencing the number of updates to FreeDesktop SDK base runtime from [klausenbusk.github.io/flathub-stats](https://klausenbusk.github.io/flathub-stats) with GitLab release tags. This repo attempts to address [flathub-infra/website#2945](https://github.com/flathub-infra/website/issues/2945) by automating the process.

Each day (and on each push to main), CI fetches Flathub's public per-day stats, computes an estimate of active users, and publishes the results as a static JSON API and little web dashboard. My hope is that having it in the open encourages people to validate the claims and poke any holes in the method so it can be improved.

Some notes/caveats from building this, in no particular order:

- **Patch release adoption is measured over the release's whole life.** We count updates from when Flathub starts serving a release until the next one arrives, however long that is. Since we only count updates—never fresh installs—an installation shows up at most once per release, so a longer window doesn't double-count anyone; it just catches machines that update less often.

- **A branch's first release is measured by downloads, not updates.** There's nothing to update from when a branch launches, so `.0` releases used to be skipped entirely. We now count downloads over that window instead; in practice they're almost all fresh installs (25.08.0 saw 1,875,105 downloads against 2 updates). These windows are usually short—four to seven days, since `.1` follows quickly—so the numbers land well under the estimate and rarely move it. The one exception so far is 20.08.0, whose 58-day window set the floor in late 2020.

- **We can't detect when a branch's first release starts being served.** Arrival detection looks for a spike above the previous week's updates, and a brand-new branch has no previous week, so the window starts at the tag date instead. The first day or two is typically near-zero as a result, which makes these points a slight undercount.

- **Points on the chart aren't directly comparable to each other.** There's a bias toward releases that happened to sit around longer, and thus we were able to count more updates being delivered to infrequent updaters.

- **FreeDesktop SDK base runtime _or_ Mesa GL driver extension.** We count whichever is higher; typically it's the Mesa GL driver extension, but the base runtime was useful to measure especially earlier on.

- **Multiple FreeDesktop SDK branches are in use at a time.** Not all apps in active use migrate to the newest runtimes, so we can never sum the number of updates to different branches; instead, we base the estimate of active users on the highest count of updates to a single branch.

- **Release cycles plus the app ecosystem create noise!** There are so many variables that can introduce noise and perceived dips in active users; this is especially visible when one branch's popularity is falling in favor of a newer branch. To help paper over this unavoidable volatility, we can base our estimate on the highest number we've seen in the past six months. Even still, a dip in the chart is not necessarily evidence of a decline in users.

- **Updates aren't available for download exactly when the release is cut.** At first I was basing things off of the literal patch release timestamps from freedesktop-sdk, but I realized that what actually matters is when Flathub starts serving the build; to account for this, we measure when there's a spike in downloads to the branch, and base the patch release window from there. 

- **This counts Flatpak installations, not people.** Updates are a good signal of _active installations_, but this is technically not the same as individual people: one person may have many installations, or a machine shared by many people may have one system Flatpak installation.

- **NVIDIA users may be undercounted.** I'm not actually sure if NVIDIA-only systems pull in `GL.default` or not. If not, this method misses those installations.

- **The most recent estimate lags by about a release cycle.** A release can only be measured once the next one supersedes it, so the estimate is always at least one patch release behind.

## Data sources

- **Daily download and update counts**: produced by [flathub-infra/flathub-stats](https://github.com/flathub-infra/flathub-stats), filtered to the refs we and stored in `data/daily-stats.jsonl`

- **FreeDesktop SDK point releases**: tags on [gitlab.com/freedesktop-sdk/freedesktop-sdk](https://gitlab.com/freedesktop-sdk/freedesktop-sdk), fetched via the GitLab API

## Run locally

Nothing special needed besides Python and its standard library.

```sh
python3 scripts/fetch_daily_stats.py    # incremental; safe to re-run
python3 scripts/fetch_releases.py
python3 scripts/compute_active_users.py
```

## API

I thought it could be interesting to publish an "api endpoint" of the estimate, so the following are also statically served from `api/`:

- `active-users.json`: headline estimation, plus metadata like the specific runtime release and measurement window (whose length now varies per release, reported as `window.days`); `kind` says whether the number counts `updates` or, for a branch's first release, `downloads`
- `active-users-trend.json`: individual datapoints used to generate the detailed chart
