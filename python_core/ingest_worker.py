import sqlite3
import os
import json
import sys
import yaml # Requires pyyaml package in pyodide
import pyodide.http

# Import SchemaCompiler
try:
    from schema_compiler import SchemaCompiler
except ImportError:
    # Handle case where file placement might differ in dev vs prod
    # Assuming it's in the same directory context for Worker
    print("[IngestWorker] Warning: could not import SchemaCompiler directly")
    pass


# Constants
DB_PATH = '/mnt/data/forensics.db'
BRONZE_DIR = '/mnt/data/bronze'
# Assuming schemas are provided in a known location or passed in. 
# Prompt says: "The worker receives the content of the YAML files..."
# We will look for them in a mounted dir for this implementation.
SCHEMAS_DIR = '/schemas' 
BATCH_SIZE = 1000

# Global Registry: Filename Pattern -> {schema_id, parser_format}
# Use a list of (Regex/EndsWith, Info) for matching
FILE_REGISTRY = []
YAML_CONFIGS = []

async def load_schemas():
    """Reads YAML schemas and builds the file registry."""
    global FILE_REGISTRY, YAML_CONFIGS
    FILE_REGISTRY = []
    YAML_CONFIGS = []
    
    if not os.path.exists(SCHEMAS_DIR):
        print(f"[IngestWorker] Schema directory {SCHEMAS_DIR} not found. Skipping schema load.")
        return

    print(f"[IngestWorker] Loading schemas from {SCHEMAS_DIR}...")
    
    for filename in os.listdir(SCHEMAS_DIR):
        if not filename.endswith('.yaml'):
            continue
            
        try:
            with open(os.path.join(SCHEMAS_DIR, filename), 'r') as f:
                doc = yaml.safe_load(f)
                if not doc: continue
                
                YAML_CONFIGS.append(doc)
                schema_id = doc.get('id')
                
                for dt in doc.get('data_types', []):
                    # cat = dt.get('category')
                    for file_def in dt.get('files', []):
                        path = file_def.get('path')
                        parser = file_def.get('parser', {})
                        parser_fmt = parser.get('format', 'json')
                        
                        if path:
                            # Normalize path for matching (e.g. forward slashes)
                            # We'll use suffix matching as done in JS
                            FILE_REGISTRY.append({
                                'suffix': path,
                                'schema_id': schema_id,
                                'format': parser_fmt
                            })
                            
        except Exception as e:
            print(f"[IngestWorker] Error parsing {filename}: {e}")

    print(f"[IngestWorker] Loaded {len(YAML_CONFIGS)} schemas, {len(FILE_REGISTRY)} file patterns.")


def match_file_to_schema(filename):
    """Finds the schema ID and parser format for a given filename."""
    # Normalize filename separators (OPFS 'filename' usually clean, usually no dirs if flattened)
    # If flattened as 'dir___file', we might need to reconstruct?
    # Phase 1 opfs_manager flattens path: 'path/to/file' -> 'path___to___file'
    # But filtering was done on original path.
    # Here we have the flattened filename on disk? 
    # Or does `process_file` get the original logical path?
    # `ingest_loop` lists `BRONZE_DIR` which has filenames like `folder___file.json`.
    
    # Let's handle the flattened name provided by `files = os.listdir(BRONZE_DIR)` in ingest_loop.
    # Convert '___' back to '/' to match against schema paths (which use '/')
    
    logical_path = filename.replace('___', '/')
    
    # Determine Schema
    for entry in FILE_REGISTRY:
        suffix = entry['suffix']
        # Suffix match (case insensitive?)
        if logical_path.lower().endswith(suffix.lower()):
            return entry['schema_id'], entry['format']
            
    return 'unknown_vendor', 'json' # Default


