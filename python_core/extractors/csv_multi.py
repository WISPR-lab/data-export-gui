import pandas as pd
import io
import csv
import re
from typing import List, Dict, Any, Optional
from .csv_ import CSVParser
from python_core.errors import FileLevelError



"""
A "concatenated csv" is a file that contains multiple CSV sections 
separated by titles and newlines. This is common in Apple's datasets.
Determines if a file is a concatenated CSV file by checking if it 
contains multiple sections separated by titles and newlines.
"""       


class CSVMultiParser(CSVParser):

    @classmethod
    def extract(cls, content: str, config: Optional[Dict] = None,  filepath: str = None) -> List[Dict[str, Any]]:
        config = config or {}
        if not content or not content.strip():
            raise FileLevelError("Empty CSV input")
        try:
            
            if cls._is_concatenated(content, filepath):
                
                segments = re.split("\n\n\n", content)
                all_records = []
                current_line = 1
                
                for segment in segments:
                    segment_start_line = current_line
                    lines = [line.strip() for line in segment.split("\n") if len(line.strip()) > 0]
                    if len(lines) >= 2:
                        header = lines[0]
                        csvstring = "\n".join(lines[1:])
                        df, bad_lines, line_map = cls.str_to_df(csvstring)
                        if df.empty:
                            current_line += len(segment.split("\n"))
                            continue
                        records = df.fillna('').to_dict(orient='records')
                        for i, record in enumerate(records):
                            if i in line_map:
                                start, end = line_map[i]
                                record["__line_numbers"] = [segment_start_line + start - 2, segment_start_line + end - 2]
                            else:
                                record["__line_numbers"] = [segment_start_line]
                            record["__segment_header"] = header
                            all_records.append(record)
                    current_line += len(segment.split("\n"))
                return all_records
            
            else: # if not concatenated, parse as a single CSV
                print("[CSVMultiParser] No concatenated sections detected. Parsing as single CSV.")
                df, bad_lines, line_map = cls.str_to_df(content)
                if df.empty:
                    return []
                records = df.to_dict(orient='records')
                for i, record in enumerate(records):
                    if i in line_map:
                        record["__line_numbers"] = line_map[i]
                    else:
                        record["__line_numbers"] = [i + 2]
                return records
                
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

