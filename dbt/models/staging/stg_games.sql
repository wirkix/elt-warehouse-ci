select
    cast(get_json_object(payload, '$.id') as bigint) as game_id,
    cast(get_json_object(payload, '$.date') as timestamp) as game_date,
    cast(get_json_object(payload, '$.season') as int) as season,
    get_json_object(payload, '$.status') as status,
    cast(get_json_object(payload, '$.postseason') as boolean) as postseason,
    cast(get_json_object(payload, '$.home_team.id') as bigint) as home_team_id,
    cast(get_json_object(payload, '$.visitor_team.id') as bigint) as visitor_team_id,
    cast(get_json_object(payload, '$.home_team_score') as int) as home_team_score,
    cast(get_json_object(payload, '$.visitor_team_score') as int) as visitor_team_score,
    cast(ingested_at as timestamp) as ingested_at
from {{ source('nba_staging', 'raw_games') }}
