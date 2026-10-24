import os

import psycopg
import pytest

from peru_macro.warehouse import initialize


@pytest.fixture
def db():
    dsn = os.environ.get("TEST_DATABASE_URL")
    if not dsn:
        pytest.skip(
            "Set TEST_DATABASE_URL to a disposable PostgreSQL database for integration tests"
        )
    with psycopg.connect(dsn, autocommit=True, prepare_threshold=None) as conn:
        # Explicit opt-in test DB; never point this to a production database.
        conn.execute("DROP SCHEMA IF EXISTS macro_analytics CASCADE")
        conn.execute("DROP SCHEMA IF EXISTS macro_raw CASCADE")
        conn.execute("DROP SCHEMA IF EXISTS macro_control CASCADE")
        initialize(conn)
        yield conn
