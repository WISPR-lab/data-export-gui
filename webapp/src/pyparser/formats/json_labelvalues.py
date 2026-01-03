from .json_ import JSON_Handler

TRIVIAL = lambda x: (x is None) \
    or (isinstance(x, str) and x.strip() == "") \
    or (x == []) \
    or (isinstance(x, list) and all((e == "" or e is None or e == []) for e in x))

VALUE_KEYS = ["value", "timestamp_value", "vec", "dict"]


class JSONLabelValues_Handler(JSON_Handler):

    def __init__(self):
        super().__init__()

    def batch():
        pass

    @override
    def parse_str(self, s: str):
        
        jsonobj = self.str_to_jsonobj()


    def flatten_lv(self, jsonobj: dict | list):
        if isinstance(jsonobj, dict):
            lv_list = jsonobj.get("label_values", None)
            if lv_list is None:
                return jsonobj
            return self._parse_lv_dict(lv_list)
        
        if isinstance(jsonobj, list):
            res = []
            for e in jsonobj:
                if TRIVIAL(e):
                    continue
                if isinstance(e, dict):
                    lv_list = e.get("label_values")
                    if lv_list is not None:
                        res.append(self._parse_lv_dict(lv_list))
                        continue
                res.append({"PARSER_INVALID_DATA": str(e)})
            return res



    def _parse_lv_dict(self, l: list):
        """
        l = [
            { "label": "Something", "value": "12345"}, ...
        ]

        --> { "Something": "12345", ... }
        """
        if TRIVIAL(l):
            return ""
        if not isinstance(l, list):
            return str(l)
        
        label_num = 0
        
        res = {}
        for e in l:
            if TRIVIAL(e):
                continue
            if not isinstance(e, dict) \
            or ("label" not in e.keys() and "title" not in e.keys()):
                if "timestamp_value" in e:
                    res.update({"timestamp_value": e.get("timestamp_value")})
                else:
                    res.update({"PARSER_INVALID_DATA": str(e)})
                continue

            key = e.get("label", key = e.get("title", ""))
            if key == "":
                key = f"UNNAMED_LABEL_{label_num}"
                label_num += 1
            
            if key in res and (not TRIVIAL(res[key])):
                continue # label value already in dict and has nontrivial value

            if "dict" in e:
                res[key] = self._parse_lv_dict(e["dict"])
            elif "vec" in e:
                res[key] = self._parse_lv_list(e["vec"])
            elif "timestamp_value" in e:
                res[key] = self._parse_value(e["timestamp_value"])
            else: 
                res[key] = self._parse_value(e.get("value", ""))

            if TRIVIAL(res[key]):
                res[key] = ""
        
        
        if all(k.startswith("UNNAMED_LABEL_") for k in res.keys()):
            res = list(res.values())
        
        return res
       


    def _parse_lv_list(self, lv_list: list):
        res = []
        if not isinstance(lv_list, list) or len(lv_list) == 0:
            return res
        for e in lv_list:
            if isinstance(e, dict) and len(e) > 0:
                if "dict" in e:
                    vf = self._parse_lv_dict(e["dict"])
                elif "vec" in e:
                    vf = self._parse_lv_list(e["vec"])
                elif "timestamp_value" in e:
                    vf =self._parse_value(e["timestamp_value"])
                else: # "value" in d.keys():
                    vf = self._parse_value(e.get("value", ""))
                res.append(vf)
            elif TRIVIAL(e):
                res.append("")
            else:
                res.append(self._parse_value(e))
        
        if TRIVIAL(res):
            return ""
        return res


    def _parse_value(self, v):
        if TRIVIAL(v):
            return ""
        if isinstance(v, list):
            return self._parse_lv_list(v)
        if isinstance(v, dict):
            return self._parse_lv_dict(v)
        
        try:
            return int(v)
        except:
            pass 
        try:
            return float(v)
        except:
            pass
        return str(v)
  
 


        
