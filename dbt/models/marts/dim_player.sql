select
    player_id,
    first_name,
    last_name,
    full_name,
    position,
    height,
    weight,
    college,
    country,
    draft_year,
    draft_round,
    draft_number,
    team_id as current_team_id
from {{ ref('stg_players') }}
