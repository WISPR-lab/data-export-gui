# LEStrADE 
**L**ocal **E**ngine for **Str**uctured **A**nalysis of **D**ata **E**xports (named after the minor Sherlock Holmes character, [Inspector Lestrade](https://en.wikipedia.org/wiki/Inspector_Lestrade)) is an open-source visualization tool that helps users understand their account security history using data exports from online platforms.

Instead of uploading user data files to a server, this project processes everything locally in the browser using Pyodide, a port of CPython to WebAssembly that runs a full Python environment in the web browser.

The Vue frontend is forked and heavily modified from Google's [Timesketch](https://timesketch.org/), specifically the `timesketch/frontend-ng` ([link](https://github.com/google/timesketch/tree/master/timesketch/frontend-ng)) directory. See the *License* section below.

This repository _also_ includes evaluation scripts (`evaluation/entity_resolution/` and `evaluation/efficiency/`) for measuring:
- **Device Entity Resolution**: how well the **Device Entity Resolution** pipeline (see `python_core/device_grouping2/`) determines if two authentication or session records originate from the same identity.
- **Efficiency & Scalability**: how the pipeline's timing and memory usage scale as data volume increases (via augmented datasets at 1x, 10x, 100x, 1000x).

The datasets are large and these scripts are unnecessary if you only want to explore the web application. See [_Performance Logging & Efficiency Evaluation_](#performance-logging--efficiency-evaluation) and [_Device Entity Resolution_ Evaluation](#device-entity-resolution-evaluation) below.

## Quickstart (Web App)

You can either visit a hosted version of the static LEStrADE site at https://wispr-lab.github.io/data-export-gui/, or run it locally on your own machine. To do the latter:

### Clone & Initialize Submodules (Required)
This project relies on Git submodules for user-agent parsing. You **must** initialize them first:
```bash
git clone --recurse-submodules https://github.com/WISPR-lab/data-export-gui/
# or if already cloned:
git submodule update --init --recursive
```

### With Docker
**Prerequisites**: [Docker](https://www.docker.com/products/cli/) or [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running. 

```bash
docker compose up --build web
```
The web application will be live at `http://localhost:5001`.

### Without Docker
**Prerequisites**:
* Node.js 22+ with [Yarn v1](https://classic.yarnpkg.com/en/docs/install/)
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

## Performance Logging & Efficiency Evaluation

The pipeline logs timing (duration, rows, DB calls per stage) on every run, printed as JSON to
the console and downloaded as `<filename>_mem_perf.csv`. Column/field meanings are documented
inline in `python_core/performance.py` and `webapp/src/utils/performanceExport.js` — read those,
not this file, for the current schema.

Memory sampling (JS heap + WASM heap, per stage) is optional — set `PERFORMANCE_MEMORY_SAMPLING=1`
**before** `sync_assets.sh` runs (i.e. before `yarn serve`/`yarn build`):
```bash
PERFORMANCE_MEMORY_SAMPLING=1 yarn serve
```

### Using Data for Efficiency Evaluation

1. **Generate augmented datasets** (if testing scalability):
   ```bash
   uv run python -m evaluation.efficiency.augment --platform facebook --multiplier 100
   uv run python -m evaluation.efficiency.augment --platform google --multiplier 1000
   ```

2. **Run pipeline with timing/memory profiling enabled** and upload augmented ZIP files through the web UI.

3. **Analyze the downloaded CSV** to measure:
   - How time/memory scale with data size (1x vs 10x vs 100x vs 1000x)
   - Which stages are performance bottlenecks
   - Peak memory usage per stage

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


---


## _Device Entity Resolution_ Evaluation

This is optional and requires substantial disk and memory resources; skip it if you only want to run the web app. (todo better explanation)

### Datasets

| Name | Short citation | URL | # records | Compressed size at download | Uncompressed dataset size |
|---|---:|---|---:|---:|---:|
| FP Stalker | [Vastel et al., 2018](https://inria.hal.science/hal-01652021/document) | https://github.com/Spirals-Team/FPStalker <br/> (extension1.txt.tar.gz and extension2.txt.tar.gz)| 15K| 137 MB | ~260 MB| 
| RBA Logins | [Wiefling et al., 2022](https://dl.acm.org/doi/10.1145/3546069) | https://zenodo.org/records/6782156 | ~33M | 1.1 GB | 9.1 GB |

### Docker Configuration

Running outside of Docker is not recommended. You must change your Docker/VM settings to ensure you have sufficient disk space and memory available. 

#### Resource Settings
* **Absolute Minimum**: 4 GB RAM, 15 GB free disk space.
   * This might crash and will be significantly less efficient.
* **Recommended**: 8 GB RAM, 25 GB free disk space.


#### Mac/Windows users
* If you are running **Docker Desktop** (most users), follow [these instructions](https://docs.docker.com/desktop/settings-and-maintenance/settings/#resources) to change your `Memory limit` and `Disk usage limit` to the settings specified above.
* If you are using a different VM, use the instructions below:
   * [Colima](https://github.com/abiosoft/colima#customizing-the-vm)
   * [OrbStack](https://docs.orbstack.dev/settings#cpu-memory)
   * [WSL](https://learn.microsoft.com/en-us/windows/wsl/wsl-config#configuration-setting-for-wslconfig)


#### Linux users
* If you are _not_ using a VM to run Docker, proceed (but add the `--memory="8g"` flag").
* If you are using a VM, ensure disk/memory limits meet the requirments. But you probably already know how to do that...

  

### Run Instructions

1. **Start the container**:

   ```bash
      # from data-export-gui dir
      mkdir -p evaluation/entity_resolution/data_raw
      
      # mac/windows OR linux with VM
      docker compose run --rm eval

      # if linux w/o VM
      docker compose run --rm eval --memory="8g" # or "4g", etc.
   ```
   This will put you in an interactive bash session inside the container (at `/workspace`). The raw datasets will be downloaded to Docker named volume (`data_raw`) mounted at `evaluation/entity_resolution/data_raw` to speed up the SQLite writes.


2. Inside the container shell, **download data and run evaluation**:
   ```bash
   uv run python -m evaluation.entity_resolution.run

   # Draw K tracking_ids active within a random 30-day timestamp window:
   uv run python -m evaluation.entity_resolution.run --window-days 30
   ```


--- 

## Contributing

Feel free to submit UI bugs under Issues or post there if you're interested in contributing to the project.
To add support for a new platform (or augment supported keys for an existing one), follow the instructions in the [Manifests Schema Guide](manifests/README.md). 

### Repository Structure                                                                                                                                                                                                                    
* **`webapp/`**: Vue 2 / Vuetify frontend (modified Google Timesketch derivative).
* **`python_core/`**: Python parsing and database logic (runs inside Pyodide in the browser).
* **`manifests/`**: Platform YAML configurations defining mappings to ECS.
* **`evaluation/`**: Academic paper replication package, figure scripts, and `evaluation/entity_resolution/`.
* **`schema.sql`**: SQLite database schema. Both JS and Pyodide read/write to this DB, but never at the same time.
* **`tests/`**: Vitest (JS) and Pytest (Python) integration tests.

### Pyodide Flow
1. Vue worker downloads Pyodide WASM + package wheels (pandas, regex, sqlite3) on load.
2. After the user imports their data export ZIP file in the UI, it is unzipped locally by JS and files are written to the [Origin Private File System (OPFS)](https://developer.mozilla.org/en-US/docs/Web/API/File_System_API/Origin_private_file_system)
3. Python (`python_core/`) parses the data into a standard representation defined by the YAML schemas in `manifests/`.
4. Python saves normalized rows to a WASM SQLite database synced to OPFS defined by `schema.sql`.
5. Vue queries the local SQLite DB to render views.

### Unit testing

If you make changes to the `python_core` logic and would like to run unit tests, run
```bash
# via Docker
docker compose run --rm test tests/python  # all python tests
docker compose run --rm test tests/python/test_device_grouping2.py # or a specific test

# without Docker
uv sync
uv run pytest tests/python # all python test
uv run pytest tests/python/test_device_grouping2.py # or a specific test
```

## License

This repository uses multiple licenses to protect different components. See `LICENSE` for more details.
