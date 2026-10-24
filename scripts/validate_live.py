"""Reproduce local integration evidence against DATABASE_URL (disposable database only)."""

import json
import os
import shutil
from datetime import date
from pathlib import Path

import psycopg

from peru_macro.client import acquire
from peru_macro.contracts import catalog
from peru_macro.pipeline import sync

dsn = os.environ["DATABASE_URL"]
inputs = Path("data/real_inputs")
if not inputs.exists():
    entries = acquire(Path("data"), catalog(), date(2005, 1, 1), date(2025, 12, 31))
    inputs.mkdir(parents=True)
    for entry in entries:
        shutil.copyfile(Path("data") / entry["path"], inputs / (entry["spec"]["code"] + ".json"))
result = sync(
    dsn, Path("data"), date(2005, 1, 1), date(2025, 12, 31), Path("data/real_inputs"), Path("dbt")
)
replay = sync(
    dsn, Path("data"), date(2005, 1, 1), date(2025, 12, 31), Path("data/real_inputs"), Path("dbt")
)
with psycopg.connect(dsn) as conn:
    rows = conn.execute("""
      select s.code,s.frequency,s.unit,count(*),count(*) filter(where h.value is null)
      from macro_raw.observation_history h join macro_raw.series s using(code)
      where h.valid_to is null group by 1,2,3 order by 1
    """).fetchall()
    months = conn.execute("select count(*) from macro_analytics.mart_macro_dashboard").fetchone()[0]
    version = conn.execute("select version()").fetchone()[0]
    latest = conn.execute("""
      select month,inflation_yoy_pct,exchange_pen_usd,policy_rate_eom_pct
      from macro_analytics.mart_macro_dashboard order by month desc limit 1
    """).fetchone()
evidence = {
    "dataset": "BCRP API, eight verified series",
    "start": "2005-01-01",
    "end": "2025-12-31",
    "first_load": result,
    "replay": replay,
    "monthly_panel_rows": months,
    "series": [
        dict(zip(["code", "frequency", "unit", "rows", "missing"], r, strict=True)) for r in rows
    ],
    "engine": version,
    "latest_month_sample": latest,
    "validation_engine_note": "PGlite/WASM; full PostgreSQL 16 multi-session concurrency is configured for CI, not proven by this local run.",
}
assert replay["new_versions"] == 0
Path("docs/validation.json").write_text(json.dumps(evidence, default=str, indent=2) + "\n")
print(json.dumps(evidence, default=str, indent=2))
