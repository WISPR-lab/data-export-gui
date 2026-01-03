from .format_handler import FormatHandler
import re



"""
A "concatenated csv" is a file that contains multiple CSV sections 
separated by titles and newlines. This is common in Apple's datasets.
Determines if a file is a concatenated CSV file by checking if it 
contains multiple sections separated by titles and newlines.
"""       


class CSVMulti_Handler(FormatHandler):

    def __init__(self, **args):
        super().__init__()
        # TODO
    

    def _validate_filetype(s: str, path: str):
        
        pattern = re.compile(r'^[^\n",]*(\n\s*){2,}[^\n",]*', re.MULTILINE)
        match = pattern.search(s)
        if match:
            return True
        if path is not None:
            if "iCloudUsageData" in path:
                return True
        return False
        