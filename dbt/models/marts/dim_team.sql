select
    team_id,
    team_name,
    full_name,
    abbreviation,
    conference,
    division,
    city
from {{ ref('stg_teams') }}
