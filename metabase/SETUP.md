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

1. Sign in at https://www.duckdns.org with GitHub/Google/etc. -- **done**,
   `elt-warehouse-ci.duckdns.org` resolves to `163.192.133.188` (verified
   via `nslookup` 2026-09-19).
2. Download the Databricks JDBC driver Metabase plugin jar (from
   [Databricks' driver downloads page](https://www.databricks.com/spark/jdbc-drivers-download)
   or the community Metabase-Databricks driver's GitHub releases) --
   **done**, saved locally at `databricks/databricks-jdbc-3.4.2.jar`
   (gitignored -- 41MB third-party binary, not committed). Still needs
   copying onto the VM's `metabase/plugins/` once that directory exists
   there (step 3), e.g.:
   ```bash
   scp -i ~/.ssh/ecobici_pulse_oracle databricks/databricks-jdbc-3.4.2.jar \
       ubuntu@163.192.133.188:~/elt-warehouse-ci/metabase/plugins/
   ```

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

Then build dashboards against `nba_marts.fact_game` (team results, scoring
margins, win/loss over the season -- see the repo README for the exact
mart schema; no player-game box scores, that's balldontlie's paid tier --
see README's "Why this design"), and set the relevant dashboard's public
sharing link on for the portfolio card's `demo` link (Admin -> Sharing ->
Public Sharing must be enabled first).

## Status

VM confirmed reusable, DuckDNS subdomain claimed and resolving, JDBC
driver jar downloaded locally (steps 1-2 done). Still blocked on you for
port 443 -- **two separate firewalls both need it opened**, not just one:

1. **OCI Security List** (cloud-level, console-only, I can't do this) --
   Networking -> Virtual Cloud Networks -> your VCN -> Security Lists ->
   add an ingress rule for TCP 443 from `0.0.0.0/0`.
2. **Host-level iptables** (inside the VM over SSH) -- checked 2026-09-19,
   this VM's `iptables` only has an explicit ACCEPT for port 22; port 443
   would currently hit the trailing REJECT rule even with (1) done. I
   drafted the fix but the harness blocked me from running it
   autonomously (firewall changes on a live VM need your explicit go-ahead
   each time, not just once) -- run this yourself, or tell me to go ahead
   and I will:
   ```bash
   sudo iptables -I INPUT 5 -p tcp -m state --state NEW --dport 443 -j ACCEPT
   sudo netfilter-persistent save
   ```

Once both are open, tell me and I'll drive step 3 onward (clone, scp the
jar, `docker compose up`, configure Metabase) over SSH.
