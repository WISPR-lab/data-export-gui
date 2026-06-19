import js
from extractors import worker as extractor_worker
import semantic_map.worker as semantic_map_worker
from field_normalization import worker as norm_worker
import device_grouping2.worker as device_grouping2_worker
from semantic_map.worker import get_counts

def run(platform: str, given_name: str) -> dict:
    # 1. Extract
    js.reportProgress('extract', 30)
    extract_res = extractor_worker.extract(platform, given_name)
    upload_id = extract_res.get('upload_id')
    if not upload_id:
        raise ValueError("Extraction failed to return an upload_id")

    # 2. Semantic Map
    js.reportProgress('semantic_map', 40)
    semantic_map_worker.map(platform, upload_id)

    # 3. Normalize
    js.reportProgress('normalize', 60)
    norm_worker.normalize(upload_id)

    # 4. Group
    js.reportProgress('group', 85)
    device_grouping2_worker.group(upload_id)

    counts = get_counts(upload_id)
    return {
        'status': 'success',
        'upload_id': upload_id,
        'events_count': counts.get('events_count', 0),
        'devices_count': counts.get('devices_count', 0),
        'partial_errors': extract_res.get('partial_errors', [])
    }
