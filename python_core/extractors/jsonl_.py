from .json_ import JSONParser
from python_core.errors import FileLevelError, RecordLevelError
from typing import List, Dict, Any, Optional
from utils.filter_builder import make_filter


class JSONLParser(JSONParser):

    @classmethod
    def extract(cls, content: str, config: Optional[Dict] = None,  filepath: str = None) -> List[Dict[str, Any]]:
        config = config or {}
        res = []
        if "where" in config:
            filter_callable = make_filter(config["where"])
        
        line_num = 0
        for line in content.splitlines():
            line_num += 1
            line = line.strip()
            if not line: continue
            try:
                obj = cls.basic_str_to_json(line)
                if "where" in config and not filter_callable(obj):
                    continue
                obj["__line_numbers"] = [line_num, line_num]
                res.append(obj)
            except FileLevelError:
                raise
            except Exception:
                continue

        return res
        
