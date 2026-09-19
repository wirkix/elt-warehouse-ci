{#
    Hand-rolled date spine (no dbt_utils dependency, matching this
    portfolio's other dbt projects) spanning every date a game was
    actually played, via Databricks SQL's native sequence()/explode().
#}
with bounds as (
    select
        min(date(game_date)) as min_date,
        max(date(game_date)) as max_date
    from {{ ref('stg_games') }}
),

spine as (
    select explode(sequence(min_date, max_date, interval 1 day)) as date_day
    from bounds
)

select
    date_day,
    year(date_day) as year,
    month(date_day) as month,
    day(date_day) as day_of_month,
    dayofweek(date_day) as day_of_week,
    date_format(date_day, 'EEEE') as day_name,
    date_format(date_day, 'MMMM') as month_name
from spine
