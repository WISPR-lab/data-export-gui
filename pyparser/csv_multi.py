from base import BaseParser
from parseresult import ParseResult
from errors import FileLevelError
import re



"""
A "concatenated csv" is a file that contains multiple CSV sections 
separated by titles and newlines. This is common in Apple's datasets.
Determines if a file is a concatenated CSV file by checking if it 
contains multiple sections separated by titles and newlines.
"""       


class CSVMultiParser(BaseParser):

    @classmethod
    def parse(cls, s: str, filename: str, cfg, default="", **kwargs):
        """Placeholder: CSV multi-section parser not yet implemented"""
        result = ParseResult()
        result.add_error(FileLevelError(
            "CSV multi-section parser not yet implemented", 
            context={'filename': filename}
        ))
        return result

    @classmethod
    def _is_concatenated(cls, s: str, path: str):
        
        pattern = re.compile(r'^[^\n",]*(\n\s*){2,}[^\n",]*', re.MULTILINE)
        match = pattern.search(s)
        if match:
            return True
        if path is not None:
            if "iCloudUsageData" in path:
                return True
        return False

        
""" TODO: Implement multi-section CSV parsing """