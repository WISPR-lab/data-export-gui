import pandas as pd
import io
import csv
import re
from typing import List, Dict, Any, Optional
from .base import BaseParser
from python_core.errors import FileLevelError



"""
A "concatenated csv" is a file that contains multiple CSV sections 
separated by titles and newlines. This is common in Apple's datasets.
Determines if a file is a concatenated CSV file by checking if it 
contains multiple sections separated by titles and newlines.
"""       


class CSVMultiParser(BaseParser):

    @classmethod
    def extract(cls, content: str, config: Optional[Dict] = None,  filepath: str = None) -> List[Dict[str, Any]]:
        config = config or {}
        if not content or not content.strip():
            raise FileLevelError("Empty CSV input")
        try:
            
            if cls._is_concatenated(content, filepath):
                
                segments = re.split("\n\n\n", content)
                header_records_map = {}
                for segment in segments:
                    lines = [line.strip() for line in segment.split("\n") if len(line.strip()) > 0]
                    if len(lines) >= 2:
                        header = lines[0]
                        csvstring = "\n".join(lines[1:])
                        df, bad_lines = cls.str_to_df(csvstring)[0]
                        if df.empty:
                            header_records_map[header] = []
                            continue
                        content = df.fillna('').to_dict(orient='records')
                        header_records_map[header] = content
                return header_records_map
            
            else: # if not concatenated, parse as a single CSV
                print("[CSVMultiParser] No concatenated sections detected. Parsing as single CSV.")
                df, bad_lines = cls.str_to_df(content)
                if df.empty:
                    return []
                return df.to_dict(orient='records')
                
            # TODO deal with error handling
        except FileLevelError:
            raise
        except Exception as e:
            raise FileLevelError(f"CSV extraction failed: {e}", context={'error_type': type(e).__name__})



    @classmethod
    def _is_concatenated(cls, s: str, path: str):
        
        pattern = re.compile(r'^[^\n",]*(\n\s*){2,}[^\n",]*', re.MULTILINE)
        match = pattern.search(s)
        if match:
            return True
        if path is not None and isinstance(path, str):
            if "iCloudUsageData" in path: # match did not pick up on file, but likely has concatenated contents
                return True
        return False    

