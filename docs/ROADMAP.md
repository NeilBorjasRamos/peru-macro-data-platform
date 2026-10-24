# Next improvements
These are not implemented:
1. Production-like load and contention testing beyond the two-writer regression.
2. Catalog metadata versioning and schema migration/rollback tooling.
3. Source availability/freshness checks relative to each series release calendar.
4. Scheduled overlap refresh, full-range backfills and alert delivery.
5. Safe inactive-candidate garbage collection and restore automation.
6. Dagster orchestration if operational needs exceed the current CLI + dbt DAG.
7. A read-only dashboard or API with authentication and query limits.
8. Cloud IaC, restricted database roles, TLS, secret management and measured costs.

Completed after publishing: all 45 Python tests and the dbt demo passed against
PostgreSQL 16.6, including advisory-lock and failed-promotion regression tests.
[Validation evidence](VALIDATION.md). Next priority: a restore drill and bounded
retention of inactive build schemas.
