# CLAUDE.md

Guidance for Claude Code (and future contributors) working in this repo.

## What this is

Project #5 of alois-wirkes.com's 6-project portfolio roadmap: an NBA data
ELT warehouse on Databricks Free Edition (Delta Lake, Unity Catalog) built
dbt-first -- staging/marts models, schema + custom data tests, dbt docs,
and a GitHub Actions CI pipeline that runs `dbt build` on every push/PR so
a broken model or failing test blocks the merge, not just gets noticed
later. Visualized in a self-hosted Metabase instance.

## Repo layout

```
extract/
  client.py     # balldontlie API client: cursor pagination, 5 req/min throttle, 429/5xx retry
  models.py     # pydantic models per endpoint (Team, Player, Game)
  landing.py    # lands raw JSON into Databricks Delta staging tables, MERGEd by id
  run.py        # entrypoint: python -m extract.run --seasons 2024 2025
dbt/
  dbt_project.yml
  profiles.yml.example
  macros/generate_schema_name.sql   # custom +schema is used as-is, not concatenated with target schema
  models/staging/   # views, one per raw table -- parses payload JSON, casts types
  models/marts/     # tables: dim_team, dim_player, dim_date, fact_game
  tests/            # custom singular data tests
metabase/
  docker-compose.yml + Caddyfile.example + SETUP.md   # self-hosted, free VM
.github/workflows/
  ci.yml        # pytest + ruff always; dbt build against Databricks (needs repo secrets)
  refresh.yml   # daily cron: re-extract + dbt build, keeps the live demo current
tests/          # extract/ unit tests -- fixtures only, no live API or Databricks needed
```

## Local dev quirks

