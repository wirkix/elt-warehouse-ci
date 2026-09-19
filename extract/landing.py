"""Lands raw balldontlie records into a Databricks Delta staging schema.

Each record is stored as its full JSON payload in a `payload` STRING column
plus its `id` and an `ingested_at` timestamp -- dbt's staging models parse
the JSON, this layer's only job is a faithful, idempotent raw copy.

Idempotent by design: every run loads into a throwaway `<table>_staging`
table, then MERGEs into the real `<table>` by `id`, so reruns update
existing rows instead of piling up duplicates. (economic-pulse-lakehouse
hit exactly this bug landing straight into a bucket with no overwrite
semantics -- MERGE avoids it here instead of relying on remembering to
clear a prefix.)
"""

from __future__ import annotations

import os
from collections.abc import Iterable
from datetime import UTC, datetime

from databricks import sql
from pydantic import BaseModel


def get_connection():
    catalog = os.environ.get("DATABRICKS_CATALOG", "workspace")
    schema = os.environ.get("DATABRICKS_STAGING_SCHEMA", "nba_staging")
    connection = sql.connect(
        server_hostname=os.environ["DATABRICKS_HOST"],
        http_path=os.environ["DATABRICKS_HTTP_PATH"],
        access_token=os.environ["DATABRICKS_TOKEN"],
        catalog=catalog,
        # Connecting with a schema that doesn't exist yet is fine (session
        # opens either way) but every later unqualified statement resolves
        # against it, so create it eagerly rather than failing on the
        # first CREATE TABLE with SCHEMA_NOT_FOUND.
        schema="default",
        # The legacy Thrift transport 404s against this Free Edition
        # serverless warehouse -- only the newer Statement Execution API
        # (SEA) transport works externally here.
        use_sea=True,
    )
    with connection.cursor() as cursor:
        cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {catalog}.{schema}")
        cursor.execute(f"USE SCHEMA {schema}")
    return connection


def land_records(connection, table: str, records: Iterable[BaseModel]) -> int:
    """Merge `records` into `raw_<table>`, keyed by each record's `id`. Returns row count."""
    raw_table = f"raw_{table}"
    staging_table = f"raw_{table}_staging"
    ingested_at = datetime.now(UTC).isoformat()
    rows = [
        {"id": record.id, "payload": record.model_dump_json(), "ingested_at": ingested_at}
        for record in records
    ]

    with connection.cursor() as cursor:
        cursor.execute(
            f"CREATE TABLE IF NOT EXISTS {raw_table} "
            "(id BIGINT, payload STRING, ingested_at TIMESTAMP) USING DELTA"
        )
        if not rows:
            return 0

        cursor.execute(
            f"CREATE OR REPLACE TABLE {staging_table} "
            "(id BIGINT, payload STRING, ingested_at TIMESTAMP) USING DELTA"
        )
        cursor.executemany(
            f"INSERT INTO {staging_table} (id, payload, ingested_at) "
            "VALUES (%(id)s, %(payload)s, %(ingested_at)s)",
            rows,
        )
        cursor.execute(
            f"MERGE INTO {raw_table} AS target "
            f"USING {staging_table} AS source "
            "ON target.id = source.id "
            "WHEN MATCHED THEN UPDATE SET * "
            "WHEN NOT MATCHED THEN INSERT *"
        )
        cursor.execute(f"DROP TABLE {staging_table}")
    return len(rows)
