# ADR 002 — Test candidate tables before consumer promotion
Status: accepted.

Context: dbt builds models across separate transactions. Running it directly in
a serving schema can expose partly updated analytics before all tests finish.
Decision: per-run candidate schema, table materializations and dbt build; only
after success replace stable consumer views inside one PostgreSQL transaction.
Consequence: consumers retain the previous snapshot on failure, while raw history
can independently advance. Storage grows with retained builds. Column-type changes
may block CREATE OR REPLACE VIEW and require a reviewed migration.
