import pandas as pd
import io
import csv
from typing import List, Dict, Any, Optional
from .base import BaseParser

pd.options.mode.copy_on_write = True

class CSVParser(BaseParser):

    @classmethod
    def extract(cls, content: str, config: Optional[Dict] = None) -> List[Dict[str, Any]]:
        config = config or {}
        try:
            df, bad_lines = cls.str_to_df(content)
            
            if df.empty:
                return []
                
            # Convert to list of dicts. 
            return df.to_dict(orient='records')
            
        except Exception:
            return [] # TODO error handling

    @classmethod
    def str_to_df(cls, s: str):
        bad_lines = []
        def handle_bad_line(line):
            bad_lines.append(f"Malformed or ragged line skipped: {','.join(line[:5])}...")
            return None
        try:
            # engine='python' is more robust for bad lines and allows the callable
            df = pd.read_csv(
                io.StringIO(s),
                dtype=str,
                keep_default_na=False,
                on_bad_lines=handle_bad_line,
                engine='python',
                quoting=csv.QUOTE_MINIMAL
            )
            df = df.dropna(how='all') # Drop fully empty rows
            return df, bad_lines
        except Exception:  # TODO error handling 
            return pd.DataFrame(), []




    @classmethod
    def drop_duplicates(cls, df, dupe_cfg: dict):
        # dupe_cfg = { subset: ["Recovery ID"], keep: "row_completeness"}
        try:
            subset = dupe_cfg.get("subset", [])
            keep = dupe_cfg.get("keep", "first")
            if keep not in ["first", "last", "row_completeness"]:
                # TODO log warning eventually
                keep = "first"
            
            if keep == "row_completeness":
                # Add temp columns for null count and original order
                null_counts = df.replace('', pd.NA).notnull().sum(axis=1)
                df = df.assign(temp_null_count=null_counts, temp_orig_index=range(len(df)))
                df = df.sort_values(['temp_null_count', 'temp_orig_index'], ascending=[False, True])
                df = df.drop_duplicates(subset=subset, keep='first')
                df = df.sort_values('temp_orig_index').drop(columns=['temp_null_count', 'temp_orig_index'])
            else:
                df = df.drop_duplicates(subset=subset, keep=keep)
            return df
        
        except Exception as e:
            raise RuntimeError(f"drop_duplicates error: {str(e)}")