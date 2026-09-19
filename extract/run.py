"""Entrypoint: pulls teams/players/games from balldontlie and lands them
in the Databricks staging schema.

    python -m extract.run --seasons 2024 2025

Season numbers are the year a season *starts* in (balldontlie convention),
e.g. `2025` is the 2025-26 season.

Deliberately no player-game stats (box scores) -- balldontlie's /stats
gates that behind their paid ALL-STAR tier ($9.99/mo), which would break
this project's "stays live at $0 indefinitely" goal. Games-level results
(final scores, margins, win/loss) only.
"""

from __future__ import annotations

import argparse
import logging

from extract.client import BalldontlieClient
from extract.landing import get_connection, land_records
from extract.models import Game, Player, Team

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seasons", type=int, nargs="+", required=True)
    return parser.parse_args()


def _fetch_then_land(table: str, records) -> None:
    # Opens a fresh Databricks connection right before landing, rather
    # than reusing one connection across the whole run -- balldontlie's
    # 5 req/min limit means fetching a large table (e.g. ~7,400 players,
    # ~15 minutes) leaves a shared connection idle for minutes at a time.
    # Found live: the SEA client doesn't error on a connection gone stale
    # after an idle gap like that, it just hangs indefinitely on the next
    # statement (0s CPU, no active network connection, no exception ever
    # raised) -- the same class of bug as ecobici-pulse's dropped-
    # connection consumer, just silent instead of a clean error here.
    with get_connection() as connection:
        landed = land_records(connection, table, records)
        logger.info("landed %d %s", landed, table)


def main() -> None:
    args = parse_args()
    client = BalldontlieClient()

    teams = [Team.model_validate(row) for row in client.teams()]
    _fetch_then_land("teams", teams)

    players = [Player.model_validate(row) for row in client.players()]
    _fetch_then_land("players", players)

    games = [Game.model_validate(row) for row in client.games(args.seasons)]
    _fetch_then_land("games", games)


if __name__ == "__main__":
    main()
