# Estimated Active Flathub Users

An attempt at automatically estimating the number of active users of Flathub, based on the manual method used for the [over one million active users](https://docs.flathub.org/blog/over-one-million-active-users-and-growing) and [2 billion downloads](https://docs.flathub.org/blog/2-billion-downloads-2024) blog posts.

The goal is to demonstrate the adoption of Flathub and Flatpak by Linux users, encouraging app developers to distribute their apps on Flathub. My hope is that having this in the open enables people to validate the claims and poke any holes in the method so it can be improved.

Check out the current estimate and a basic explanation of the methodology on the [live website](http://cassidyjames.com/flathub-active-users/).

## Notes

Some notes and caveats from building this, in no particular order:

- **This counts Flatpak installations, not people.** Updates are a good signal of _active installations_, but this is technically not the same as individual people: one person may have many installations, or a machine shared by many people may have one system Flatpak installation.

- **NVIDIA users may be undercounted.** I'm not actually sure if NVIDIA-only systems pull in `GL.default` or not. If not, this method misses those installations.

## Data sources

- **Daily download and update counts**: produced by [flathub-infra/flathub-stats](https://github.com/flathub-infra/flathub-stats), filtered to the refs we're interested in and stored in `data/daily-stats.jsonl`

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

- `active-users.json`: headline estimation, plus supporting metadata
- `active-users-trend.json`: individual datapoints used to generate the detailed chart