- **This dev machine's default Python (3.14) can't install `dbt-core`
  cleanly** -- Avast's HTTPS-scanning proxy breaks a raw network-fetch step
  in one of dbt-core's sub-dependencies (`dbt-core-experimental-parser`
  tries to download a prebuilt wheel from a GitHub release URL and fails
  TLS verification under Python 3.14's stricter cert validation). Use
  Python 3.12 instead: `py -3.12 -m venv .venv`. Same root cause and fix as
  [motor-analytics](https://github.com/wirkix/motor-analytics)'s `.venv`.
- `extract/client.py` calls `truststore.inject_into_ssl()` at import time
  (same fix ecobici-pulse and economic-pulse-lakehouse needed for this
  machine's Avast HTTPS interception) -- don't remove it or outbound calls
  to `api.balldontlie.io` may fail TLS verification on this machine even
  though they work fine in CI.
- **`dbt build`/`dbt run` on this dev machine spends ~5 minutes upfront on
  a "SPOG discovery" probe that fails and falls back** -- dbt-databricks
  1.12+ tries to auto-detect unified-workspace config by hitting
  `https://<host>/.well-known/databricks-config` using a plain
  `requests`/`urllib3` client that isn't patched with
  `truststore.inject_into_ssl()` (unlike `extract/client.py`), so it hits
  this same machine's usual Avast TLS-interception issue, retries for 5
  minutes, then falls back to the explicit profile config and runs
  normally. Verified this is dev-machine-only, not a real failure (the
  build still succeeds, 31/31 tests passed) -- expect CI to skip this
  delay entirely since GitHub Actions runners don't have Avast in the
  path.
- `dbt parse`/`dbt compile` need a `profiles.yml` with *some* Databricks
  target configured, even to just check Jinja/ref syntax -- `dbt parse`
  alone doesn't connect to the warehouse and is safe to run against dummy
  credentials for a quick sanity check; `dbt compile`/`dbt run`/`dbt build`
  all actually connect, so they hang or fail against a fake host. Verified
  this repo's models with `dbt parse` before real Databricks credentials
  existed; re-run `dbt build` for real once they do.

## Databricks-specific gotchas

- **Databricks Free Edition (renamed from "Community Edition") runs Unity
  Catalog by default, with exactly one preconfigured catalog named
  `workspace`** -- no `hive_metastore`, no ability to create additional
  catalogs on the free tier. `.env`'s `DATABRICKS_CATALOG` should stay
  `workspace` unless that changes.
- **dbt's default schema-naming concatenates the target schema with a
  model's custom `+schema` config** (target `nba` + custom `nba_staging`
  -> `nba_nba_staging`). `macros/generate_schema_name.sql` overrides this
  to use the custom schema name as-is, so `dbt_project.yml`'s
  `nba_staging`/`nba_marts` configs land exactly where named. Don't remove
  that macro without also fixing the resulting double-prefixed schema
  names.
- `extract/landing.py` MERGEs into `raw_<table>` via a `raw_<table>_staging`
  throwaway table on every run, keyed by the record's own `id` --
  deliberately not a raw-file landing pattern. economic-pulse-lakehouse hit
  a real bug landing straight into MinIO with no overwrite semantics
  (every rerun's randomly-named Parquet files piled up and got
  double-counted); MERGE avoids that class of bug here by construction
  rather than by remembering to clear a prefix each run.
- `dim_date` is generated via Databricks SQL's native
  `sequence()`/`explode()`, not `dbt_utils.date_spine()` -- this portfolio
  deliberately avoids a `dbt_utils` dependency (see job-market-radar's own
  CLAUDE.md for the same convention).
- **This Free Edition serverless warehouse 404s on `databricks-sql-connector`'s
  default Thrift transport** -- only the newer Statement Execution API
  (SEA) transport works externally here. `extract/landing.py` passes
  `use_sea=True` to `sql.connect()`; `dbt/profiles.yml.example` passes the
  equivalent via `connection_parameters: {use_sea: true}` (a documented
  dbt-databricks passthrough to the connector, not a dbt-native option).
  Don't drop either or every connection attempt 404s.
- **`cursor.executemany()` issues one sequential HTTP request per row, not
  a batched insert** (documented in the connector's own docstring). Landing
  ~7,400 players this way hung for 1.5+ hours doing effectively nothing.
  `land_records()` batches up to `INSERT_CHUNK_SIZE` (1000) rows into each
  `INSERT`'s `VALUES` list instead -- don't reintroduce `executemany` for
  bulk loads here.
- **A Databricks SEA connection left idle for a few minutes goes stale and
  the client hangs on the next statement instead of raising an error** (0s
  CPU, no active network connection, no exception -- ever). Hit this
  because balldontlie's 5 req/min limit means paginating ~7,400 players
  takes ~15 minutes, and the original code held one Databricks connection
  open across that whole fetch. `extract/run.py` now fetches each table
  fully from balldontlie *before* opening its Databricks connection
  (`_fetch_then_land`) specifically to avoid ever leaving a connection
  idle across a long pagination gap -- same class of bug as
  ecobici-pulse's dropped-connection consumer, just silent instead of a
  clean error here. If a future hang shows this same 0-CPU/no-connection
  signature, suspect a stale connection first.

## Known gotchas / history

- balldontlie's API changed since this project was scoped in the roadmap
  planning doc -- it now requires a free signup-issued API key
  (`BALLDONTLIE_API_KEY`, 5 req/min on the free tier) rather than being
  fully anonymous/keyless. `extract/client.py` throttles to
  `60 / RATE_LIMIT_PER_MIN` seconds between requests and retries on 429
  using the `Retry-After` header.
- **balldontlie's `/stats` endpoint (player-game box scores) requires
  their paid ALL-STAR tier ($9.99/mo)** -- discovered live via a 401 on
  the free-tier key, confirmed against their own docs. Deliberately not
  paying for it to keep this project's "$0 indefinitely" pitch intact, so
  the scope is teams/players/games only -- no `fact_player_game_stats`
  mart. If that tradeoff ever changes, `/stats` needs its own `Stat`
  pydantic model, client method, staging model, and mart re-added (all
  removed, not stubbed out, when this was decided).
- `.github/workflows/ci.yml`'s `dbt`/`docs` jobs check whether
  `secrets.DATABRICKS_HOST` is set and skip (not fail) if it's absent --
  this matters for PRs from a fork (no secret access) but also means
  **CI's "blocks bad models" guarantee only actually holds once
  `DATABRICKS_HOST`/`DATABRICKS_HTTP_PATH`/`DATABRICKS_TOKEN` are set as
  real repo secrets** (`gh secret set ...`). Don't assume CI is enforcing
  anything until those are confirmed set.
- GitHub Pages must be switched to "GitHub Actions" as its source
  (Settings -> Pages -> Build and deployment -> Source) once, or
  `ci.yml`'s `docs` job's `actions/deploy-pages` step will fail on the
  first run.

## Deployment

No traditional "deploy" -- `.github/workflows/refresh.yml` re-extracts +
`dbt build`s on a daily cron so the warehouse stays current without a
24/7 orchestrator (Databricks Free Edition SQL warehouses auto-suspend
between queries, so a long-running scheduler would mostly wait on cold
starts). Metabase runs continuously on a self-hosted free VM -- see
`metabase/SETUP.md`.
