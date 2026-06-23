# LEStrADE 
**L**ocal **E**ngine for **Str**uctured **A**nalysis of **D**ata **E**xports (named after the minor Sherlock Holmes character, [Inspector Lestrade](https://en.wikipedia.org/wiki/Inspector_Lestrade)) is an open-source visualization tool that helps users understand their account security history using data exports from online platforms.

Instead of uploading user data files to a server, this project processes everything locally in the browser using Pyodide, a port of CPython to WebAssembly that runs a full Python environment in the web browser.

The Vue frontend is forked and heavily modified from Google's [Timesketch](https://timesketch.org/), specifically the `timesketch/frontend-ng` ([link](https://github.com/google/timesketch/tree/master/timesketch/frontend-ng)) directory. See the *License* section below.

## Introduction

You can either visit a hosted version of the static LEStrADE site at https://wispr-lab.github.io/data-export-gui/, or run it locally on your own machine

This repository _also_ includes a set of evaluation scripts (`entity_resolution_evaluation/`) for measuring how well our **Device Entity Resolution** pipeline (see `python_core/device_grouping2/`) determines if two authentication or session records originate from the same identity. These scripts use two public datasets, FP Stalker and RBA TODO CITE, which together are very large (11GB+). It is unnecessary to download and run these scripts if you are interested in just exploring the web application. If you are interested in reproducing the results of this pipeline evaluation and have sufficient storage, go for it.



## Clone & Initialize Submodules (Required)
This project relies on Git submodules for user-agent parsing. You **must** initialize them first:
```bash
git clone --recurse-submodules https://github.com/WISPR-lab/data-export-gui/
# or if already cloned:
git submodule update --init --recursive
```

## Run Web App

You can visit the hosted version at https://wispr-lab.github.io/data-export-gui or run the app locally on your own machine.

### With Docker
**Prerequisites**: [Docker](https://www.docker.com/products/cli/) or [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running. 

```bash
docker compose up --build web
```
The web application will be live at `http://localhost:5001`.

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




## OPTIONAL: Run _Device Entity Resolution_ Evaluation Scripts

This is optional and requires substantial disk and memory resources; skip it if you only want to run the web app.

### Datasets

| Name | Short citation | URL | # records | Compressed size at download | Uncompressed dataset size |
|---|---:|---|---:|---:|---:|
| FP Stalker | [Vastel et al., 2018](https://inria.hal.science/hal-01652021/document) | https://github.com/Spirals-Team/FPStalker <br/> (extension1.txt.tar.gz and extension2.txt.tar.gz)| 15K| 137 MB | ~260 MB| 
| RBA Logins | [Wiefling et al., 2022](https://dl.acm.org/doi/10.1145/3546069) | https://zenodo.org/records/6782156 | ~33M | 1.1 GB | 9.1 GB |

### Docker & Hardware Configuration

Running these evaluation scripts outside of Docker is not recommended. You must configure Docker to allocate sufficient hardware resources to the container. If using Docker Desktop (macOS/Windows), go to **Settings > Resources** and adjust the limits.
* **Resource Requirements**:
  * **Absolute Minimum**: 4 GB RAM, 15 GB free disk space.
  * **Recommended**: 8+ GB RAM, 25 GB free disk space.

### Run Instructions

1. **Start the container**:
   ```bash
   mkdir -p entity_resolution_evaluation/data/{raw,normalized} && docker compose run --rm eval
   ```
   This will put you in an interactive bash session inside the container (at `/workspace`). The raw datasets will be downloaded to Docker named volume (`data_raw`) mounted at `entity_resolution_evaluation/data/raw` to speed up the SQLite writes.


2. Inside the container shell, **download the datasets**:
   ```bash
   python -m entity_resolution_evaluation.fetch_data
   ```
   *(Autodetects container RAM to tune chunk sizes. Override via `--ram <GB>` if needed).*

3. **Verify data**:
   ```bash
   ls -lh entity_resolution_evaluation/data/raw
   ```
   Ensure `rba.db` (~8–10 GB) and `fp_stalker.db` (~260 MB) exist.

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

The Vue frontend is forked and heavily modified from Google's [Timesketch](https://timesketch.org/), specifically the `timesketch/frontend-ng` ([link](https://github.com/google/timesketch/tree/master/timesketch/frontend-ng)) directory., which is licensed under the Apache License 2.0. Files that have been modified from the original repository have been documented as such. This project, too, is protected by the same license. See [LICENSE](LICENSE) for details.

