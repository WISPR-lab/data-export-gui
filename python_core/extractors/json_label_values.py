from .json_ import JSONParser
from errors import RecordLevelError
from typing import List, Dict, Any, Optional

class JSONLabelValuesParser(JSONParser):

    @classmethod
    def extract(cls, content: str, config: Optional[Dict] = None) -> List[Dict[str, Any]]:
        config = config or {}
        try:
            
            raw_json = cls.basic_str_to_json(content) # this is inherited
            flat_json = cls._flatten_lv(raw_json)
            data = cls._resolve_root(flat_json, config)
            
            if isinstance(data, list):
                return [x for x in data if isinstance(x, dict)]
            elif isinstance(data, dict):
                return [data]
            return []
        except Exception as e: #TODO ERROR HANDLING
            return [RecordLevelError(f"File-level parsing error: {str(e)}", 
                                     context={'error_type': type(e).__name__})]


    @classmethod
    def str_to_json(cls, s: str) -> str:
        # differs between inherited classes
        # Returns (flat_json, errors) tuple
        try:
            raw_json = cls.basic_str_to_json(s) # this is inherited
            flat_json = cls._flatten_lv(raw_json)
            return flat_json, []
        except Exception as e:
            return [], [RecordLevelError(f"Label-values parsing error: {str(e)}", 
                                         context={'error_type': type(e).__name__})]


    @classmethod
    def _flatten_lv(cls, jsonobj: dict | list):
        if isinstance(jsonobj, dict):
            lv_list = jsonobj.get("label_values", None)
            if lv_list is None:
                return jsonobj
            return cls._flatten_lv_dict(lv_list)
        
        if isinstance(jsonobj, list):
            res = []
            for e in jsonobj:
                if cls._is_trivial(e):
                    continue
                if isinstance(e, dict):
                    lv_list = e.get("label_values")
                    if lv_list is not None:
                        dct = cls._flatten_lv_dict(lv_list)
                        ts = e.get("timestamp", None)
                        if not cls._is_trivial(ts):
                            dct.update({"timestamp": ts})
                        res.append(dct)
                        continue
                res.append({"PARSER_INVALID_DATA": str(e)})
            return res


    @classmethod
    def _flatten_lv_dict(cls, l: list):
        """
        l = [
            { "label": "Something", "value": "12345"}, ...
        ]

        --> { "Something": "12345", ... }
        """
        if cls._is_trivial(l):
            return ""
        if not isinstance(l, list):
            return str(l)
        
        label_num = 0
        
        res = {}
        for e in l:
            if cls._is_trivial(e):
                continue
            if not isinstance(e, dict) \
            or ("label" not in e.keys() and "title" not in e.keys()):
                if "timestamp_value" in e:
                    res.update({"timestamp_value": e.get("timestamp_value")})
                else:
                    res.update({"PARSER_INVALID_DATA": str(e)})
                continue

            key = e.get("label", e.get("title", ""))
            if key == "":
                key = f"UNNAMED_LABEL_{label_num}"
                label_num += 1
            
            if key in res and (not cls._is_trivial(res[key])):
                continue # label value already in dict and has nontrivial value

            res[key] = cls._get_val(e)
        
        if all(k.startswith("UNNAMED_LABEL_") for k in res.keys()):
            res = list(res.values())
        
        return res
       


    @classmethod
    def _flatten_lv_list(cls, lv_list: list):
        res = []
        if not isinstance(lv_list, list) or len(lv_list) == 0:
            return res
        for e in lv_list:
            if isinstance(e, dict) and len(e) > 0:
                res.append(cls._get_val(e))
            elif cls._is_trivial(e):
                res.append("")
            else:
                res.append(cls._flatten_val(e))
        
        if cls._is_trivial(res):
            return ""
        return res
    

    @classmethod
    def _get_val(cls, e: dict):
        val = ""
        if "dict" in e:
            val = cls._flatten_lv_dict(e["dict"])
        elif "vec" in e:
            val = cls._flatten_lv_list(e["vec"])
        elif "timestamp_value" in e:
            val = cls._flatten_val(e["timestamp_value"])
        else: # "value" in d.keys():
            val = cls._flatten_val(e.get("value", ""))
        if cls._is_trivial(val):
            val = ""
        return val



    @classmethod
    def _flatten_val(cls, v):
        if cls._is_trivial(v):
            return ""
        if isinstance(v, list):
            return cls._flatten_lv_list(v)
        if isinstance(v, dict):
            return cls._flatten_lv_dict(v)
        
        try:
            return int(v)
        except:
            pass 
        try:
            return float(v)
        except:
            pass
        return str(v)
  
 


        
