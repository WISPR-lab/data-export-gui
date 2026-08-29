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
    def extract(
        cls, content: str, config: Optional[Dict] = None, filepath: str = None
    ) -> List[Dict[str, Any]]:
        config = config or {}
        if not content or not content.strip():
            raise FileLevelError("Empty CSV input")
        try:
            if cls._is_concatenated(content, filepath):
                segments = []
                pos = 0
                for m in re.finditer(r"\n\s*\n", content):
                    segments.append((pos, content[pos:m.start()]))
                    pos = m.end()
                segments.append((pos, content[pos:]))
                all_records = []

                for seg_offset, segment in segments:
                    segment_start_line = content.count("\n", 0, seg_offset) + 1
                    lines = [
                        line.strip()
                        for line in segment.split("\n")
                        if len(line.strip()) > 0
                    ]
                    if len(lines) >= 2:
                        header = lines[0]
                        csvstring = "\n".join(lines[1:])
                        df, bad_lines, line_map = cls.str_to_df(csvstring)
                        if df.empty:
                            continue
                        records = df.fillna("").to_dict(orient="records")
                        for i, record in enumerate(records):
                            if i in line_map:
                                start, end = line_map[i]
                                record["__line_numbers"] = [
                                    segment_start_line + start,
                                    segment_start_line + end,
                                ]
                            else:
                                record["__line_numbers"] = [segment_start_line]
                            record["__segment_header"] = header
                            all_records.append(record)
                return all_records

            else:  # if not concatenated, parse as a single CSV
                print(
                    "[CSVMultiParser] No concatenated sections detected. Parsing as single CSV."
                )
                df, bad_lines, line_map = cls.str_to_df(content)
                if df.empty:
                    return []
                records = df.to_dict(orient="records")
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
            raise FileLevelError(
                f"CSV extraction failed: {e}", context={"error_type": type(e).__name__}
            )

    @classmethod
    def _is_concatenated(cls, s: str, path: str):

        # one or more blank lines followed by a title line (no commas/quotes)
        pattern = re.compile(r'\n[ \t]*\n\s*[^\n",]+\n')
        match = pattern.search(s)
        if match:
            return True
        if path is not None and isinstance(path, str):
            if (
                "iCloudUsageData" in path
            ):  # match did not pick up on file, but likely has concatenated contents
                return True
        return False
