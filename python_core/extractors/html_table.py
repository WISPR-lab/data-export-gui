from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from .base import BaseParser
from .csv_ import CSVParser
from python_core.errors import FileLevelError


class HTMLTableParser(CSVParser):

    @classmethod
    def _extract_table(cls, table_element) -> List[Dict[str, Any]]:
        headers = []
        rows_data = []
        
        thead = table_element.find('thead')
        tbody = table_element.find('tbody')
        
        if thead:
            header_row = thead.find('tr')
            if header_row:
                headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]
        
        if not headers:
            first_tr = table_element.find('tr')
            if first_tr:
                potential_headers = first_tr.find_all(['th', 'td'])
                if all(cell.name == 'th' for cell in potential_headers):
                    headers = [th.get_text(strip=True) for th in potential_headers]
        
        rows_to_parse = tbody.find_all('tr') if tbody else table_element.find_all('tr')[1:] if headers else table_element.find_all('tr')
        
        for row in rows_to_parse:
            cells = row.find_all(['td', 'th'])
            if cells:
                row_dict = {}
                for i, cell in enumerate(cells):
                    col_name = headers[i] if i < len(headers) else f"Column_{i}"
                    row_dict[col_name] = cell.get_text(strip=True)
                rows_data.append(row_dict)
        
        return rows_data

    @classmethod
    def extract(cls, content: str, config: Optional[Dict] = None, filepath: str = None) -> List[Dict[str, Any]]:
        config = config or {}
        if not content or not content.strip():
            raise FileLevelError("Empty HTML input")
        try:
            soup = BeautifulSoup(content, 'html.parser')
            tables = soup.find_all('table')
            
            if not tables:
                raise FileLevelError("No tables found in HTML")
            
            total_lines = len(content.splitlines())
            all_rows = []
            
            if len(tables) > 1:
                print(f"[HTMLTableParser] Warning: Multiple tables found in HTML. Extracting {len(tables)} tables.")
                for i, table in enumerate(tables):
                    rows = cls._extract_table(table)
                    for row in rows:
                        row["__line_numbers"] = [1, total_lines]
                    all_rows.extend(rows)
            else:
                rows = cls._extract_table(tables[0])
                for row in rows:
                    row["__line_numbers"] = [1, total_lines]
                all_rows.extend(rows)
            
            return all_rows
            
        except FileLevelError:
            raise
        except Exception as e:
            raise FileLevelError(f"CSV extraction failed: {e}", context={'error_type': type(e).__name__})
