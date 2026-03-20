import pandas as pd
import io
import re
import csv
import pandas as pd
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from .base import BaseParser
from .csv_ import CSVParser
from python_core.errors import FileLevelError



class HTMLMyActvityParser(BaseParser):

    @classmethod
    def extract(cls, content: str, config: Optional[Dict] = None,  filepath: str = None) -> List[Dict[str, Any]]:
        config = config or {}
        if not content or not content.strip():
            raise FileLevelError("Empty HTML input")
        try:

            soup = BeautifulSoup(content, 'html.parser')
            return cls._parse_google_myactivity(soup) 
            
        except FileLevelError:
            raise
        except Exception as e:
            raise FileLevelError(f"CSV extraction failed: {e}", context={'error_type': type(e).__name__})


    @classmethod
    def _parse_google_myactivity(cls, soup: BeautifulSoup) -> list[dict]:
            outer_cells = soup.find_all('div', class_='outer-cell mdl-cell mdl-cell--12-col mdl-shadow--2dp')
            data_list = []

            for cell in outer_cells:
                data_dict = {}
            
                header = cell.find('div', class_='header-cell mdl-cell mdl-cell--12-col').get_text(strip=True)
                data_dict['Platform'] = header
                
                content_cells = cell.find_all('div', class_='content-cell mdl-cell mdl-cell--6-col mdl-typography--body-1')
                
                activity_cell = content_cells[0]
                activity_text = activity_cell.get_text(separator='<br>', strip=True).split('<br>')
                activity_line = activity_text[0]
                data_dict['Activity'] = re.sub(r'\s+', ' ', activity_line)
                
                
                link = activity_cell.find('a')  # link in activity cell
                if link:
                    data_dict['Activity'] = link.get_text(strip=True)
                    data_dict['URL'] = link['href']
                
                for line in activity_text[1:]:  # address and timestamp
                    if re.search(r'\d{4}', line):
                        data_dict['Timestamp'] = line
                    elif data_dict['Platform'] == 'Maps':
                        data_dict['Address'] = line
                
                # context cell
                context_cell = cell.find('div', class_='content-cell mdl-cell mdl-cell--12-col mdl-typography--caption')
                if context_cell:
                    #context_lines = context_cell.get_text(separator='<br>', strip=True).split('<br>')
                    # Replace <br> with a unique placeholder
                    context_lines = context_cell.get_text(separator='[BR]', strip=True).split('[BR]')
                    newcontextlines = []
                    for i, elem in enumerate(context_lines):
                        if elem == "Locations:" and context_lines[i+1] == "At":
                            context_lines.extend(["Locations:", "At this general area - Based on your past activity"])
                        elif elem in ("At", "this general area", "- Based on your past activity"):
                            continue
                        elif elem == "here":
                            newcontextlines[-1] = newcontextlines[-1] + " " + elem
                        elif elem == ".":
                            newcontextlines[-1] = newcontextlines[-1] + elem
                        else:
                            newcontextlines.append(elem)
                    context_lines = newcontextlines

                    for i in range(0, len(context_lines), 2):
                        attribute = context_lines[i].replace(':', '').strip()
                        value = context_lines[i + 1].strip()
                        if attribute == 'Locations':
                            location_link = context_cell.find('a')
                            if location_link:
                                data_dict['Location.URL'] = location_link['href']
                                #value = location_link.get_text(strip=True)
                        if attribute == 'here':
                            continue
                        data_dict[attribute] = value
                
                data_list.append(data_dict)
            
            return data_list
