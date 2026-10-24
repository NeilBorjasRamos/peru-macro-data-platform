"""Single-writer orchestration across acquisition, ingestion, dbt and promotion."""

import os
import subprocess
import sys
import uuid
from datetime import UTC, date, datetime
from pathlib import Path

import psycopg
from psycopg.conninfo import conninfo_to_dict
from psycopg.types.json import Jsonb

from .client import acquire
from .contracts import catalog
from .warehouse import LOCK_KEY, ingest, initialize, promote


def build(conn, dsn: str, run_id: str, project: Path) -> str:
    schema = "build_" + uuid.UUID(run_id).hex
    settings = conninfo_to_dict(dsn)
    env = os.environ.copy()
    env.update(
        {
            "PGHOST": settings.get("host", "localhost"),
            "PGPORT": settings.get("port", "5432"),
            "PGUSER": settings.get("user", "macro"),
            "PGPASSWORD": settings.get("password", ""),
            "PGDATABASE": settings.get("dbname", "macro"),
            "DBT_BUILD_SCHEMA": schema,
            "DBT_SEND_ANONYMOUS_USAGE_STATS": "false",
            "PGSSLMODE": settings.get("sslmode", "prefer"),
        }
    )
    # Logs go to stderr; credentials are never printed by this process.
    subprocess.run(
        ["dbt", "build", "--project-dir", str(project), "--profiles-dir", str(project)],
        env=env,
        check=True,
        stdout=sys.stderr,
    )
    promote(conn, run_id, schema)
    return schema


def sync(
    dsn: str,
    root: Path,
    start: date,
    end: date,
    inputs: Path | None = None,
    project: Path | None = None,
    specs: list[dict] | None = None,
    observed_at=None,
    dataset_mode: str = "real",
) -> dict:
    if start > end or start.year < 2000 or end.year > 2099:
        raise ValueError("Require 2000 <= start <= end <= 2099")
    if start.day != 1:
        raise ValueError("Start must be the first day of a month")
    # Monthly periods use month-start; daily periods are filtered by exact end date.
    started_at = datetime.now(UTC)
    if observed_at is not None and observed_at.tzinfo is None:
        raise ValueError("observed_at must be timezone-aware")
    root = root.resolve()
    run_id = str(uuid.uuid4())
    with psycopg.connect(dsn, autocommit=True, prepare_threshold=None) as conn:
        acquired = conn.execute("SELECT pg_try_advisory_lock(%s)", (LOCK_KEY,)).fetchone()[0]
        if not acquired:
            raise RuntimeError("Another pipeline writer holds the PostgreSQL advisory lock")
        try:
            initialize(conn)
            if dataset_mode not in {"real", "synthetic"}:
                raise ValueError("Unknown dataset mode")
            with conn.transaction():
                conn.execute(
                    "INSERT INTO macro_control.environment VALUES (TRUE,%s) ON CONFLICT DO NOTHING",
                    (dataset_mode,),
                )
                mode = conn.execute(
                    "SELECT dataset_mode FROM macro_control.environment"
                ).fetchone()[0]
                if mode != dataset_mode:
                    raise ValueError("Use separate databases for real and synthetic runs")
            batch = acquire(root, specs or catalog(), start, end, inputs)
            observed_at = observed_at or datetime.now(UTC)
            stats = ingest(conn, batch, start, end, run_id, observed_at)
            result = {"run_id": run_id, "status": "ingested", **stats}
            if project:
                result["build_schema"] = build(conn, dsn, run_id, project.resolve())
                result["status"] = "published"
            return result
        except Exception as exc:
            # Ingestion may already be committed. Failed Gold is never promoted.
            safe_error = f"{type(exc).__name__}: pipeline failed; inspect sanitized local logs"
            with conn.transaction():
                conn.execute(
                    """
                    INSERT INTO macro_control.runs VALUES (%s,'failed',%s,%s)
                    ON CONFLICT(run_id) DO UPDATE SET status='failed',details=runs.details||excluded.details
                """,
                    (run_id, observed_at or started_at, Jsonb({"error": safe_error})),
                )
            raise
        finally:
            conn.execute("SELECT pg_advisory_unlock(%s)", (LOCK_KEY,))
