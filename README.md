# Estimated Active Flathub Users

For the [over one million active users](https://docs.flathub.org/blog/over-one-million-active-users-and-growing) and [2 billion downloads](https://docs.flathub.org/blog/2-billion-downloads-2024) posts on the Flathub blog, I hand-estimated the active-user figure by cross-referencing the number of updates to FreeDesktop SDK base runtime from [klausenbusk.github.io/flathub-stats](https://klausenbusk.github.io/flathub-stats) with GitLab release tags. This repo attempts to address [flathub-infra/website#2945](https://github.com/flathub-infra/website/issues/2945) by automating the process.

Each day (and on each push to main), CI fetches Flathub's public per-day stats, computes an estimate of active users, and publishes the results as a static JSON API and little web dashboard. My hope is that having it in the open encourages people to validate the claims and poke any holes in the method so it can be improved.

Some notes/caveats from building this, in no particular order:

- **Patch release adoption is measured over its first 28 days.** Patch release lifecycles shorter than that introduce noise and aren't comparable since it takes time for people to come online and run Flatpak updates; instead, we omit shorter patch release windows.

- **FreeDesktop SDK base runtime _or_ Mesa GL driver extension.** We count whichever is higher; typically it's the Mesa GL driver extension, but the base runtime was useful to measure especially earlier on.

- **Multiple FreeDesktop SDK branches are in use at a time.** Not all apps in active use migrate to the newest runtimes, so we can never sum the number of updates to different branches; instead, we base the estimate of active users on the highest count of updates to a single branch.

- **Release cycles plus the app ecosystem create noise!** There are so many variables that can introduce noise and perceived dips in active users; this is especially visible when one branch's popularity is falling in favor of a newer branch. To help paper over this unavoidable volatility, we can base our estimate on the highest number we've seen in the past six months. Even still, a dip in the chart is not necessarily evidence of a decline in users.

- **Updates aren't available for download exactly when the release is cut.** At first I was basing things off of the literal patch release timestamps from freedesktop-sdk, but I realized that what actually matters is when Flathub starts serving the build; to account for this, we measure when there's a spike in downloads to the branch, and base the patch release window from there. 

- **This counts Flatpak installations, not people.** Updates are a good signal of _active installations_, but this is technically not the same as individual people: one person may have many installations, or a machine shared by many people may have one system Flatpak installation.

- **NVIDIA users may be undercounted.** I'm not actually sure if NVIDIA-only systems pull in `GL.default` or not. If not, this method misses those installations.

- **The most recent estimate can end up being months old.** The latest estimate depends on there having been a patch release available for a branch for 28 days; if there is no patch release made, or multiple patch releases are made less than 28-days apart, it causes a delay in the estimate.

## Data sources

- **Daily download and update counts**: produced by [flathub-infra/flathub-stats](https://github.com/flathub-infra/flathub-stats), filtered to the refs we and stored in `data/daily-stats.jsonl`

- **FreeDesktop SDK point releases**: tags on [gitlab.com/freedesktop-sdk/freedesktop-sdk](https://gitlab.com/freedesktop-sdk/freedesktop-sdk), fetched via the GitLab API

## Run locally

Nothing special needed besides Python and its standard library.

```sh
python3 scripts/fetch_daily_stats.py    # incremental; safe to re-run
python3 scripts/fetch_releases.py
python3 scripts/compute_active_users.py
python3 -m unittest discover -s tests
```

## API

I thought it could be interesting to publish an "api endpoint" of the estimate, so the following are also statically served from `api/`:

- `active-users.json`: headline estimation, plus metadata like the specific runtime release and measurement window
- `active-users-trend.json`: individual datapoints used to generate the detailed chart
