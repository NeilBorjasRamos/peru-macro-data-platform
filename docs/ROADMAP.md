# Next improvements
These are not implemented:
1. A PostgreSQL 16 run in the target environment proving the advisory-lock test.
2. Catalog metadata versioning and schema migration/rollback tooling.
3. Source availability/freshness checks relative to each series release calendar.
4. Scheduled overlap refresh, full-range backfills and alert delivery.
5. Safe inactive-candidate garbage collection and restore automation.
6. Dagster orchestration if operational needs exceed the current CLI + dbt DAG.
7. A read-only dashboard or API with authentication and query limits.
8. Cloud IaC, restricted database roles, TLS, secret management and measured costs.

First priority after publishing: run the included CI, then demonstrate a controlled
revision and a failed candidate promotion in PostgreSQL 16.
