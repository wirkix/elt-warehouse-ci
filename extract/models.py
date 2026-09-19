"""Pydantic models for balldontlie's raw API payloads.

These validate shape at extract time (fail fast on an API contract change)
but are deliberately permissive on nested/optional fields -- dbt's staging
layer, not this layer, is the source of truth for typed/cleaned columns.
"""

from __future__ import annotations

from pydantic import BaseModel


class Team(BaseModel):
    id: int
    conference: str | None = None
    division: str | None = None
    city: str | None = None
    name: str
    full_name: str
    abbreviation: str


class Player(BaseModel):
    id: int
    first_name: str
    last_name: str
    position: str | None = None
    height: str | None = None
    weight: str | None = None
    jersey_number: str | None = None
    college: str | None = None
    country: str | None = None
    draft_year: int | None = None
    draft_round: int | None = None
    draft_number: int | None = None
    team: Team | None = None


class Game(BaseModel):
    id: int
    date: str
    season: int
    status: str
    period: int | None = None
    time: str | None = None
    postseason: bool
    home_team_score: int
    visitor_team_score: int
    home_team: Team
    visitor_team: Team
