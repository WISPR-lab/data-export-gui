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

> **Note**: The `pyparser` logic is developed in the root directory and `pyodideWorker.js` in `webapp/src/`, but they are automatically synced to `webapp/public/` when the development server or build runs to bypass legacy build limitations.

4. Storage (Dexie.js/IndexedDB): Python/Pyodide passes "rows" of data in JSON back to Java Script. This is saved into a searchable database (IndexedDB) with a Dexie.js wrapper.

5. UI (JavaScript): UI elements are rendered from the local DB.

The way I like to think about it, the Python/Pyodide engine pretends to be the "server" in the classic client-server model, even though the data doesn't leave the local machine.


## Understanding and writing new schema

The YAML files in `schemas/` provide instructions for the Python engine. The goal of this is to minimize how much of the Python engine in `pyparser` we have to rewrite if we want to add support for a new platform or if the platforms change file formats. 

Under `data_types` is a list of every "type" of event or state (i.e., login events, sent message events, all trusted devices) present in the whole ZIP data export 
*TODO DEFINE THIS BETTER*

- `temporal` must be `event` (point in time) or `state` (persistent status/settings)
    - the primary timestamp associated with an event should be added to the `fields` section (see below) as
    `{name: "primary_timestamp", source: <ur timestamp key>, type: "datetime"}`
- `category` must be one of the `valid_categories` in `schemas/all_fields.yaml` where hierarchies are separated by `.`
- `files` must be a list 

The same type of event (i.e., trusted devices) might pop up across several files. For each file, add an entry to `files`. 

#### Parser block
The attributes under `file: parser:` describe the shape of the file and how the engine should parse it.

- `format`:
    - `json`: Standard JSON, ok for nested dictionaries within dictionaries, but not nested lists.
    - `json_label_values`: Special Meta format where data is stored in lists of `{label: "Key", value: "Val"}`.
    - `jsonl`: JSONL format, common in Discord
    - `csv`
    - `csv_multi`: a very odd file that contains multiple CSV sections separated by titles and newlines, common in Apple

- `json_root`: (`json`/`json_label_values`/`jsonl` only; optional): The path to the list of objects you want to parse. Use [] to denote a list (e.g., `account_activity_v2[]`).

- `filter`: A logic gate to discard irrelevant rows.
    - Simple: i.e., `{field: "event_type", op: "==", value: "login"}`
    - Complex: Uses `logic`: `any` or `all` with a conditions list. Supports operators: `==`, `startswith`, `contains`, `endswith`, `!=`. Add more supported operators in `webapp/src/pyparser/base.py`.

#### Fields block

The fields list defines the output schema. Every item must have a `name` (the clean/standardized database key; must be present in `schemas/all_fields.yaml`) and a `source` (the raw data key in the file), and optionally a `type` and `transform`.


JSON (and jsonl, json_label_values) `source` fields support path traversal for nested dictionaries via dot notation and . Use single quotes for keys containing spaces.
-  `session.ip_address` 
- `'Device ID details'.first_seen_time`

**Coalescing**
If `transform == "coalesce"` and `source` is a list of keys he engine will pick the first one from the data that isn't null. 

Example: `source: ["push_tokens[0].id", "family_id"]`
