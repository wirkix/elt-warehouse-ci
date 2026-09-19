{#
    dbt's default behavior concatenates the target schema with a model's
    custom `+schema` config (e.g. target "nba" + custom "nba_staging" ->
    "nba_nba_staging"). Every model here sets its own explicit +schema
    (nba_staging / nba_marts per dbt_project.yml), so use that name as-is.
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
