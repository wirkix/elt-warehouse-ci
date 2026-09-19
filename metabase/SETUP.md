# Setting up the live Metabase demo

Manual, account/domain-gated step -- Claude can't complete this on your
behalf. Follow this runbook yourself, or share SSH access afterward and I
can drive the rest.

Unlike ecobici-pulse's VM (deliberately zero inbound ports, since its live
demo is a separate Vercel app), this one needs to actually serve Metabase
to portfolio visitors, so it needs one public inbound port opened (443).

## 1. VM

Confirmed 2026-09-19: ecobici-pulse's Oracle Cloud Always Free VM
(`163.192.133.188`, see that repo's `scripts/setup_oracle_vm.md`) is up
and healthy -- reusing it, no new VM needed. One small Always Free VM runs
both projects' containers side by side.

This VM needs one extra ingress rule it didn't need for ecobici-pulse
alone: **HTTPS (443)** from `0.0.0.0/0` in the VM's subnet security list
(ecobici-pulse's "zero inbound ports beyond SSH" design doesn't apply
here, since this VM now also needs to be Metabase's public entry point).

## 2. Domain (DuckDNS) + Databricks JDBC driver

Using [DuckDNS](https://www.duckdns.org) -- a free dynamic-DNS provider,
no domain purchase needed, and Caddy can still get a real Let's Encrypt
cert for a `*.duckdns.org` name same as any other domain:

1. Sign in at https://www.duckdns.org with GitHub/Google/etc.
2. Under "domains", add a subdomain -- suggest `elt-warehouse-ci` (giving
   `elt-warehouse-ci.duckdns.org`); pick another if it's taken.
3. In the IP field next to it, enter the VM's public IP
   (`163.192.133.188`) and click "update ip". That's it -- no ongoing
   dynamic-update script needed since this VM's IP is stable.
4. Download the Databricks JDBC driver Metabase plugin jar (from
   [Databricks' driver downloads page](https://www.databricks.com/spark/jdbc-drivers-download)
   or the community Metabase-Databricks driver's GitHub releases) into
   `metabase/plugins/` on the VM -- Metabase doesn't bundle a Databricks
   driver by default.

## 3. Deploy

```bash
git clone https://github.com/wirkix/elt-warehouse-ci.git
cd elt-warehouse-ci/metabase
cp Caddyfile.example Caddyfile
nano Caddyfile   # confirm it has your real *.duckdns.org name
mkdir -p plugins  # drop the driver jar here (step 2)
docker compose up -d
```

## 4. Configure Metabase

Open `https://elt-warehouse-ci.duckdns.org` (or whatever subdomain you
picked), complete Metabase's first-run setup wizard, then **Admin ->
Databases -> Add a database**:

- Type: Databricks
- Host: the same `DATABRICKS_HOST` as `.env` (no `https://` prefix)
- HTTP path: the same `DATABRICKS_HTTP_PATH`
- Personal access token: the same `DATABRICKS_TOKEN`
- Catalog: `workspace`

Then build dashboards against `nba_marts.fact_game` /
`nba_marts.fact_player_game_stats` (team/player leaderboards, scoring
trends over the season -- see the repo README for the exact mart schema),
and set the relevant dashboard's public sharing link on for the portfolio
card's `demo` link (Admin -> Sharing -> Public Sharing must be enabled
first).

## Status

VM confirmed reusable (step 1 done). Still blocked on you for: claiming
the DuckDNS subdomain + pointing it at the VM's IP, opening port 443 on
the VM's security list, and downloading the Databricks JDBC driver jar
(step 2). Tell me the subdomain you picked and I can drive steps 3-4 over
SSH from there.
