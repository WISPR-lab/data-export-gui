CREATE TABLE IF NOT EXISTS raw_events (
    id INTEGER PRIMARY KEY,
    source_file TEXT,
    adapter_type TEXT,
    raw_data JSON
);
