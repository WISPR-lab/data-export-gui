import json as jsonlib
import hjson
import json5
import demjson3

class JSON_Handler(object):

    def __init__(self):
        super().__init__()

    def batch():
        pass

    
    def parse_str(s: str):
        pass # TODO
        


    def str_to_jsonobj(s: str):
        robust_parsing_methods = [
            lambda s_: jsonlib.loads(s_),  # Standard JSON
            lambda s_: jsonlib.loads(s_.replace("'", '"')),  # Convert single quotes
            lambda s_: demjson3.decode(s_, strict=False, allow_trailing_comma=True),  # Lenient parsing
            lambda s_: json5.loads(s_),  # ES5-style parsing
            lambda s_: hjson.loads(s_, use_decimal=True, object_pairs_hook=dict)
        ]

        for _, method in enumerate(robust_parsing_methods):
            try:
                jsonobj = method(s)
                break
            except Exception as e:
                continue
        if jsonobj is None:
            raise RuntimeError("unable to parse") # TODO custom err
        return jsonobj
            

    def _validate_format():
        pass