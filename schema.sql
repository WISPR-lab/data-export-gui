CREATE TABLE IF NOT EXISTS uploads (
    id TEXT PRIMARY KEY, 
    given_name TEXT,         
    platform TEXT,           
    upload_timestamp REAL,
    updated_at REAL,
    color TEXT
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
    FOREIGN KEY(upload_id) REFERENCES uploads(id) ON DELETE CASCADE
);


CREATE TABLE IF NOT EXISTS raw_data ( -- filled during extraction step
    id TEXT PRIMARY KEY,
    upload_id TEXT,
    file_id TEXT,             
    data JSONTEXT,
    FOREIGN KEY(upload_id) REFERENCES uploads(id) ON DELETE CASCADE,
    FOREIGN KEY(file_id) REFERENCES uploaded_files(id) ON DELETE CASCADE
);



CREATE TABLE IF NOT EXISTS events ( -- filled during semantic map
    id TEXT PRIMARY KEY,
    upload_id TEXT,
    file_ids JSONTEXT,  -- multiple possible after deduplication
    raw_data_ids JSONTEXT,  -- can be multiple raw data entries that map to the same event, stored as JSON list of raw_data ids
    --             
    timestamp REAL,
    event_action TEXT,
    event_kind TEXT,
    event_category JSONTEXT DEFAULT '[]',
    --
    message TEXT,
    attributes JSONTEXT,    --
    tags JSONTEXT DEFAULT "[]",
    labels JSONTEXT DEFAULT "[]",
    --
    deduplicated BOOLEAN DEFAULT 0,
    extra_timestamps JSONTEXT DEFAULT "[]",
    --
    FOREIGN KEY(upload_id) REFERENCES uploads(id) ON DELETE CASCADE
);


CREATE TABLE IF NOT EXISTS event_comments (
    id TEXT PRIMARY KEY,
    event_id TEXT,
    comment TEXT,
    created_at REAL,
    updated_at REAL,
    FOREIGN KEY(event_id) REFERENCES events(id) ON DELETE CASCADE
);



CREATE TABLE IF NOT EXISTS auth_devices_initial ( -- filled during semantic map
    id TEXT PRIMARY KEY,
    upload_id TEXT,
    file_id TEXT,
    raw_data_id TEXT,
    --
    entity_type TEXT,
    event_kind TEXT,
    event_category JSONTEXT DEFAULT '[]',
    --
    attributes JSONTEXT,     
    --        
    FOREIGN KEY(upload_id) REFERENCES uploads(id) ON DELETE CASCADE,
    FOREIGN KEY(file_id) REFERENCES uploaded_files(id) ON DELETE CASCADE,
    FOREIGN KEY(raw_data_id) REFERENCES raw_data(id) ON DELETE CASCADE
);




-----------------------------------------
--------          VIEWS          --------
-----------------------------------------


-- view for Events Mappings
CREATE VIEW IF NOT EXISTS v_event_field_mappings AS
-- static columns
SELECT 'id' AS field, 'text' AS type
UNION SELECT 'timestamp', 'timestamp'
UNION SELECT 'message', 'text'
UNION SELECT 'event_category', 'category'
UNION SELECT 'event_action', 'text'
UNION SELECT 'event_kind', 'category'
UNION SELECT 'platform', 'text'
UNION
-- dynamic from JSON attributes
SELECT DISTINCT key AS field, 'text' AS type
FROM events, json_each(events.attributes)
WHERE events.attributes IS NOT NULL AND events.attributes != '';





-- view for Auth Devices Mappings
CREATE VIEW IF NOT EXISTS v_device_field_mappings AS
-- static columns
SELECT 'id' AS field, 'text' AS type
UNION SELECT 'entity_type', 'category'
UNION SELECT 'event_kind', 'category'
UNION SELECT 'event_category', 'category'
UNION SELECT 'platform', 'text'
UNION
-- dynamic from JSON attributes
SELECT DISTINCT key AS field, 'text' AS type
FROM auth_devices_initial, json_each(auth_devices_initial.attributes)
WHERE auth_devices_initial.attributes IS NOT NULL AND auth_devices_initial.attributes != '';



-- all event action types
CREATE VIEW IF NOT EXISTS v_event_actions AS
SELECT DISTINCT event_action
FROM events
WHERE event_action IS NOT NULL AND event_action != '';