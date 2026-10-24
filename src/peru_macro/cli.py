"""Small orchestration CLI; database credentials are read only from the environment."""

import argparse
import json
import os
from datetime import date, datetime
from pathlib import Path

import psycopg

from .demo import create_demo
from .pipeline import sync
from .warehouse import as_of


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("data"))
    commands = parser.add_subparsers(dest="command", required=True)
    load = commands.add_parser("sync")
    load.add_argument("--start", type=date.fromisoformat, required=True)
    load.add_argument("--end", type=date.fromisoformat, required=True)
    load.add_argument("--inputs", type=Path)
    load.add_argument("--dbt-project", type=Path, default=Path("dbt"))
    load.add_argument("--ingest-only", action="store_true")
    demo = commands.add_parser("demo")
    demo.add_argument("--revised", action="store_true")
    demo.add_argument("--dbt-project", type=Path, default=Path("dbt"))
    point = commands.add_parser("as-of")
    point.add_argument("--at", type=datetime.fromisoformat, required=True)
    commands.add_parser("status")
    args = parser.parse_args()
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        parser.error("DATABASE_URL must be set; see .env.example")
    try:
        if args.command in {"sync", "demo"}:
            if args.command == "demo":
                inputs = args.root / "synthetic_inputs"
                create_demo(inputs, args.revised)
                result = sync(
                    dsn,
                    args.root,
                    date(2024, 1, 1),
                    date(2024, 2, 29),
                    inputs,
                    args.dbt_project,
                    dataset_mode="synthetic",
                )
                result["dataset"] = "synthetic"
            else:
                result = sync(
                    dsn,
                    args.root,
                    args.start,
                    args.end,
                    args.inputs,
                    None if args.ingest_only else args.dbt_project,
                )
        else:
            with psycopg.connect(dsn) as conn:
                if args.command == "as-of":
                    if args.at.tzinfo is None:
                        raise ValueError("as-of instant must include timezone")
                    result = {"observations": as_of(conn, args.at)}
                else:
                    result = {
                        "runs": conn.execute("""
                        SELECT run_id,status,observed_at,details FROM macro_control.runs
                        ORDER BY observed_at DESC LIMIT 10
                    """).fetchall()
                    }
        print(json.dumps(result, default=str))
    except Exception as exc:
        # psycopg connection errors can include endpoints; don't echo a DSN.
        print(
            json.dumps(
                {
                    "status": "failed",
                    "error_type": type(exc).__name__,
                    "message": "Pipeline failed; inspect sanitized logs and macro_control.runs",
                }
            )
        )
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
