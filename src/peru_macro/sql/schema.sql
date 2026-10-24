CREATE SCHEMA IF NOT EXISTS macro_raw;
CREATE SCHEMA IF NOT EXISTS macro_control;
CREATE SCHEMA IF NOT EXISTS macro_analytics;

CREATE TABLE IF NOT EXISTS macro_control.schema_version (
    version INTEGER PRIMARY KEY CHECK (version = 1)
);
INSERT INTO macro_control.schema_version VALUES (1) ON CONFLICT DO NOTHING;

CREATE TABLE IF NOT EXISTS macro_raw.series (
    code TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    frequency TEXT NOT NULL CHECK (frequency IN ('M','D')),
    unit TEXT NOT NULL,
    aggregation TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS macro_control.runs (
    run_id UUID PRIMARY KEY,
    status TEXT NOT NULL CHECK(status IN ('running','ingested','published','failed')),
    observed_at TIMESTAMPTZ NOT NULL,
    details JSONB NOT NULL
);
CREATE TABLE IF NOT EXISTS macro_control.sources (
    run_id UUID REFERENCES macro_control.runs(run_id),
    code TEXT REFERENCES macro_raw.series(code),
    sha256 TEXT NOT NULL,
    bronze_path TEXT NOT NULL,
    source_url TEXT NOT NULL,
    PRIMARY KEY(run_id,code)
);
CREATE TABLE IF NOT EXISTS macro_raw.observation_history (
    code TEXT NOT NULL REFERENCES macro_raw.series(code),
    period DATE NOT NULL,
    value NUMERIC,
    valid_from TIMESTAMPTZ NOT NULL,
    valid_to TIMESTAMPTZ,
    run_id UUID NOT NULL REFERENCES macro_control.runs(run_id),
    PRIMARY KEY(code,period,valid_from),
    CHECK(valid_to IS NULL OR valid_to > valid_from)
);
CREATE UNIQUE INDEX IF NOT EXISTS one_current_observation
ON macro_raw.observation_history(code,period) WHERE valid_to IS NULL;
CREATE INDEX IF NOT EXISTS observation_history_lookup
ON macro_raw.observation_history(code,period,valid_from,valid_to);
CREATE TABLE IF NOT EXISTS macro_control.publications (
    singleton BOOLEAN PRIMARY KEY DEFAULT TRUE CHECK(singleton),
    run_id UUID NOT NULL REFERENCES macro_control.runs(run_id),
    build_schema TEXT NOT NULL,
    published_at TIMESTAMPTZ NOT NULL
);
CREATE TABLE IF NOT EXISTS macro_control.environment (
    singleton BOOLEAN PRIMARY KEY DEFAULT TRUE CHECK(singleton),
    dataset_mode TEXT NOT NULL CHECK(dataset_mode IN ('real','synthetic'))
);
CREATE TABLE IF NOT EXISTS macro_control.rejects (
    run_id UUID REFERENCES macro_control.runs(run_id),
    code TEXT NOT NULL,
    period DATE NOT NULL,
    raw_value TEXT NOT NULL,
    reason TEXT NOT NULL,
    PRIMARY KEY(run_id,code,period)
);
