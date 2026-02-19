from .json_ import JSONParser
from .jsonl_ import JSONLParser
from .csv_ import CSVParser
from .csv_multi import CSVMultiParser
from .json_label_values import JSONLabelValuesParser

REGISTRY = {
    'json': JSONParser,
    'jsonl': JSONLParser,
    'csv': CSVParser,
    'csv_multi': CSVMultiParser,
    'json_label_values': JSONLabelValuesParser,
}

def get_parser(fmt: str):
    return REGISTRY.get(fmt, JSONParser)()
