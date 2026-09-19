select
    cast(get_json_object(payload, '$.id') as bigint) as team_id,
    get_json_object(payload, '$.conference') as conference,
    get_json_object(payload, '$.division') as division,
    get_json_object(payload, '$.city') as city,
    get_json_object(payload, '$.name') as team_name,
    get_json_object(payload, '$.full_name') as full_name,
    get_json_object(payload, '$.abbreviation') as abbreviation,
    cast(ingested_at as timestamp) as ingested_at
from {{ source('nba_staging', 'raw_teams') }}
