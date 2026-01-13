from .json_ import JSONParser

class JSONLParser(JSONParser):
        

    @classmethod
    def str_to_json(cls, s: str):
        dicts = []
        for line in s.split("\n"):
            if len(line.strip()) == 0:
                continue
            dicts.append(cls.basic_str_to_json(line))
        return dicts