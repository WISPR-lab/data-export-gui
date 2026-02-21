from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class BaseParser(ABC):

    encoding = 'utf-8'


    @classmethod
    def _is_trivial(cls, x):
        return (x is None) \
            or (isinstance(x, str) and x.strip() == "") \
            or (x == []) \
            or (isinstance(x, list) and all((e == "" or e is None or e == []) for e in x))

    
    
    @abstractmethod
    def extract(self, content: str, config: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """
        Parses content into a flat list of dicts.
        config: The 'parser' section from the YAML manifest (e.g., {'json_root': '...'})
        """
        pass

