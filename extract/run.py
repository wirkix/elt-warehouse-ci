"""Entrypoint: pulls teams/players/games/stats from balldontlie and lands
them in the Databricks staging schema.

    python -m extract.run --seasons 2024 2025

Season numbers are the year a season *starts* in (balldontlie convention),
e.g. `2025` is the 2025-26 season.
"""

from __future__ import annotations

import argparse
import logging

from extract.client import BalldontlieClient
from extract.landing import get_connection, land_records
from extract.models import Game, Player, Stat, Team

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seasons", type=int, nargs="+", required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    client = BalldontlieClient()
    connection = get_connection()

    try:
        teams = [Team.model_validate(row) for row in client.teams()]
        landed = land_records(connection, "teams", teams)
        logger.info("landed %d teams", landed)

        players = [Player.model_validate(row) for row in client.players()]
        landed = land_records(connection, "players", players)
        logger.info("landed %d players", landed)

        games = [Game.model_validate(row) for row in client.games(args.seasons)]
        landed = land_records(connection, "games", games)
        logger.info("landed %d games", landed)

        stats = [Stat.model_validate(row) for row in client.stats(args.seasons)]
        landed = land_records(connection, "stats", stats)
        logger.info("landed %d stats rows", landed)
    finally:
        connection.close()


if __name__ == "__main__":
    main()
