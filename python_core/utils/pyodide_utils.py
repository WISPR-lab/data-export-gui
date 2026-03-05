import builtins

def init_pyodide():
    try:
        from extractors import worker as extractor_worker
    except Exception as e:
        print(f"[Pyodide] Error importing extractors.worker: {e}")

    try:
        from semantic_map import worker as semantic_map_worker
    except Exception as e:
        print(f"[Pyodide] Error importing semantic_map.worker: {e}")


def load_manifests():
    import os
    import builtins
    
    manifests_dir = builtins.MANIFESTS_DIR
    yaml_files = [f for f in os.listdir(manifests_dir) if f.endswith('.yaml')]
    return yaml_files

