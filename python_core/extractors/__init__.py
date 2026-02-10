from .json_ import JSONParser
from .jsonl_ import JSONLParser
from .csv_ import CSVParser

REGISTRY = {
    'json': JSONParser,
    'jsonl': JSONLParser,
    'csv': CSVParser,
    # alias
    'json_label_values': JSONParser # TODO
}

def get_parser(fmt: str):
    return REGISTRY.get(fmt, JSONParser)()
