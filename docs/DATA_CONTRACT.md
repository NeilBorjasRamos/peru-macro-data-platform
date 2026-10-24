# Data contract
Catalog: src/peru_macro/catalog.json. Range: 2000–2099; start must be month-start.
One source code is requested per response; exactly one named header series and
one value per period are required. The API header does not include its code:
identity is anchored to the requested URL plus checked-in catalog, not independently
verified against a returned identifier.

Monthly labels: Jan.2024 → 2024-01-01. Daily labels: 02.Jan.24 → 2024-01-02.
English months plus observed Spanish-style aliases are supported. The two-digit
daily year belongs to the project's explicitly limited 2000–2099 domain.
Unknown date labels, duplicate periods, empty/all-missing series, missing columns
or periods outside the requested range fail the batch.

## Values and quality
Finite numeric source text is parsed as Decimal and stored in unrestricted NUMERIC.
Known missing markers (including n.d.) become explicit nulls, never zero.
Malformed numeric values may be quarantined with raw text, code, period and reason.
More than 1% malformed observations in any series blocks the entire ingest.
The threshold is a project policy and currently fixed in warehouse.py.

A rejected update does not overwrite a prior accepted value. Consequently a
consumer can retain an older accepted observation while the new source value is
quarantined; use observed_since and rejected diagnostics to identify staleness.
Schema/date failures are not selectively quarantined.

## Frequency and units
Monthly values remain at monthly grain. Daily reference rates are reduced to the
last non-null observation available within the month, not the average.
Missing daily values and absent weekends are not forward-filled.
Different index bases are not compared directly. Rates expressed as percentages
are not subjected to percentage-growth calculations. policy_minus_inflation_pp
is a descriptive difference in percentage points, not a forecast-adjusted real rate.

## Invariants
Per ingest: received = accepted (including explicit nulls) + rejected.
Accepted rows = unchanged + newly versioned records.
At most one open history version per code/period, enforced by a unique partial index.
No overlapping observed intervals, tested by dbt.
Current-state model count equals open history count, tested by dbt.
Every monthly model key is unique, tested by dbt.
Only successfully built/tested candidate tables can become consumer views.

No release-date column is inferred from period labels. valid_from means this
system observed the value then, not that BCRP first published it at that instant.
