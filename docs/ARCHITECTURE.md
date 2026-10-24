# Architecture and consistency
## Storage
- Filesystem Bronze: source code / SHA-256 JSON, exact HTTP bytes.
- macro_raw.series: current checked-in catalog.
- macro_raw.observation_history: accepted values and explicit nulls, SCD2 by observation time.
- macro_control.runs/sources/rejects: execution, provenance and rejected raw values.
- build_UUID: immutable candidate tables built by dbt.
- macro_analytics: stable consumer views and atomic publication pointer.

## Lifecycle
The PostgreSQL session advisory lock spans source capture, history ingest, dbt
subprocess and view promotion. It is a coordinator protocol; an independent
writer that ignores it is outside the safety boundary.
1. Acquire lock and initialize schema version 1.
2. Enforce real/synthetic database isolation.
3. Capture all requested series into Bronze.
4. Validate every series before writing any observations.
5. In one transaction, add run/source records, close changed versions and insert new ones.
6. Commit ingestion, set status ingested.
7. Run dbt build in build_UUID, materializing four tables and executing 12 tests.
8. Atomically replace the three consumer views and publication pointer; set published.
9. On failure, audit failed; retain previous consumer publication and release lock.

The ingestion and promotion transactions are separate. A dbt failure does not
roll back accepted history. A process crash may leave a run marked running or
ingested; inspect tables and rerun. No asynchronous distributed transaction is claimed.

## Temporal grain
Business key: code + source period. System version key: code + period + valid_from.
Valid interval is [valid_from, valid_to), with null valid_to for current.
Two numeric strings 100 and 100.0 compare as the same Decimal value.
A changed accepted value closes its previous interval; a missing marker is an
explicit null revision. Absent periods and rejected updates do not delete accepted
history. Source observations must be loaded using a current observation time;
backfill changes the requested source range, not the system clock.

The catalog metadata is current-state, not historically versioned. Changes to
units or index bases require reviewed migrations; changing a label does not
retrospectively produce an official data vintage.

## Model semantics
stg_current_observations: exact accepted current-state snapshot, including nulls.
fct_monthly_observations: one series-month; daily rates use the last available
non-null observation inside that month. No cross-month forward filling.
mart_macro_dashboard: pivot with original units; GDP YoY joins the exact prior-year
month rather than lagging twelve available rows across possible gaps.
mart_revisions: versions observed since this system started.

All dbt models are tables in the candidate schema. Serving views never reference
live raw views, so later ingestion cannot leak into an old published snapshot.

## Trust and resource boundaries
One series per HTTP request avoids silently mismatching positional multi-series
results. Responses use explicit language ing but the daily September alias Set
was observed and is supported. Responses are capped at 20 MiB, three attempts,
and connect/read timeouts; there is no overall end-to-end download deadline.
Decimal values use PostgreSQL NUMERIC without truncating the source precision.
Automatic psycopg prepared statements are disabled for portability through session
proxies; connection pooling is not implemented.

PostgreSQL 16 is the deployment target in Compose and CI. Local PGlite evidence
proves SQL behavior only within its documented multiplexing limitations.
