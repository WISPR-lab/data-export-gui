# --------- group schema by path --------- #

"""

transforms a schema yaml dict into a dict grouped by file path

example: {
    
    "security_and_login_information/account_activity.json" : [
        { 
            "temporal": "event", 
            "category": "auth.pwd.change", 
            "parser": {....},
            "fields": [ {name: ..., source: ..., type: ...}, ... ]
        }, ...
    ],
    ...
}

"""

def group_by_file(schema_yaml):
    res = {} 
    errors = []
    for dtype in schema_yaml.get('data_types', []):
        for file in dtype.get('files', []):
            
            if not isinstance(file, dict):
                errors.append(f"Invalid file entry in schema: {str(file)}")
                continue
            
            path = file.get('path')
            if path is None:
                errors.append(f"File entry has no path: {str(file)}")
                continue
            if path not in res:
                res[path] = []
            
            path_info = {
                'temporal': dtype.get('temporal', ""), 
                'category': dtype.get('category', ""),
                'parser': file.get('parser', {}),
                'fields': file.get('fields', []),
            }
            res[path].append(path_info)
    return res, errors