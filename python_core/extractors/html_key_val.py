from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from .base import BaseParser

class HTMLKeyValParser(BaseParser):
    def extract(
        self, content: str, config: Optional[Dict] = None, filepath: str = None
    ) -> List[Dict[str, Any]]:
        text = content.replace("<br/>", "\n").replace("<br>", "\n")
        soup = BeautifulSoup(text, "html.parser")
        
        for element in soup(["style", "script"]):
            element.decompose()
            
        record = {}
        for line in soup.get_text().splitlines():
            line = line.strip()
            if ":" in line:
                parts = line.split(":", 1)
                key = parts[0].strip()
                val = parts[1].strip()
                if key and val:
                    record[key] = val
                    
        record["__line_numbers"] = [1, len(content.splitlines())]
        return [record] if record else []
