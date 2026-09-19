import json
from pathlib import Path

from extract.models import Game, Player, Team

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str) -> list[dict]:
    return json.loads((FIXTURES / name).read_text())["data"]


def test_team_validates():
    teams = [Team.model_validate(row) for row in load("teams_page.json")]
    assert teams[0].abbreviation == "BOS"
    assert teams[1].full_name == "Los Angeles Lakers"


def test_player_validates():
    players = [Player.model_validate(row) for row in load("players_page.json")]
    assert players[0].last_name == "James"
    assert players[0].team.abbreviation == "LAL"


def test_game_validates():
    games = [Game.model_validate(row) for row in load("games_page.json")]
    assert games[0].home_team_score == 118
    assert games[0].postseason is False
