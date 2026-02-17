CREATE TABLE IF NOT EXISTS upload (
    id TEXT PRIMARY KEY, 
    given_name TEXT,         
    platform TEXT,           
    upload_timestamp REAL,
    color TEXT,
);

CREATE TABLE IF NOT EXISTS uploaded_files ( -- filled during extraction step   
    id TEXT PRIMARY KEY, 
    manifest_file_id TEXT,
    upload_id TEXT, 
    opfs_filename TEXT,                
    manifest_filename TEXT,        
    file_hash TEXT,               
    upload_timestamp REAL,        
    file_size_bytes INTEGER,
    parse_status TEXT,
    FOREIGN KEY(upload_id) REFERENCES upload(id) ON DELETE CASCADE
);


CREATE TABLE IF NOT EXISTS raw_data ( -- filled during extraction step
    id INTEGER PRIMARY KEY,
    upload_id TEXT,
    file_id TEXT,             
    data JSON,
    FOREIGN KEY(upload_id) REFERENCES upload(id) ON DELETE CASCADE,
    FOREIGN KEY(file_id) REFERENCES uploaded_files(id) ON DELETE CASCADE
);



CREATE TABLE IF NOT EXISTS events ( -- filled during semantic map
    id INTEGER PRIMARY KEY,
    upload_id TEXT,
    file_ids JSON,  -- multiple possible after deduplication
    raw_data_ids JSON,  -- can be multiple raw data entries that map to the same event, stored as JSON list of raw_data ids
    --             
    timestamp REAL,
    event_action TEXT,
    event_kind TEXT,
    --
    message TEXT,
    attributes JSON,    --
    tags JSON DEFAULT "[]",
    labels JSON DEFAULT "[]",
    --
    deduplicated BOOLEAN DEFAULT 0,
    extra_timestamps JSON DEFAULT "[]"
    --
    FOREIGN KEY(upload_id) REFERENCES upload(id) ON DELETE CASCADE,
    -- FOREIGN KEY(file_id) REFERENCES uploaded_files(id) ON DELETE CASCADE,
    -- FOREIGN KEY(raw_data_id) REFERENCES raw_data(id) ON DELETE CASCADE
);



CREATE TABLE IF NOT EXISTS event_comments (
    id INTEGER PRIMARY KEY,
    event_id INTEGER,
    comment TEXT,
    created_at REAL,
    updated_at REAL,
    FOREIGN KEY(event_id) REFERENCES events_initial(id) ON DELETE CASCADE
);



CREATE TABLE IF NOT EXISTS auth_devices_initial ( -- filled during semantic map
    id INTEGER PRIMARY KEY,
    upload_id TEXT,
    file_id TEXT,
    raw_data_id TEXT,
    --
    entity_type TEXT,
    event_kind TEXT,
    --
    attributes JSON,     
    --        
    FOREIGN KEY(upload_id) REFERENCES upload(id) ON DELETE CASCADE,
    FOREIGN KEY(file_id) REFERENCES uploaded_files(id) ON DELETE CASCADE,
    FOREIGN KEY(raw_data_id) REFERENCES raw_data(id) ON DELETE CASCADE
);


---------------------------------