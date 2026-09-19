# Setting up the live Metabase demo

Manual, account/domain-gated step -- Claude can't complete this on your
behalf. Follow this runbook yourself, or share SSH access afterward and I
can drive the rest.

Unlike ecobici-pulse's VM (deliberately zero inbound ports, since its live
demo is a separate Vercel app), this one needs to actually serve Metabase
to portfolio visitors, so it needs one public inbound port opened (443).

## 1. VM

Reuse ecobici-pulse's Oracle Cloud Always Free VM if it's still up (check
`ssh ubuntu@<its-ip> docker ps` first) -- one small Always Free VM can run
both projects' containers side by side. Otherwise, follow
`ecobici-pulse/scripts/setup_oracle_vm.md` steps 1-2 to create a fresh one.

If reusing the existing VM, open one extra ingress rule this time: **HTTPS
(443)** from `0.0.0.0/0` in the VM's subnet security list (ecobici-pulse's
"zero inbound ports beyond SSH" design doesn't apply here, since this VM
now also needs to be Metabase's public entry point).

## 2. Domain + Databricks JDBC driver

1. Point a subdomain (e.g. `metabase.yourdomain.tld`) at the VM's public
   IP -- Caddy (below) needs this to issue a Let's Encrypt cert. If you
   don't have a domain yet, a free one from a provider like Cloudflare's
   `*.trycloudflare.com` tunnel is an alternative to a real DNS record;
   tell me which and I'll adjust the Caddyfile.
2. Download the Databricks JDBC driver Metabase plugin jar (from
   [Databricks' driver downloads page](https://www.databricks.com/spark/jdbc-drivers-download)
   or the community Metabase-Databricks driver's GitHub releases) into
   `metabase/plugins/` on the VM -- Metabase doesn't bundle a Databricks
   driver by default.

## 3. Deploy

```bash
git clone https://github.com/wirkix/elt-warehouse-ci.git
cd elt-warehouse-ci/metabase
cp Caddyfile.example Caddyfile
nano Caddyfile   # fill in your real subdomain
mkdir -p plugins  # drop the driver jar here (step 2)
docker compose up -d
```

## 4. Configure Metabase

Open `https://metabase.yourdomain.tld`, complete Metabase's first-run setup
wizard, then **Admin -> Databases -> Add a database**:

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

Not yet done -- blocked on you for the VM/domain/driver-jar steps above.
