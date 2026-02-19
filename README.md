# Takeout Tool

Data timeline exploration tool for Google Takeout and other social media archives, forked and heavily modified from Google's [Timesketch](https://timesketch.org/).

Instead of uploading sensitive files to a server, this project processes everything locally by outsourcing parsing to Pyodide, a port of CPython to WebAssembly that runs a full Python environment to the web browser.



## Quickstart

**Prerequisites**
- Node.js 18+
- yarn

**Setup**

```bash
cd webapp
yarn install
yarn serve
```

The frontend usually runs on `http://localhost:5001`

## Architecture

1. UI (JavaScript): The user selects a platform (e.g., Facebook) and drops a ZIP file into the browser.

2. Unzip (JavaScript): JS unzips the uploaded file in local browser storage and discards files not mentioned in the platform schemas.

3. Parsing engine (Python/Pyodide): JavaScript passes each remaining file string AND the schema YAML to the functions in `pyparser/`. Python handles all the data cleaning and field name standardization.

> **Note**: The `pyparser` logic is developed in the root directory and `pyodide-worker.js` in `webapp/src/`, but they are automatically synced to `webapp/public/` when the development server or build runs to bypass legacy build limitations. #TODO UPDATE

4. Storage (Dexie.js/IndexedDB): Python/Pyodide passes "rows" of data in JSON back to Java Script. This is saved into a searchable database (IndexedDB) with a Dexie.js wrapper.

5. UI (JavaScript): UI elements are rendered from the local DB.

The way I like to think about it, the Python/Pyodide engine pretends to be the "server" in the classic client-server model, even though the data doesn't leave the local machine.


## Understanding and writing new schema


The platform YAML files in `manifests/` (i.e., `apple.yaml`) provide instructions for the Python engine to map data exports into (a slightly modified version of) the Elastic Common Schema (ECS). The goal of this is to minimize how much of the Python engine in `python_core` we have to rewrite if we want to add support for a new platform or if the platforms change file formats. 


A manifest has two main sections:

1. `files`:  physical files to parse (inputs)
2. `views`: specs for the logical events/states extracted from those files (outputs).



### (1) File Sources

Define the physical file once, even if it contains multiple types of events.

```yaml
files:
  - id: "insta_devices"                 # Unique reference ID        
    path: "path/to/devices.json"        # Relative path in the ZIP
    parser:
      format: "json"
      json_root: "devices_devices[]"
      drop_duplicates:                  # optional deduplication, follows pandas conventions
        subset: ["Device ID"]
        keep: "last"
  - id: ....
```


The attributes under `parser:` describe the shape of the file and how the engine should parse it.

- `format`:
    - `json`: standard JSON, ok for nested dictionaries within dictionaries, but not nested lists.
    - `json_label_values`: Special Meta format where data is stored in lists of `{label: "Key", value: "Val"}`.
    - `jsonl`: newline delimited JSON format, common in Discord
    - `csv`
    - `csv_multi`: a very odd file that contains multiple CSV sections separated by titles and newlines, common in Apple

- `json_root`: (json/json_label_values/jsonl only; optional): The path to the list of objects you want to parse. Use [] to denote a list (e.g., `account_activity_v2[]`).
- `drop_duplicates`: (optional) logic to clean data at the source level. Follows pandas conventions. Requires:
    - `subset`: list of columns to check
    - `keep`: `first`, `last`, or `row_completeness` (keep the row with the most non-null row entries)



### (2) Views

A `view` defines how to transform a source into a strem of events/states (vaguely using ECS conventions). You can have multiple views for a single source (e.g., one for "Logins" and one for "Logouts").

```yaml
views:
  - file: 
      id: "insta_devices"           # Must match a file ID
      where: {source: "status", op: "==", value: "active"}.  # Filtering (optional) only rows that match this condition

    # hardcoded ECS values for every event in this view.
    static:
      event.kind: "asset"                           # 'event' (action) or 'asset' (state)
      event.category: ["authentication", "host"]    # follow ECS conventions
      event.type: ["info"]                          # follow ECS conventions
      entity.type: "authenticated_device"
    
    # dynamic mappings
    fields:
      - {target: "entity.last_seen_timestamp", source: "'Last Login'.timestamp", type: "datetime"}
      - {target: "user_agent.original", source: "'User Agent'.value", type: "string"}
```

#### file attributes:
- `where` selects only rows that match this condition
    - Simple: i.e., `{source: "event_type", op: "==", value: "login"}`
    - Complex: Uses logic: any or all with a conditions list. 
        - Supports operators: `==`, `startswith`, `contains`, `endswith`, `!=`. 
        - Add more supported operators in `webapp/src/pyparser/base.py`.

#### path traversal for source keys
JSON (and jsonl) source fields support path traversal for nested dictionaries via dot notation and bracket notation. Use single quotes for keys containing spaces, e.g.:
- `session.ip_address`
- `'Device ID details'.first_seen_time`
- `push_tokens[0].id`: Gets the id of the first item in the list.

#### Static attributes:
hardcoded ECS (Elastic Common Schema) values for every event in this view.
- `event.kind`
    - `event`: points in time (Logins, Messages, Clicks).
    - `asset`: inventory items (Devices, Contacts). use this for "State" snapshots.
        - for asset rows, map specific entity identifiers (see Custom Fields below).


#### Dynamic field mappings:
Every very item must have `target` (the standardized ECS field name) and a `source` (the raw data key in the file), and optionally a `type` and `transform`. Path traversal for `source` fields follows conventions above. 

If transform is set to "coalesce" (or if source is a list), the engine will pick the first non-null value.
- e.g., `{ ... source: ["push_tokens[0].id", "family_id"], transform: "coalesce"}`




#### Custom ECS Fields currently used
ECS isn't really built for this use case, so we have a couple of custom fields that we're consistently using at the moment

- `device.id.[platform]`: internal device fingerprint (not user ID) for a specific platform
- `device.given_name`: user-defined nickname for device (e.g., "Bob's iPhone"), common in Apple
- `device.imei`: International Mobile Equipment Identity
- `device.meid`: Mobile Equipment Identifier
- `entity.type`: for assets. use value `"authenticated_device"` for trusted device lists
- `entity.[first/last]_seen_timestamp`: for assets, instead of `@timestamp`



