# TODO abstract
from typing import Callable, List
from errors import ParseError, FileLevelError, RecordLevelError, FieldLevelError
from parseresult import ParseResult


class BaseParser(object):

    encoding = "utf-8"

    op_mapping = {
        "eq": ["==", "===", "=", "eq"],
        "ne": ["!=", "!==", "ne", "neq"],
        "contains": ["contains", "includes"],
        "startswith": ["startswith", "starts_with"],
        "endswith": ["endswith", "ends_with"]
    }



    @classmethod
    def _is_trivial(cls, x):
        return (x is None) \
            or (isinstance(x, str) and x.strip() == "") \
            or (x == []) \
            or (isinstance(x, list) and all((e == "" or e is None or e == []) for e in x))

    
    @classmethod
    def parse(cls, s: str, filename: str, cfg: List[dict], default="", **kwargs):
        pass
