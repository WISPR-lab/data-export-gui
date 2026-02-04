from json_ import JSONParser
from errors import RecordLevelError

class JSONLParser(JSONParser):
        

    @classmethod
    def str_to_json(cls, s: str):
        """Parse JSONL format line-by-line with error tracking"""
        dicts = []
        errors = []
        for line_num, line in enumerate(s.split("\n"), 1):
            if len(line.strip()) == 0:
                continue
            try:
                obj = cls.basic_str_to_json(line)
                dicts.append(obj)
            except Exception as e:
                errors.append(RecordLevelError(
                    f"Line {line_num} parse error: {str(e)}", 
                    context={'line_num': line_num, 'line_preview': line[:50]}
                ))
        return dicts, errors