select
    game_id,
    date(game_date) as date_day,
    season,
    status,
    postseason,
    home_team_id,
    visitor_team_id,
    home_team_score,
    visitor_team_score,
    home_team_score - visitor_team_score as home_margin,
    case
        when home_team_score > visitor_team_score then home_team_id
        else visitor_team_id
    end as winning_team_id
from {{ ref('stg_games') }}
where status = 'Final'
