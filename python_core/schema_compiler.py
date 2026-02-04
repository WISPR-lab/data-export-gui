import json
import sqlite3

class SchemaCompiler:
    def __init__(self):
        pass

    def compile_views(self, conn, yaml_configs):
        """
        Generates and executes SQL CREATE VIEW statements based on YAML configs.
        
        Args:
            conn: SQLite connection object
            yaml_configs: List of dicts (parsed YAML content)
        """
        print("[SchemaCompiler] Compiling Views...")
        
        for config in yaml_configs:
            schema_id = config.get('id')
            if not schema_id:
                continue

            print(f"[SchemaCompiler] Processing schema: {schema_id}")
            
            for dt in config.get('data_types', []):
                category = dt.get('category')
                if not category:
                    continue
                
                # View Name: view_<vendor>_<category>
                # Sanitize category for SQL (dots to underscores)
                safe_cat = category.replace('.', '_')
                view_name = f"view_{schema_id}_{safe_cat}"
                
                # Build Select Columns
                select_parts = []
                
                # 1. Add ID and source metadata
                select_parts.append("id")
                select_parts.append("source_file")
                select_parts.append(f"'{category}' AS \"event.category\"") # Static ECS field
                
                # 2. Add Mapped Fields
                # Generate: json_extract(raw_data, '$."<Source>"') AS "<Target>"
                for field in dt.get('fields', []):
                    source = field.get('source')
                    target = field.get('name')
                    
                    if not source or not target:
                        continue
                        
                    # Handle source path (simple check for now, can be complex path)
                    # If source contains dots but is not quoted, we might need to be careful?
                    # The prompt example: '$."Logged In Date"'
                    # We will quote the source key to handle spaces and special chars.
                    
                    # If source is a list (coalesce), for now picking first or skipping?
                    # Prompt says: "Iterate the fields list... Generate json_extract..."
                    # Does not mention coalesce. I'll stick to string source for now.
                    if isinstance(source, list):
                        # Fallback: just use the first one or ignore
                         source = source[0]
                    
                    # Escape double quotes in source key if necessary
                    safe_source = source.replace('"', '\\"')
                    
                    # SQL Expression
                    expr = f"json_extract(raw_data, '$.\"{safe_source}\"')"
                    
                    # Target column name (quoted)
                    col_def = f"{expr} AS \"{target}\""
                    select_parts.append(col_def)

                # 3. Build WHERE Clause
                # Filter by adapter_type (Schema ID)
                where_clauses = [f"adapter_type = '{schema_id}'"]
                
                # Filter by source files (Important for differentiating categories within same vendor)
                file_paths = [f.get('path') for f in dt.get('files', []) if f.get('path')]
                if file_paths:
                    # Construct LIKE clauses for file paths (suffix match as per earlier logic)
                    file_checks = []
                    for path in file_paths:
                        # Use ending match pattern
                        # Escape single quotes in path
                        safe_path = path.replace("'", "''") 
                        file_checks.append(f"source_file LIKE '%{safe_path}'")
                    
                    if file_checks:
                         where_clauses.append(f"({' OR '.join(file_checks)})")

                # Combine SQL
                select_sql = ",\n    ".join(select_parts)
                where_sql = " AND ".join(where_clauses)
                
                create_view_sql = f"""
                CREATE VIEW IF NOT EXISTS "{view_name}" AS
                SELECT
                    {select_sql}
                FROM raw_events
                WHERE {where_sql};
                """
                
                try:
                    conn.execute("DROP VIEW IF EXISTS \"{}\"".format(view_name)) # Recreate view
                    conn.execute(create_view_sql)
                    print(f"[SchemaCompiler] Created View: {view_name}")
                except Exception as e:
                    print(f"[SchemaCompiler] Failed to create view {view_name}: {e}")
                    # print(create_view_sql) # Debug

        conn.commit()
        print("[SchemaCompiler] View Compilation Complete.")
