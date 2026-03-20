from .json_ import JSONParser
from .jsonl_ import JSONLParser
from .csv_ import CSVParser
from .csv_multi import CSVMultiParser
from .json_label_values import JSONLabelValuesParser
from .html_table import HTMLTableParser

REGISTRY = {
    'json': JSONParser,
    'jsonl': JSONLParser,
    'csv': CSVParser,
    'csv_multi': CSVMultiParser,
    'json_label_values': JSONLabelValuesParser,
    'html': HTMLTableParser,
    'html_table': HTMLTableParser,
    'html_ggl_myactivity': HTMLTableParser,
}

def get_parser(fmt: str):
    return REGISTRY.get(fmt, JSONParser)()
