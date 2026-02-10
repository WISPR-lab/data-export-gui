CREATE TABLE IF NOT EXISTS upload (
    id TEXT PRIMARY KEY, 
    given_name TEXT,         
    platform TEXT,           
    upload_timestamp REAL
);

CREATE TABLE IF NOT EXISTS uploaded_files (
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


CREATE TABLE IF NOT EXISTS raw_data (
    id INTEGER PRIMARY KEY,
    upload_id TEXT,
    file_id TEXT,             
    data JSON,
    FOREIGN KEY(upload_id) REFERENCES upload(id) ON DELETE CASCADE,
    FOREIGN KEY(file_id) REFERENCES uploaded_files(id) ON DELETE CASCADE
);



CREATE TABLE IF NOT EXISTS events_initial (
    id INTEGER PRIMARY KEY,
    upload_id TEXT,
    file_id TEXT,
    raw_data_id TEXT,  
    --             
    timestamp REAL,
    event_action TEXT,
    event_kind TEXT,
    --
    message TEXT,
    attributes JSON,
    is_duplicate_of INTEGER DEFAULT -1,  -- -1 = not a duplicate, otherwise stores the id of the original event
    --
    FOREIGN KEY(upload_id) REFERENCES upload(id) ON DELETE CASCADE,
    FOREIGN KEY(file_id) REFERENCES uploaded_files(id) ON DELETE CASCADE,
    FOREIGN KEY(raw_data_id) REFERENCES raw_data(id) ON DELETE CASCADE
);


CREATE TABLE IF NOT EXISTS auth_devices_initial (
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