from json_ import JSONParser
from errors import RecordLevelError
from typing import List, Dict, Any, Optional


try:
    from python_core.utils.filter_builder import make_filter
except ImportError:
    from ..utils.filter_builder import make_filter


from utils.filter_builder import make_filter


class JSONLParser(JSONParser):

    @classmethod
    def extract(cls, content: str, config: Optional[Dict] = None) -> List[Dict[str, Any]]:
        res = []
        if "where" in config:
            filter_callable = make_filter(config["where"])
        
        for line in content.splitlines():
            line = line.strip()
            if not line: continue
            try:
                obj = cls.basic_str_to_json(line)
                if "where" in config and not filter_callable(obj):
                    continue
                res.append(obj)
            except:
                continue # TODO ERROR HANDLING

        return res
        
