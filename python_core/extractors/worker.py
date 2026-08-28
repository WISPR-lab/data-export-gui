import os
import json
import sys
import traceback
from datetime import datetime, timezone
import uuid
import hashlib
import python_core.runtime.safe_file_utils as safefileutils
from python_core.runtime.pyodide_utils import get_config_value


from manifest import Manifest
from db_session import DatabaseSession
from extractors import get_parser
from python_core.errors import FileLevelError
from python_core.logger import get_logger

logger = get_logger("extractors")


def _file_size_bytes(filepath: str, use_memfs: bool = False) -> int:
    if use_memfs:
        return safefileutils.getsize(filepath)
    else:
        stat = os.stat(filepath)
        return stat.st_size


def _file_hash(filepath: str, alg: str = "sha256", use_memfs: bool = False) -> str:
    if use_memfs:
        return safefileutils.file_hash(filepath, alg)
    else:
        with open(filepath, "rb") as f:
            hash_object = hashlib.file_digest(f, alg)
        return hash_object.hexdigest()


def _file_read(filepath: str, use_memfs: bool = False) -> str:
    if use_memfs:
        content = safefileutils.read_text(filepath)
    else:
        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    return content


def extract(
    platform: str,
    given_name: str,
    db_path: str = None,
    tmp_storage_dir: str = None,
    manifest: Manifest = None,
    conn=None,
) -> dict:

    tmp_storage_dir = tmp_storage_dir or get_config_value("TEMP_ZIP_DATA_STORAGE")
    use_memfs = get_config_value("IS_FIREFOX") or get_config_value("IS_SAFARI")

    ts = datetime.now(timezone.utc).timestamp()
    upload_id = uuid.uuid4().hex

    try:
        manifest = manifest or Manifest(platform=platform)

        with DatabaseSession(db_path, existing_conn=conn) as conn:
            if not safefileutils.exists(tmp_storage_dir):
                logger.error("Temp storage directory not found: %s", tmp_storage_dir)
                return {
                    "status": "failure",
                    "error": f"Temp storage directory not found: {tmp_storage_dir}",
                }

            files = [
                f
                for f in os.listdir(tmp_storage_dir)
                if safefileutils.isfile(os.path.join(tmp_storage_dir, f))
            ]
            if len(files) == 0:
                logger.warning("No files found in %s.", tmp_storage_dir)
                return {
                    "status": "failure",
                    "error": f"OPFS_EMPTY: No files found in {tmp_storage_dir}. Files were written by JS but are not visible to Python — likely an OPFS/NativeFS sync issue.",
                }

            COLOR_PALETTE = ["5E75C2", "BB77C4", "FD7EAC"]

            # Backfill any existing uploads that don't have a color
            null_cursor = conn.execute(
                'SELECT id FROM uploads WHERE color IS NULL OR color = ""'
            )
            null_uploads = null_cursor.fetchall()
            for idx, (up_id,) in enumerate(null_uploads):
                conn.execute(
                    "UPDATE uploads SET color = ? WHERE id = ?",
                    (COLOR_PALETTE[idx % len(COLOR_PALETTE)], up_id),
                )

            # Auto-generate upload name: "platform" or "platform 2", "platform 3", etc.
            result = conn.execute(
                "SELECT COUNT(*) FROM uploads WHERE platform = ?", [platform]
            ).fetchone()
            count = result[0] if result else 0
            auto_name = platform if count == 0 else f"{platform} {count + 1}"

            total_result = conn.execute("SELECT COUNT(*) FROM uploads").fetchone()
            total_count = total_result[0] if total_result else 0
            assigned_color = COLOR_PALETTE[total_count % len(COLOR_PALETTE)]

            conn.execute(
                "INSERT INTO uploads (id, platform, given_name, upload_timestamp, updated_at, color) VALUES (?, ?, ?, ?, ?, ?)",
                (upload_id, platform, auto_name, ts, ts, assigned_color),
            )

            partial_errors = []
            for opfs_filename in files:
                opfs_filepath = os.path.join(tmp_storage_dir, opfs_filename)
                file_cfgs = manifest.get_file_cfgs(opfs_filename)
                content = None  # lazily read once, reused across configs sharing this physical file

                for file_cfg in file_cfgs:
                    success = True

                    manifest_filename = file_cfg.get("path")
                    manifest_file_id = file_cfg.get("id")
                    parser_cfg = file_cfg.get(
                        "parser", {}
                    )  # manifest YAML uses 'parser' not 'parser_config'
                    if (
                        not manifest_file_id
                        or not parser_cfg
                        or not parser_cfg.get("format")
                    ):
                        success = False
                        continue

                    fmt = parser_cfg.get("format")

                    try:
                        parser = get_parser(fmt)
                        if not parser:
                            logger.warning("No parser found for format '%s' (file '%s')", fmt, opfs_filename)
                            success = False
                            continue

                        if content is None:
                            content = _file_read(opfs_filepath, use_memfs)

                        records = parser.extract(content, parser_cfg, opfs_filename)
                        if not records:
                            logger.warning("No records extracted from file '%s' (manifest_file_id='%s')", opfs_filename, manifest_file_id)
                            success = False
                            continue

                        logger.debug("Extracted %d records from %s", len(records), manifest_file_id)

                        file_hash = hashlib.sha256(content.encode("utf-8", errors="replace")).hexdigest()

                        # read into db
                        file_id = uuid.uuid4().hex
                        file_info = (
                            file_id,
                            manifest_file_id,
                            upload_id,
                            opfs_filename,
                            manifest_filename,
                            file_hash,
                            ts,
                            _file_size_bytes(opfs_filepath, use_memfs=use_memfs),
                            "success" if success else "failure",
                        )
                        conn.execute(
                            "INSERT INTO uploaded_files (id, manifest_file_id, upload_id, opfs_filename, manifest_filename, file_hash, upload_timestamp, file_size_bytes, parse_status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            file_info,
                        )

                        raw_data_rows = []
                        for r in records:
                            line_numbers = r.pop("__line_numbers", [1])
                            raw_data_rows.append(
                                (
                                    uuid.uuid4().hex,
                                    upload_id,
                                    file_id,
                                    json.dumps(r),
                                    json.dumps(line_numbers),
                                )
                            )
                        conn.executemany(
                            "INSERT INTO raw_data (id, upload_id, file_id, data, line_numbers) VALUES (?, ?, ?, ?, ?)",
                            raw_data_rows,
                        )
                        conn.commit()

                    except FileLevelError as e:
                        logger.error("File-level parse error for %s: %s", opfs_filename, e)
                        partial_errors.append(
                            {"file": opfs_filename, "level": "error", "msg": str(e)}
                        )
                        success = False
                    except Exception as e:
                        logger.error("Error processing %s: %s", opfs_filename, e)
                        traceback.print_exc()
                        partial_errors.append(
                            {"file": opfs_filename, "level": "error", "msg": str(e)}
                        )
                        success = False

            logger.info("Extraction completed for upload_id: %s (%d files processed)", upload_id, len(files))
            return {
                "status": "success",
                "upload_id": upload_id,
                "partial_errors": partial_errors,
            }

    except Exception as e:
        logger.error("Fatal Database Error: %s", e)
        return {"status": "failure", "error": str(e)}


if __name__ == "__main__":
    print("NEED EXTRACT ARGUMENTS")
