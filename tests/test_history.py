from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

import psycopg
import pytest

from peru_macro.contracts import catalog
from peru_macro.warehouse import as_of, ingest, promote

pytestmark = pytest.mark.integration
START, END = date(2024, 1, 1), date(2024, 2, 29)
NOW = datetime(2026, 1, 1, tzinfo=UTC)


def batch(value="100"):
    return [
        {
            "spec": catalog()[0],
            "sha": "test",
            "path": "synthetic.json",
            "url": "synthetic",
            "payload": {
                "config": {"series": [{"name": "SYNTHETIC"}]},
                "periods": [{"name": "Jan.2024", "values": [value]}],
            },
        }
    ]


def load(db, value="100", day=0):
    return ingest(db, batch(value), START, END, str(uuid4()), NOW + timedelta(days=day))


def test_replay_retains_single_version(db):
    assert load(db)["new_versions"] == 1
    assert load(db, "100.0", 1)["unchanged"] == 1
    assert db.execute("SELECT count(*) FROM macro_raw.observation_history").fetchone()[0] == 1


def test_revision_and_asof(db):
    load(db)
    load(db, "101", 1)
    assert as_of(db, NOW)[0][2] == Decimal("100")
    assert as_of(db, NOW + timedelta(days=1))[0][2] == Decimal("101")
    assert (
        db.execute(
            "SELECT count(*) FROM macro_raw.observation_history WHERE valid_to IS NULL"
        ).fetchone()[0]
        == 1
    )


def test_explicit_missing_is_revision(db):
    load(db)
    rows = batch("n.d.")
    rows[0]["payload"]["periods"].append({"name": "Feb.2024", "values": ["1"]})
    ingest(db, rows, START, END, str(uuid4()), NOW + timedelta(days=1))
    assert as_of(db, NOW + timedelta(days=1))[0][2] is None


def test_failed_contract_does_not_change_history(db):
    load(db)
    with pytest.raises(ValueError):
        load(db, "invalid", 1)
    assert as_of(db, NOW + timedelta(days=2))[0][2] == Decimal("100")


def test_nonmonotonic_ingest_rolls_back_run(db):
    load(db)
    with pytest.raises(ValueError, match="monotonically"):
        load(db, "101", 0)
    assert db.execute("SELECT count(*) FROM macro_control.runs").fetchone()[0] == 1


def test_promotion_failure_keeps_previous_consumer_view(db):
    runid = str(uuid4())
    ingest(db, batch(), START, END, runid, NOW)
    db.execute("CREATE SCHEMA good_build")
    for name in ("fct_monthly_observations", "mart_macro_dashboard", "mart_revisions"):
        db.execute(f"CREATE TABLE good_build.{name} AS SELECT 1 AS value")
    promote(db, runid, "good_build")
    with pytest.raises(psycopg.errors.UndefinedTable):
        promote(db, runid, "nonexistent_build")
    assert db.execute("SELECT value FROM macro_analytics.mart_macro_dashboard").fetchone()[0] == 1
    db.execute("DROP SCHEMA good_build CASCADE")


def test_sync_audits_failed_model_build(db, tmp_path, monkeypatch):
    import os

    from peru_macro.pipeline import sync

    monkeypatch.setattr("peru_macro.pipeline.acquire", lambda *a, **kw: batch())

    def failed_build(*args):
        raise RuntimeError("injected dbt test failure")

    monkeypatch.setattr("peru_macro.pipeline.build", failed_build)
    with pytest.raises(RuntimeError, match="injected"):
        sync(os.environ["TEST_DATABASE_URL"], tmp_path, START, END, project=tmp_path)
    assert db.execute("SELECT status FROM macro_control.runs").fetchone()[0] == "failed"
    assert db.execute("SELECT count(*) FROM macro_raw.observation_history").fetchone()[0] == 1
    assert db.execute("SELECT count(*) FROM macro_control.publications").fetchone()[0] == 0


def test_postgres_rejects_second_writer(db):
    import os

    from peru_macro.warehouse import LOCK_KEY

    if os.environ.get("VALIDATION_PGLITE"):
        pytest.skip("PGlite multiplexing does not prove PostgreSQL multi-session locking")
    assert db.execute("SELECT pg_try_advisory_lock(%s)", (LOCK_KEY,)).fetchone()[0]
    try:
        with psycopg.connect(os.environ["TEST_DATABASE_URL"], autocommit=True) as other:
            assert not other.execute("SELECT pg_try_advisory_lock(%s)", (LOCK_KEY,)).fetchone()[0]
    finally:
        db.execute("SELECT pg_advisory_unlock(%s)", (LOCK_KEY,))


def test_real_and_synthetic_modes_cannot_mix(db, tmp_path, monkeypatch):
    import os

    from peru_macro.pipeline import sync

    monkeypatch.setattr("peru_macro.pipeline.acquire", lambda *a, **kw: batch())
    sync(os.environ["TEST_DATABASE_URL"], tmp_path, START, END, dataset_mode="synthetic")
    with pytest.raises(ValueError, match="separate databases"):
        sync(os.environ["TEST_DATABASE_URL"], tmp_path, START, END, dataset_mode="real")
