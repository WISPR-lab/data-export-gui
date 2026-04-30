import pandas as pd
import io
import csv
from typing import List, Dict, Any, Optional
from .base import BaseParser
from python_core.errors import FileLevelError

class CSVParser(BaseParser):

    @classmethod
    def extract(cls, content: str, config: Optional[Dict] = None,  filepath: str = None) -> List[Dict[str, Any]]:
        config = config or {}
        if not content or not content.strip():
            raise FileLevelError("Empty CSV input")
        try:
            df, bad_lines, line_map = cls.str_to_df(content)
            
            if df.empty:
                return []
                
            records = df.to_dict(orient='records')
            for i, record in enumerate(records):
                if i in line_map:
                    record["__line_numbers"] = line_map[i]
                else:
                    record["__line_numbers"] = [i + 2]  # fallback: header on line 1, data starts at line 2
            return records
            
        except FileLevelError:
            raise
        except Exception as e:
            raise FileLevelError(f"CSV extraction failed: {e}", context={'error_type': type(e).__name__})

    @classmethod
    def str_to_df(cls, s: str):
        bad_lines = []
        line_map = {}  # map from row_index to [start_line, end_line]
        
        # Track line boundaries for each record (handles multiline values)
        lines = s.splitlines(keepends=False)
        row_idx = 0
        current_record_start = 2  # data starts at line 2 (1-indexed, after header)
        in_quote = False
        
        for line_num, line in enumerate(lines, start=1):
            if line_num == 1:  # header
                continue
            # Very basic quote tracking for multiline values
            in_quote = in_quote ^ (line.count('"') % 2 == 1)
            if not in_quote:
                # End of a record
                line_map[row_idx] = [current_record_start, line_num]
                row_idx += 1
                current_record_start = line_num + 1
        
        def handle_bad_line(line):
            bad_lines.append(f"Malformed or ragged line skipped: {','.join(line[:5])}...")
            return None
        try:
            df = pd.read_csv(
                io.StringIO(s),
                dtype=str,
                keep_default_na=False,
                on_bad_lines=handle_bad_line,
                engine='python',
                quoting=csv.QUOTE_MINIMAL
            )
            df = df.dropna(how='all')
            return df, bad_lines, line_map
        except Exception as e:
            raise FileLevelError(f"CSV parse failed: {e}", context={'error_type': type(e).__name__})




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