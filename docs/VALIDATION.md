# Validation evidence
Date: 24 October 2026. Python 3.12.14, dbt Core 1.9.8, dbt-postgres 1.9.1.

## Real BCRP capture
Eight source series, 2005-01-01 through 2025-12-31:
- 7,242 received observations.
- 7,241 accepted current keys, including 106 explicit missing values.
- One malformed daily numeric observation quarantined, without repair.
- 252 monthly panel rows and 2,016 series-month records.
- Identical snapshot replay: 7,241 unchanged, zero new versions.
- Four dbt table models and twelve dbt data tests completed successfully.
- Machine-readable evidence: validation.json.
- Source-backed figure: assets/peru-macro-2005-2025.png.

The captured daily API response used the label 14.Set.17 and included one value
containing concatenated text rather than a standalone number. The parser explicitly
supports the month alias; the malformed value is quarantined.

## Python checks
44 tests passed, one skipped, 87% statement coverage in the local validation run.
The skipped test checks two independent PostgreSQL advisory-lock sessions.
Ruff lint and formatting, dbt parse with telemetry disabled and package build
are part of the validation sequence.

## Engine scope
This environment cannot run a normal PostgreSQL server with its required non-root
OS identity. SQL integration and real dbt builds were therefore validated with
PGlite 0.5.11 (PostgreSQL 18.6 compiled to WASM) over the PostgreSQL wire protocol.
That validates the exercised SQL, not full PostgreSQL 16 compatibility, multi-session
locking, production concurrency or performance.

The included CI provisions real PostgreSQL 16.6 and runs the lock test. That CI has
not run yet for this new project. Docker/Compose, Windows/macOS and Python 3.11/3.13
have not been executed here. No throughput benchmark or cloud deployment is claimed.
