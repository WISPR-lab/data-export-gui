"""Load and normalize the FP Stalker dataset from DuckDB into a DataFrame."""
import sys
from pathlib import Path

import duckdb
import pandas as pd
from tqdm import tqdm

import evaluation.entity_resolution.config as cf

_root = Path(__file__).resolve().parent.parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

import python_core.field_normalization.user_agent as ua
from python_core.field_normalization.device import normalize_device_fields

_ua_parser = ua.UserAgentParser()


def _normalize_rows(df: pd.DataFrame, ua_col: str, ts_col: str, keep_cols: list) -> pd.DataFrame:
    records = []
    for _, row in tqdm(df.iterrows(), total=len(df), desc="Normalizing UA strings"):
        d = _ua_parser.parse({"user_agent_original": row.get(ua_col, "")})
        d = normalize_device_fields(d)
        norm = {k: v for k, v in d.items() if k.startswith("norm__")}
        norm["timestamp"] = row.get(ts_col, "")
        records.append(norm)

    norm_df = pd.DataFrame(records, index=df.index)
    norm_cols = [c for c in norm_df.columns if c.startswith("norm__")]
    result = pd.concat([norm_df[["timestamp"] + norm_cols], df[[c for c in keep_cols if c in df.columns] + [ua_col]]], axis=1)
    result.rename(columns={c: f"attr__{c}" for c in norm_cols}, inplace=True)
    return result


def load() -> pd.DataFrame:
    print(f"Loading FP Stalker from {cf.FP_STALKER_DB} ...")
    with duckdb.connect(str(cf.FP_STALKER_DB), read_only=True) as conn:
        raw = conn.execute(f"SELECT * FROM {cf.DB_TABLE}").df()
    print(f"  {len(raw)} records, {raw['id'].nunique()} unique tracking IDs")

    df = _normalize_rows(raw, ua_col="userAgentHttp", ts_col="creationDate",
                         keep_cols=["id", "counter", "osDetailed", "browserDetailed"])
    df.rename(columns={"id": "tracking_id", "counter": "id"}, inplace=True)
    return df
