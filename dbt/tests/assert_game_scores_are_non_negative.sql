{#
    Custom singular test: a failure here means the extract/landing layer
    (or balldontlie itself) produced a nonsensical score -- fails the
    build rather than silently shipping bad data downstream.
#}
select game_id, home_team_score, visitor_team_score
from {{ ref('fact_game') }}
where home_team_score < 0 or visitor_team_score < 0
