# LEStrADE 
**L**ocal **E**ngine for **Str**uctured **A**nalysis of **D**ata **E**xports (named after the minor Sherlock Holmes character, [Inspector Lestrade](https://en.wikipedia.org/wiki/Inspector_Lestrade)) is an open-source visualization tool that helps users understand their account security history using data exports from online platforms.

Instead of uploading user data files to a server, this project processes everything locally in the browser using, a port of CPython to WebAssembly that runs a full Python environment to the web browser.

The Vue frontend is forked and heavily modified from Google's [Timesketch](https://timesketch.org/), specifically the `timesketch/frontend-ng` ([link](https://github.com/google/timesketch/tree/master/timesketch/frontend-ng)) directory. See the *License* section below.

## Quickstart

You can either visit a hosted version of the static site at https://wispr-lab.github.io/data-export-gui/, or set it up on your own machine.

### Clone & Initialize Submodules (Required)
This project relies on Git submodules for user-agent parsing. You **must** initialize them first:
```bash
git clone --recurse-submodules https://github.com/WISPR-lab/data-export-gui/
# or if already cloned:
git submodule update --init --recursive
```

---
Finish the setup either with or without Docker:

### With Docker
**Prerequisites**: [Docker](https://www.docker.com/products/cli/) or [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running.

1. **Build and start the application**:
   ```bash
   docker compose up --build
   ```
   The web application will be live at `http://localhost:5001`.

2. **Run Python integration tests**:
   ```bash
   docker compose run --rm test

   # or run specific tests
   docker compose run --rm test tests/python/test_device_grouping2.py
   docker compose run --rm test tests/python/test_device_grouping2.py::test_group_pipeline_outputs
   ```

---

### Without Docker
**Prerequisites**:
* Node.js 18+ with [Yarn v1](https://classic.yarnpkg.com/en/docs/install/)
* Python 3.12+ (standard CPython)
* uv (`brew install uv` or `pip install uv`)

1. **Install and run local version of the web app**:
   ```bash
   cd webapp
   yarn install
   yarn serve
   ```
   Under the hood, this runs `sync_assets.sh` which automatically builds the `UA-Extract-purepy` wheel using `uv`.
   The frontend runs at `http://localhost:5001`.

2. **Install Python dependencies and run tests**:
   ```bash
   # from repo root, not /webapp
   uv sync

   # run all tests
   uv run pytest tests/python 

   # or run specific tests
   uv run pytest tests/python/test_device_grouping2.py
   uv run pytest tests/python/test_device_grouping2.py::test_group_pipeline_outputs
   ```

3. **Sync dependency updates to Pyodide**:
   If you change dependencies inside `pyproject.toml`, update `requirements.txt` to keep the in-browser Pyodide runtime in lockstep:
   ```bash
   uv pip compile pyproject.toml -o python_core/requirements.txt --no-header
   ```

## Architecture

To protect user privacy, this tool does not upload user's data files to a server. Instead, it runs a Python environment that processes the database directly inside the browser using **Pyodide** (a port of CPython and its packages to WebAssembly).
It's probably overcomplicated architecture but I couldn't bear writing a parser in JS... 

## Repository Structure                                                                                                                                                                                                                    
* **`webapp/`**: Vue 2 / Vuetify frontend with some JS utility files.                                                                                                                                      
* **`python_core/`**: Python parsing and database logic (runs inside Pyodide in the browser).                                                                                                                                              
* **`manifests/`**: Platform YAML configurations defining mappings to ECS.                                                                                                                                                                 
* **`schema.sql`**: SQLite database schema. Both JS and Pyodide read/write to this DB, but never at the same time.                                                                                                                                                                                               
* **`tests/`**: Vitest (JS) and Pytest (Python) integration tests.

### Pyodide Flow
1. Vue worker downloads Pyodide WASM + package wheels (pandas, regex, sqlite3) on load.
2. After the user imports their data export ZIP file in the UI, it is unzipped locally by JS and files are written to the [Origin Private File System (OPFS)](https://developer.mozilla.org/en-US/docs/Web/API/File_System_API/Origin_private_file_system)
3. Python (`python_core/`) parses the data into a standard representation defined by the YAML schemas in `manifests/`.
4. Python saves normalized rows to a WASM SQLite database synced to OPFS defined by `schema.sql`.
5. Vue queries the local SQLite DB to render views.


## Supported Platforms

Currently, the tool includes parsing manifests for:
* Google - *Fully Supported*
* Apple/iCloud - *Fully Supported*

We are working on support for:
* Facebook - *Beta*
* Instagram - *Beta*
* Discord - *Beta*
* Snapchat - *Beta*

For instructions on how to request your data exports, see the [How to Request Data Guide on our hosted site](https://wispr-lab.github.io/data-export-gui/#/how-to-request) (or `http://localhost:5001/#/how-to-request` when running locally). 
We'll put some anonymized sample data up soon.


## Security & Privacy

When you import your data export file, it is never transmitted over the network; all unzipping, parsing, and database transactions happen entirely inside your local browser sandbox. The codebase does not make external API requests containing your data (such as querying a remote service to parse User Agents or geolocate IP addresses).

Note that the [site](https://wispr-lab.github.io/data-export-gui/) is hosted via GitHub Pages, which may collect connection logs or track cookies. Furthermore, the Vue app currently loads some CSS assets and Pyodide package wheels from public CDNs, which implies an outbound network request. We are working on bundling these assets from the source and self-hosting our own version of the project soon with better privacy guarantees.

## Contributing

Feel free to submit UI bugs under Issues or post there if you're interested in contributing to the project.
To add support for a new platform (or augment supported keys for an existing one), follow the instructions in the [Manifests Schema Guide](manifests/README.md). 


## License

The Vue frontend is forked and heavily modified from Google's [Timesketch](https://timesketch.org/), specifically the `timesketch/frontend-ng` ([link](https://github.com/google/timesketch/tree/master/timesketch/frontend-ng)) directory., which is licensed under the Apache License 2.0. Files that have been modified from the original repository have been documented as such. This project, too, is protected by the same license. See [LICENSE](LICENSE) for details.

