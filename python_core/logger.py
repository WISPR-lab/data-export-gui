import logging
import os
import sys
from python_core.runtime.pyodide_utils import get_config_value


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(f"python_core.{name}")
    
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter("[%(name)s] %(levelname)s: %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.propagate = False

    env_level = os.environ.get("LOG_LEVEL") or get_config_value("LOG_LEVEL", default="INFO")
    level = getattr(logging, str(env_level).upper(), logging.INFO)
    logger.setLevel(level)

    return logger
