"""PostgreSQL SCD2 ingestion and atomic consumer-view publication."""

from importlib.resources import files

from psycopg import sql
from psycopg.types.json import Jsonb

from .contracts import normalize

LOCK_KEY = 72400621


def initialize(conn) -> None:
    with conn.transaction():
        conn.execute(files("peru_macro").joinpath("sql/schema.sql").read_text())


def ingest(conn, batch, start, end, run_id, observed_at) -> dict:
    # Validate all series before a single database write.
    normalized = [
        (entry, normalize(entry["payload"], entry["spec"], start, end, quarantine=True))
        for entry in batch
    ]
    codes = [entry["spec"]["code"] for entry, _ in normalized]
    if len(set(codes)) != len(codes):
        raise ValueError("Duplicate series in batch")
    for _, rows in normalized:
        if sum(row.rejection_reason is not None for row in rows) / len(rows) > 0.01:
            raise ValueError("Quality gate: more than 1% invalid numeric observations in a series")
    stats = {
        "observations": 0,
        "missing_values": 0,
        "new_versions": 0,
        "unchanged": 0,
        "rejected": 0,
    }
    with conn.transaction():
        conn.execute(
            "INSERT INTO macro_control.runs VALUES (%s,'running',%s,%s)",
            (run_id, observed_at, Jsonb({"start": str(start), "end": str(end)})),
        )
        latest = conn.execute(
            "SELECT max(valid_from) FROM macro_raw.observation_history"
        ).fetchone()[0]
        if latest is not None and observed_at <= latest:
            raise ValueError(
                "Observation time must advance monotonically; use Bronze replay with current time"
            )
        for entry, rows in normalized:
            spec = entry["spec"]
            conn.execute(
                """
                INSERT INTO macro_raw.series VALUES (%s,%s,%s,%s,%s)
                ON CONFLICT(code) DO UPDATE SET name=excluded.name, frequency=excluded.frequency,
                    unit=excluded.unit, aggregation=excluded.aggregation
            """,
                (spec["code"], spec["name"], spec["frequency"], spec["unit"], spec["aggregation"]),
            )
            conn.execute(
                "INSERT INTO macro_control.sources VALUES (%s,%s,%s,%s,%s)",
                (run_id, spec["code"], entry["sha"], entry["path"], entry["url"]),
            )
            existing = dict(
                conn.execute(
                    """
                SELECT period,value FROM macro_raw.observation_history
                WHERE code=%s AND valid_to IS NULL AND period BETWEEN %s AND %s
            """,
                    (spec["code"], start, end),
                ).fetchall()
            )
            for row in rows:
                stats["observations"] += 1
                if row.rejection_reason:
                    stats["rejected"] += 1
                    conn.execute(
                        "INSERT INTO macro_control.rejects VALUES (%s,%s,%s,%s,%s)",
                        (run_id, row.code, row.period, row.raw_value, row.rejection_reason),
                    )
                    continue
                stats["missing_values"] += int(row.value is None)
                if row.period in existing and existing[row.period] == row.value:
                    stats["unchanged"] += 1
                    continue
                if row.period in existing:
                    conn.execute(
                        """
                        UPDATE macro_raw.observation_history SET valid_to=%s
                        WHERE code=%s AND period=%s AND valid_to IS NULL
                    """,
                        (observed_at, row.code, row.period),
                    )
                conn.execute(
                    """
                    INSERT INTO macro_raw.observation_history
                    (code,period,value,valid_from,valid_to,run_id) VALUES (%s,%s,%s,%s,NULL,%s)
                """,
                    (row.code, row.period, row.value, observed_at, run_id),
                )
                stats["new_versions"] += 1
        conn.execute(
            "UPDATE macro_control.runs SET status='ingested',details=details||%s WHERE run_id=%s",
            (Jsonb(stats), run_id),
        )
    return stats


def as_of(conn, instant) -> list:
    return conn.execute(
        """
        SELECT code,period,value FROM macro_raw.observation_history
        WHERE valid_from <= %s AND (valid_to IS NULL OR %s < valid_to)
        ORDER BY code,period
    """,
        (instant, instant),
    ).fetchall()


def promote(conn, run_id, build_schema: str) -> None:
    """One atomic pointer swap after dbt successfully built and tested isolated tables."""
    with conn.transaction():
        for name in ("fct_monthly_observations", "mart_macro_dashboard", "mart_revisions"):
            conn.execute(
                sql.SQL("CREATE OR REPLACE VIEW macro_analytics.{} AS SELECT * FROM {}.{}").format(
                    sql.Identifier(name), sql.Identifier(build_schema), sql.Identifier(name)
                )
            )
        conn.execute(
            """
            INSERT INTO macro_control.publications VALUES (TRUE,%s,%s,current_timestamp)
            ON CONFLICT(singleton) DO UPDATE SET run_id=excluded.run_id,
              build_schema=excluded.build_schema,published_at=excluded.published_at
        """,
            (run_id, build_schema),
        )
        conn.execute("UPDATE macro_control.runs SET status='published' WHERE run_id=%s", (run_id,))
