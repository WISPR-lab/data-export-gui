import sys
import json
import os

# Add the project root to sys.path so we can import modules correctly
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)
sys.path.append(os.path.join(project_root, 'pyparser'))

from pyparser.pyodide import parse

def main():
    try:
        # Read the request from stdin
        request_raw = sys.stdin.read()
        if not request_raw:
            return
            
        request = json.loads(request_raw)
        
        schema_str = request.get('schema_str')
        file_content = request.get('file_content')
        filename = request.get('filename')
        
        # Run the actual parser logic
        result = parse(schema_str, file_content, filename)
        
        # Print the result as JSON
        print(json.dumps(result))
    except Exception as e:
        print(json.dumps({
            "events": [],
            "states": [],
            "fatal": True,
            "errors": [{"msg": f"Python Bridge Error: {str(e)}"}]
        }))

if __name__ == "__main__":
    main()