async def init_db():
    """Initialize the SQLite database with WAL mode."""
    print(f"[IngestWorker] Initializing database at {DB_PATH}...")
    try:
        # Fetch the schema from the public server (via symlink)
        schema_url = "/python_core/database/schema.sql"
        print(f"[IngestWorker] Fetching schema from {schema_url}...")
        try:
            response = await pyodide.http.pyfetch(schema_url)
            if response.status != 200:
                print(f"[IngestWorker] Failed to fetch schema: {response.status}")
                # Fallback to hardcoded if fetch fails? Or raise?
                # For now proceed with basic table creation if fetch fails? 
                # Or simplistic create table
            else:
                schema_sql = await response.string()
                
                conn = sqlite3.connect(DB_PATH)
                conn.execute('PRAGMA journal_mode=WAL;')
                conn.executescript(schema_sql)
                conn.commit()
                
                # Verify WAL mode
                cursor = conn.execute('PRAGMA journal_mode;')
                mode = cursor.fetchone()[0]
                print(f"[IngestWorker] Database journal mode: {mode}")
                
                return conn
        except Exception as fetch_err:
             print(f"[IngestWorker] Schema fetch error: {fetch_err}")
             # Retry or fallback logic could go here
             
    except Exception as e:
        print(f"[IngestWorker] DB Init Error: {e}")
        return None

class BaseAdapter:
    """Base adapter for converting raw content to dicts."""
    def parse_line(self, line):
        try:
            return json.loads(line)
        except:
            return None

def process_file(filepath, filename, conn):
    """Reads a file line-by-line and ingests into DB."""
    
    # Identify Protocol/Schema
    schema_id, fmt = match_file_to_schema(filename)
    print(f"[IngestWorker] Processing {filename} as {schema_id} ({fmt})")

    adapter = BaseAdapter()
    rows_buffer = []
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            for line in f:
                if not line.strip(): 
                    continue
                    
                record = None
                
                # Check format from Schema
                if fmt in ['jsonl', 'json']: 
                     # For now treating JSON and JSONL mostly same for line-based ingestion
                     # Real implementation would respect 'parser' config more strictly 
                     # (e.g. read whole file for 'json')
                     record = adapter.parse_line(line)
                elif fmt.startswith('csv'):
                    # TODO: CSV handling
                    pass

                if record:
                    # Insert with schema_id as adapter_type
                    rows_buffer.append((filename, schema_id, json.dumps(record)))
                
                # Check buffer
                if len(rows_buffer) >= BATCH_SIZE:
                    conn.executemany('INSERT INTO raw_events (source_file, adapter_type, raw_data) VALUES (?, ?, ?)', rows_buffer)
                    conn.commit()
                    rows_buffer = []
            
            # Handle full-file JSON if needed (naive)
            # If line-by-line failed/was empty but it's a JSON file
            # This is a fallback block from Phase 1, preserved but updated
            if not rows_buffer and fmt == 'json':
                 f.seek(0)
                 try:
                     full_data = json.load(f)
                     if isinstance(full_data, list):
                         new_rows = [(filename, schema_id, json.dumps(item)) for item in full_data]
                         rows_buffer.extend(new_rows)
                     elif isinstance(full_data, dict):
                         rows_buffer.append((filename, schema_id, json.dumps(full_data)))
                 except:
                     pass

        # Final flush
        if rows_buffer:
            conn.executemany('INSERT INTO raw_events (source_file, adapter_type, raw_data) VALUES (?, ?, ?)', rows_buffer)
            conn.commit()
            
    except Exception as e:
        print(f"[IngestWorker] Error processing {filename}: {e}")

async def ingest_loop():
    """Main loop to check bronze directory and ingest files."""
    
    # 1. Init DB
    conn = await init_db()
    if not conn: return
    
    # 2. Load Schemas
    await load_schemas()
    
    # 3. Compile Views (Silver Layer)
    if YAML_CONFIGS:
        compiler = SchemaCompiler()
        compiler.compile_views(conn, YAML_CONFIGS)
    else:
        print("[IngestWorker] No YAML configs found. Skipping View compilation.")
    
    # 4. Ingest Files
    if not os.path.exists(BRONZE_DIR):
        print(f"[IngestWorker] No bronze directory at {BRONZE_DIR}")
        conn.close()
        return

    files = os.listdir(BRONZE_DIR)
    print(f"[IngestWorker] Found {len(files)} files in bronze layer.")
    
    for filename in files:
        filepath = os.path.join(BRONZE_DIR, filename)
        if os.path.isfile(filepath):
            process_file(filepath, filename, conn)
            
    conn.close()
    print("[IngestWorker] Ingest complete.")

# Expose function for global call
if __name__ == '__main__':
    # When run directly
    pass
