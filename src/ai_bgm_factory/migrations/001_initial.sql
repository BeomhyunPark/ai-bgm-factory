CREATE TABLE runs (
    run_id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    config_hash TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    manifest_json TEXT NOT NULL
);
CREATE TABLE stages (
    run_id TEXT NOT NULL REFERENCES runs(run_id),
    name TEXT NOT NULL,
    attempt INTEGER NOT NULL,
    status TEXT NOT NULL,
    input_hash TEXT NOT NULL,
    duration_ms REAL,
    PRIMARY KEY (run_id, name)
);
CREATE TABLE artifacts (
    run_id TEXT NOT NULL REFERENCES runs(run_id),
    path TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    bytes INTEGER NOT NULL,
    PRIMARY KEY (run_id, path)
);
