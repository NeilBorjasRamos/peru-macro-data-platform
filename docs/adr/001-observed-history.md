# ADR 001 — Preserve observed revisions, not inferred official vintages
Status: accepted.

Context: a current BCRP API response may revise an old period but does not provide
the full sequence of original release dates needed for genuine historical vintages.
Decision: SCD2 by code and source period with system valid_from/valid_to. Preserve
current missing markers and source bytes. Query intervals as half-open.
Consequence: replay is idempotent and later corrections are explainable. Initial
historical backfill does not reconstruct what was knowable years earlier. A
research-grade vintage product needs an independent archived-release source.
