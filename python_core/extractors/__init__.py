from .json_ import JSONParser
from .jsonl_ import JSONLParser
from .csv_ import CSVParser
from .csv_multi import CSVMultiParser
from .json_label_values import JSONLabelValuesParser
from .html_table import HTMLTableParser, HTMLGglSubscriberInfoParser
from .html_ggl_myactivity import HTMLMyActvityParser

REGISTRY = {
    'json': JSONParser,
    'jsonl': JSONLParser,
    'csv': CSVParser,
    'csv_multi': CSVMultiParser,
    'json_label_values': JSONLabelValuesParser,
    'html': HTMLTableParser,
    'html_table': HTMLTableParser,
    'html_ggl_myactivity': HTMLMyActvityParser,
    'html_ggl_subscriber_info': HTMLGglSubscriberInfoParser,
}

def get_parser(fmt: str):
    return REGISTRY.get(fmt, JSONParser)()
