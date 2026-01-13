import os
import sys
import yaml
import json
import argparse

# Add the project root to sys.path so we can import modules correctly
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(project_root)
sys.path.append(os.path.join(project_root, 'pyparser'))

from pyparser.pyodide import parse, group_schema_by_path

def test_single_file(schema_path, data_file_path, filename_in_schema):
    """
    Simulates the call that JS makes to the Python parser.
    """
    if not os.path.exists(schema_path):
        print(f"Error: Schema not found at {schema_path}")
        return
    
    if not os.path.exists(data_file_path):
        print(f"Error: Data file not found at {data_file_path}")
        return

    with open(schema_path, 'r') as f:
        schema_str = f.read()
    
    with open(data_file_path, 'r') as f:
        file_content = f.read()

    print(f"--- Testing {filename_in_schema} ---")
    result = parse(schema_str, file_content, filename_in_schema)
    
    print(json.dumps(result, indent=2))
    print(f"--- End of {filename_in_schema} ---\n")
    return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Test the Python parsing engine.')
    parser.add_argument('--platform', type=str, help='Platform name (e.g., facebook)')
    parser.add_argument('--file', type=str, help='Path to the raw extracted file to test')
    parser.add_argument('--schema_filename', type=str, help='The path string as defined in the manifest')

    args = parser.parse_args()

    # Default relative paths for the repo structure
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    schema_dir = os.path.join(repo_root, 'schemas')

    if args.platform and args.file and args.schema_filename:
        schema_path = os.path.join(schema_dir, f"{args.platform}.yaml")
        test_single_file(schema_path, args.file, args.schema_filename)
    else:
        print("Usage Example:")
        print("python3 tests/python/test_parser.py --platform facebook --file /path/to/extracted/account_activity.json --schema_filename security_and_login_information/account_activity.json")
