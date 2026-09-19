select
    cast(get_json_object(payload, '$.id') as bigint) as player_id,
    get_json_object(payload, '$.first_name') as first_name,
    get_json_object(payload, '$.last_name') as last_name,
    concat(get_json_object(payload, '$.first_name'), ' ', get_json_object(payload, '$.last_name')) as full_name,
    get_json_object(payload, '$.position') as position,
    get_json_object(payload, '$.height') as height,
    get_json_object(payload, '$.weight') as weight,
    get_json_object(payload, '$.college') as college,
    get_json_object(payload, '$.country') as country,
    cast(get_json_object(payload, '$.draft_year') as int) as draft_year,
    cast(get_json_object(payload, '$.draft_round') as int) as draft_round,
    cast(get_json_object(payload, '$.draft_number') as int) as draft_number,
    cast(get_json_object(payload, '$.team.id') as bigint) as team_id,
    cast(ingested_at as timestamp) as ingested_at
from {{ source('nba_staging', 'raw_players') }}
