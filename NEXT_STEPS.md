# Next steps

Snapshot as of 2026-09-19. The pipeline itself is done and verified end
to end (see README/CLAUDE.md) -- everything left is deployment/wiring.

## 1. Open port 443 (you're doing this tomorrow)

Two separate firewalls, both need it -- see `metabase/SETUP.md`'s
"Status" section for the exact commands/console steps:
- OCI Security List (console, manual)
- Host-level iptables on the VM (drafted, needs your go-ahead to run)

## 2. Finish the Metabase deploy (blocked on #1)

Once port 443 is open on both firewalls:

```bash
ssh -i ~/.ssh/ecobici_pulse_oracle ubuntu@163.192.133.188
git clone https://github.com/wirkix/elt-warehouse-ci.git
cd elt-warehouse-ci/metabase
mkdir -p plugins
exit  # back on your machine, copy the driver jar up:
scp -i ~/.ssh/ecobici_pulse_oracle databricks/databricks-jdbc-3.4.2.jar \
    ubuntu@163.192.133.188:~/elt-warehouse-ci/metabase/plugins/
# back on the VM:
cp Caddyfile.example Caddyfile   # already points at elt-warehouse-ci.duckdns.org
docker compose up -d
```

Then open `https://elt-warehouse-ci.duckdns.org`, run Metabase's first-run
setup wizard, add the Databricks database connection (host/http_path/token
from `.env`, catalog `workspace`), build a dashboard against
`nba_marts.fact_game` (team results/margins/win-loss over the season),
and turn on Public Sharing for it (Admin -> Sharing).

Tell me once port 443 is open and I can drive all of this over SSH myself.

## 3. Final portfolio card update (blocked on #2)

`professional-website` PR #17 currently only fixes the `github` link.
Once Metabase has a public dashboard link, still needs:
- Real Spanish copy update in `src/lib/i18n/dictionaries.ts` (id 6) if the
  current placeholder copy needs adjusting for the final games-only scope
  (no player stats -- see this repo's README "Why this design").
- `demo` link -> the Metabase public dashboard URL.
- Consider adding a "docs" link/button to the card pointing at
  https://wirkix.github.io/elt-warehouse-ci/ (the published dbt docs) --
  this project's whole pitch is tests+docs+CI, worth surfacing directly
  rather than only via the README.
- Merge PR #17 (or fold these into a new commit on it) once all of the
  above is in.

## Also still open, separate project

economic-pulse-lakehouse (roadmap project #4) is still blocked on you
independently of all this -- Tableau Public workbook publish, and
`professional-website` PR #8 merge. Unrelated to elt-warehouse-ci, just
flagging so it doesn't get lost.
