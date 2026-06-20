def init_pyodide() -> None:
    try:
        from extractors import worker as extractor_worker
    except Exception as e:
        print(f"[Pyodide] Error importing extractors.worker: {e}")

    try:
        from semantic_map import worker as semantic_map_worker
    except Exception as e:
        print(f"[Pyodide] Error importing semantic_map.worker: {e}")


def load_manifests() -> list:
    import os
    import builtins

    manifests_dir = builtins.MANIFESTS_DIR
    yaml_files = [f for f in os.listdir(manifests_dir) if f.endswith(".yaml")]
    return yaml_files


def get_config_value(name: str, default: str = "NONE FOUND"):
    """Reads from builtins namespace (injected by pyodide-worker.js at boot)."""
    try:
        import builtins

        return getattr(builtins, name, default)
    except (ImportError, AttributeError):
        return default
        # raise ValueError(
        #     f"Config value '{name}' not found in builtins. Ensure config.yaml is loaded."
        # )
