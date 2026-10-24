# Operations and recovery
## Daily workflow
Use a trusted PostgreSQL database and DATABASE_URL. Run from the repository root.
macro sync --start YYYY-MM-01 --end YYYY-MM-DD captures and publishes a source range.
macro sync ... --ingest-only persists history without running dbt.
macro status returns recent run summaries.
macro as-of --at ISO_TIMESTAMP_WITH_TIMEZONE queries observed history.

## Refresh versus backfill
Incremental state is handled at the observation key: only changed values create
versions. Source acquisition is range-based rather than watermark-only because
older observations may be revised. A practical scheduled design should refresh
the latest 24 months and periodically run the full agreed historical range.
There is no scheduler installed in this release, and no claim that revisions
outside a chosen lookback are automatically discovered.

## Failures
| Signal | Recovery |
|---|---|
| 404/403 | Verify official code and availability; do not bypass restrictions |
| 429/5xx | Bounded retries; wait and rerun if exhausted |
| Unknown date/schema | Inspect captured Bronze and update reviewed contract/tests |
| All missing or quality gate | Inspect source range and raw values; do not force zero fills |
| Advisory lock busy | Wait for the owning run; investigate its session if abandoned |
| Failed dbt build/test | Keep existing views, repair models, rerun same inputs |
| Failed view replacement | Transaction rolls back the pointer; review column compatibility |
| Real/synthetic mismatch | Use another database/Compose project, never mix modes |
| Disk growth | Review obsolete build schemas and raw retention before cleanup |

The history transaction can commit even if dbt later fails. status failed therefore
does not mean history was undone. The previous analytical publication remains
valid. Rerun creates zero new versions for unchanged accepted input, but a fresh
candidate build and an audit record are still produced.

Credentials come from DATABASE_URL and are never intentionally printed. dbt logs
remain local runtime files; review/redact them before sharing. Telemetry is disabled
for orchestrated dbt and CI; use DBT_SEND_ANONYMOUS_USAGE_STATS=false for direct commands.

## Retention and backup
Each successful build has its own schema. Do not drop the schema referenced by
macro_control.publications. Retain at least the active and last known good schemas.
Automated schema garbage collection is not implemented.
Back up PostgreSQL with an appropriate pg_dump/restore workflow and Bronze together.
Test restoration into a separate database; do not point integration tests at a backup
you need to keep. Tests intentionally drop project schemas in TEST_DATABASE_URL.
Source raw files and .env are not repository contents.

## Deployment limits
Compose binds the database to localhost only. Example credentials are for disposable
development, not remote deployment. No TLS deployment, authorization roles, external
secret manager, alerting service or production availability guarantee is configured.
Schema version 1 is initialization, not a full migration framework.
