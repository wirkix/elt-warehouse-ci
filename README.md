# elt-warehouse-ci

A modern ELT warehouse over live NBA data (balldontlie), run the way a
senior data team actually runs one: dbt tests + docs, and a GitHub Actions
CI pipeline that blocks a bad model before it ships -- on Databricks
Community/Free Edition (Delta Lake, Unity Catalog), so it stays live at $0
indefinitely instead of on a trial clock.

```
balldontlie API --(Python, rate-limited to 5 req/min)--> raw JSON
    --> Databricks Delta staging schema (nba_staging, landed as-is + MERGEd
        by id so reruns update rows instead of duplicating them)
    --> dbt (dbt-databricks):
        models/staging  (views, one per raw table, JSON parsed + typed)
            --> models/marts (tables: dim_team, dim_player, dim_date,
                fact_game)
        schema tests (unique/not_null/relationships) + a custom data test
        + dbt docs
    --> GitHub Actions: dbt build on every push/PR against Databricks,
        failing tests fail the workflow; dbt docs published to GitHub
        Pages on push to main
    --> Metabase (self-hosted on a free VM) over the Databricks SQL
        warehouse -- team standings/results, scoring trends over the season
```

## Why this design

- **Databricks Free Edition, not a local Spark/Delta stand-in.** Unlike
  [motor-analytics](https://github.com/wirkix/motor-analytics) or
  [job-market-radar](https://github.com/wirkix/job-market-radar), which
  were built and fully verified against a local fixture before real
  credentials existed, dbt-databricks has no local emulator -- `dbt run`
  needs a real workspace from the first row. So this repo's extract/
  layer (balldontlie client + pydantic models) is unit-tested against
  fixtures with no Databricks dependency, but the landing layer and the
  entire dbt project only run against a real Databricks SQL warehouse.
- **CI that can actually fail the build.** The roadmap's ask for this
  project specifically was "tests, docs, and a CI pipeline that blocks bad
  models before they ship" -- so `dbt build` (not just `dbt run`) is what
  CI invokes, and a failing schema/data test fails the GitHub Actions run.
- **Hand-rolled surrogate keys/date spine, no dbt_utils.** Same convention
  as job-market-radar -- balldontlie's own integer ids are stable and
  reliable, so marts key off them directly rather than hashing a surrogate
  key; `dim_date` is generated via Databricks SQL's native
  `sequence()`/`explode()` instead of `dbt_utils.date_spine()`.
- **Metabase, not Tableau/Power BI.** The other five portfolio projects
  already cover Tableau Public and Power BI; Metabase is open-source and
  self-hostable, so it's the one BI tool in the portfolio that isn't a
  vendor's own free tier.
- **Games-level scope only, no player-game box scores.** balldontlie's
  `/stats` endpoint gates that behind their paid ALL-STAR tier
  ($9.99/mo) -- found live via a 401, confirmed against their own docs.
  Paying for it would break this project's "$0 indefinitely" pitch, so
  the scope is teams/players/games (all free-tier) and marts built from
  those: final scores, margins, win/loss, no per-player stat lines.

## Setup

```bash
git clone https://github.com/wirkix/elt-warehouse-ci.git
cd elt-warehouse-ci
py -3.12 -m venv .venv   # see "Known gotchas" -- default Python breaks dbt-core installs here
.venv/Scripts/activate
pip install -r requirements-dev.txt
cp .env.example .env
```

Fill in `.env`:

- `BALLDONTLIE_API_KEY` -- free signup at https://app.balldontlie.io/signup
  (free tier: 5 req/min, this repo's extract client throttles to match).
- `DATABRICKS_HOST` / `DATABRICKS_HTTP_PATH` / `DATABRICKS_TOKEN` -- create
  a free workspace at https://databricks.com/try-databricks (Free/Community
  Edition), create a SQL warehouse, and generate a personal access token
  under User Settings -> Developer -> Access tokens. The HTTP path is on
  the warehouse's own "Connection details" tab.

## Running the pieces individually

Extract + land raw data:

```bash
python -m extract.run --seasons 2024 2025
```

Run dbt (staging + marts + tests):

```bash
cd dbt
cp profiles.yml.example profiles.yml   # or point DBT_PROFILES_DIR at ~/.dbt
dbt build
dbt docs generate && dbt docs serve
```

## Tests

```bash
pytest -q          # extract/ unit tests -- fixtures only, no live API/Databricks needed
ruff check extract tests
cd dbt && dbt build   # schema + custom data tests, needs real Databricks credentials
```

## Data model

- `nba_staging.raw_teams` / `raw_players` / `raw_games` -- landed raw JSON
  payloads (one `payload` STRING column each), MERGEd by `id` on every
  extract run.
- `nba_marts.dim_team`, `dim_player`, `dim_date` -- descriptive dimensions.
- `nba_marts.fact_game` -- one row per completed game (`status = 'Final'`),
  with home/visitor scores, margin, and the winning team.

## Known limitations

- `dim_date` only spans dates that appear in `fact_game` -- it's not a
  general-purpose calendar table.
- CI's `dbt` and `docs` jobs need `DATABRICKS_HOST`/`DATABRICKS_HTTP_PATH`/
  `DATABRICKS_TOKEN` set as GitHub Actions repo secrets; without them the
  jobs skip (rather than fail) so PRs from a fork don't break, but that
  also means this repo's own CI only genuinely blocks bad models once
  those secrets are set.
- No Airflow/orchestration -- extract is run manually or via a scheduled
  GitHub Actions workflow (see CLAUDE.md), not a long-running scheduler,
  since Databricks Free Edition clusters aren't meant to run 24/7 anyway.
