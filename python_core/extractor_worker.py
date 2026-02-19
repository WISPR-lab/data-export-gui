import os
import json
import sys
import traceback
from datetime import datetime, UTC
import uuid
import hashlib


def get_config_value(name):
    """Get config value from builtins (injected by JS)."""
    import builtins
    if not hasattr(builtins, name):
        raise ValueError(f"Config value '{name}' not found in builtins. Ensure config.yaml is loaded.")
    return getattr(builtins, name)


try:
    from manifest import Manifest
    from db_session import DatabaseSession
    from extractors import get_parser
except ImportError:
    sys.path.append(os.path.dirname(__file__))
    from manifest import Manifest
    from db_session import DatabaseSession
    from extractors import get_parser


def _file_size_bytes(filepath):
    stat = os.stat(filepath)
    file_size_bytes = stat.st_size
    return file_size_bytes

def _file_hash(filepath, alg="sha256"):
    with open(filepath, 'rb') as f:
        hash_object = hashlib.file_digest(f, alg)
    return hash_object.hexdigest()


def extract(platform, 
            given_name, 
            db_path=None, 
            tmp_storage_dir=None, 
            manifest_dir=None):
    
    db_path = db_path or get_config_value('DB_PATH')
    tmp_storage_dir = tmp_storage_dir or get_config_value('TEMP_ZIP_DATA_STORAGE')
    manifest_dir = manifest_dir or get_config_value('MANIFESTS_DIR')
    
    print(f"[Extractor] Extracting '{platform}' files from {tmp_storage_dir} using manifest from {manifest_dir}...")
    ts = datetime.now(UTC).timestamp()
    upload_id = str(uuid.uuid4())
    
    try:

        manifest = Manifest(platform=platform, manifest_dir=manifest_dir)

        with DatabaseSession(db_path) as conn:
            
            if not os.path.exists(tmp_storage_dir):
                print(f"[Extractor] temp storage directory not found: {tmp_storage_dir}")
                parent = os.path.dirname(tmp_storage_dir)
                if os.path.exists(parent):
                    print(f"[Extractor] Parent dir '{parent}' contents: {os.listdir(parent)}")
                else:
                    print(f"[Extractor] Parent dir '{parent}' also does not exist. Check OPFS mount.")
                return {"status": "failure", "error": f"Temp storage directory not found: {tmp_storage_dir}"}

            files = [f for f in os.listdir(tmp_storage_dir) if os.path.isfile(os.path.join(tmp_storage_dir, f))]
            print(f"[Extractor] Found {len(files)} files in {tmp_storage_dir}.")
            if len(files) == 0:
                print(f"[Extractor] Raw dir listing: {os.listdir(tmp_storage_dir)}")
                return {"status": "failure", "error": f"OPFS_EMPTY: No files found in {tmp_storage_dir}. Files were written by JS but are not visible to Python — likely an OPFS/NativeFS sync issue."}

            # Auto-generate upload name: "platform" or "platform 2", "platform 3", etc.
            result = conn.execute(
                'SELECT COUNT(*) FROM uploads WHERE platform = ?',
                [platform]
            ).fetchone()
            count = result[0] if result else 0
            auto_name = platform if count == 0 else f"{platform} {count + 1}"
            
            conn.execute(
                'INSERT INTO uploads (id, platform, given_name, upload_timestamp, updated_at) VALUES (?, ?, ?, ?, ?)',
                (upload_id, platform, auto_name, ts, ts)
            )


            for opfs_filename in files:
                success = True
                opfs_filepath = os.path.join(tmp_storage_dir, opfs_filename)
            
                file_cfg = manifest.get_file_cfg(opfs_filename)
                
                manifest_filename = file_cfg.get('path')
                manifest_file_id = file_cfg.get('id')
                parser_cfg = file_cfg.get('parser', {})  # manifest YAML uses 'parser' not 'parser_config'
                if not manifest_file_id or not parser_cfg or not parser_cfg.get('format'):
                    success = False
                    continue

                fmt = parser_cfg.get('format')
                # print(f"[Extractor] Processing {opfs_filename} -> Source: {manifest_file_id} (Format: {fmt})")

                try:
                    parser = get_parser(fmt)
                    if not parser:
                        print(f"[Extractor] No parser found for format: {fmt}")
                        success = False
                        continue
                    with open(opfs_filepath, 'r', encoding='utf-8', errors='replace') as f:
                        content = f.read()
                    records = parser.extract(content, parser_cfg)
                    if not records:
                        print(f"  -> No records extracted from {opfs_filename}")
                        success = False
                        continue
                    # print(f"  -> Extracted {len(records)} records. Inserting...")
                    print(f"[Extractor] Extracted {len(records)} records from {manifest_file_id}")

                    # read into db
                    file_id = str(uuid.uuid4())
                    file_info = (file_id, manifest_file_id, upload_id, opfs_filename, manifest_filename, _file_hash(opfs_filepath), ts, _file_size_bytes(opfs_filepath), 'success' if success else 'failure')
                    conn.execute(
                        'INSERT INTO uploaded_files (id, manifest_file_id, upload_id, opfs_filename, manifest_filename, file_hash, upload_timestamp, file_size_bytes, parse_status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                        file_info
                    )
                    
                    raw_data_rows = [
                        (str(uuid.uuid4()), upload_id, file_id, json.dumps(r))
                        for r in records
                    ]
                    conn.executemany(
                        'INSERT INTO raw_data (id, upload_id, file_id, data) VALUES (?, ?, ?, ?)',
                        raw_data_rows
                    )
                    conn.commit()

                    row = conn.execute("SELECT COUNT(*) as count FROM raw_data").fetchone()
                    # print(f"  -> Total raw_data rows in DB: {row[0] if row else 'unknown'}")

                except Exception as e:
                    print(f"[Extractor] Error processing {opfs_filename}: {e}")
                    traceback.print_exc()
                    success=False       
        
        return {"status": "success", "upload_id": upload_id}
    
    except Exception as e:
        print(f"[Extractor] Fatal Database Error: {e}")
        return {"status": "failure", "error": str(e)}


if __name__ == "__main__":
    print("NEED EXTRACT ARGUMENTS")