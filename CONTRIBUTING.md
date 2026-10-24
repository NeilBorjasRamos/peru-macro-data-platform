# Contributing
Use Python 3.12 and uv 0.13.4. Run uv sync --frozen --extra dev, then:
```bash
uv run --frozen ruff check src tests scripts
uv run --frozen ruff format --check src tests scripts
uv run --frozen pytest -q
DBT_SEND_ANONYMOUS_USAGE_STATS=false uv run --frozen dbt parse --project-dir dbt --profiles-dir dbt
```
Integration tests require TEST_DATABASE_URL pointing to a disposable database.
They DROP project schemas: never point this variable at a production database.
Without it, database tests explicitly skip. CI provisions its own PostgreSQL 16.

Use focused PRs and explain acceptance evidence. Update uv.lock with pyproject.toml.
Do not use a simple numeric fill for missing values or infer original publication
dates from current API responses. Any change to history grain or serving view
columns needs an explicit migration and rollback plan.
