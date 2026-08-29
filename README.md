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

## Sample Data

You do not need your own data export to try the tool. Two exports are checked into this repository:

| File | Platform | Upload as |
|---|---|---|
| `evaluation/efficiency/data/google_original.zip` | Google Takeout | *Google* |
| `evaluation/efficiency/data/facebook_original.zip` | Facebook | *Facebook* |

Start the web app, click **Import**, choose the matching platform, and select the ZIP as-is. No unpacking
needed. The Google export exercises the fullest path through the pipeline: device registrations, session
history, and access-log activity); the Facebook export is smaller and is what the Beta manifest was written
against.

These are the same 1x archives the efficiency evaluation augments to 10x/100x/1000x, which is why they live
under `evaluation/`. See [`evaluation/README.md`](evaluation/README.md).

### Provenance & attribution

Both exports come from research accounts created for the study below, and are used here with permission.
They are not any real person's account data: the account identities are `*.researcher24@gmail.com`, and IP
addresses in the security and login records the tool parses are masked to the reserved `0.0.0.x` range.

> Julia Nonnenkamp, Naman Gupta, Abhimanyu Dev Gupta, and Rahul Chatterjee. 2025.
> **Hidden in Plain Bytes: Investigating Interpersonal Account Compromise with Data Exports.**
> In *Proceedings of the 2025 ACM SIGSAC Conference on Computer and Communications Security (CCS '25)*,
> Taipei, Taiwan. ACM, New York, NY, USA, 4304–4318. https://doi.org/10.1145/3719027.3765147

```bibtex
@inproceedings{nonnenkamp2025hidden,
  author    = {Nonnenkamp, Julia and Gupta, Naman and Gupta, Abhimanyu Dev and Chatterjee, Rahul},
  title     = {Hidden in Plain Bytes: Investigating Interpersonal Account Compromise with Data Exports},
  booktitle = {Proceedings of the 2025 ACM SIGSAC Conference on Computer and Communications Security},
  series    = {CCS '25},
  year      = {2025},
  pages     = {4304--4318},
  publisher = {Association for Computing Machinery},
  address   = {New York, NY, USA},
  location  = {Taipei, Taiwan},
  doi       = {10.1145/3719027.3765147},
  url       = {https://doi.org/10.1145/3719027.3765147}
}
```

If you use these sample exports in your own work, please cite the paper above.

## Evaluation

Evaluation scripts and instructions live in [`evaluation/README.md`](evaluation/README.md).



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
To try the tool without requesting your own export, see [_Sample Data_](#sample-data) above.


## Security & Privacy

When you import your data export file, it is never transmitted over the network; all unzipping, parsing, and database transactions happen entirely inside your local browser sandbox. The codebase does not make external API requests containing your data (such as querying a remote service to parse User Agents or geolocate IP addresses).

Note that the [site](https://wispr-lab.github.io/data-export-gui/) is hosted via GitHub Pages, which may collect connection logs or track cookies. Furthermore, the Vue app currently loads some CSS assets and Pyodide package wheels from public CDNs, which implies an outbound network request. We are working on bundling these assets from the source and self-hosting our own version of the project soon with better privacy guarantees.



## Contributing

Feel free to submit UI bugs under Issues or post there if you're interested in contributing to the project.
To add support for a new platform (or augment supported keys for an existing one), follow the instructions in the [Manifests Schema Guide](manifests/README.md), then validate your changes:
```bash
uv run python scripts/validate_manifests.py
```
This checks every manifest against the field vocabulary in `manifests/__taxonomy.yaml` and exits non-zero on error. It catches the mistakes that otherwise fail silently at runtime: an unknown `entity.type` or `event.kind`, a view pointing at a file id that doesn't exist, an unimplemented `transform`. Run it before opening a PR.

### Repository Structure                                                                                                                                                                                                                    
* **`webapp/`**: Vue 2 / Vuetify frontend (modified Google Timesketch derivative).
* **`python_core/`**: Python parsing and database logic (runs inside Pyodide in the browser).
* **`manifests/`**: Platform YAML configurations defining mappings to ECS.
* **`evaluation/`**: Academic paper replication package, figure scripts, and `evaluation/entity_resolution/`.
* **`scripts/`**: Developer utilities, currently `validate_manifests.py`.
* **`schema.sql`**: SQLite database schema. Both JS and Pyodide read/write to this DB, but never at the same time.
* **`tests/`**: Pytest suite for the Python engine. See [`tests/README.md`](tests/README.md).

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
The parser tests under `tests/python/extractors/` are parameterized over real export files and skip themselves when that data isn't present. See [`tests/README.md`](tests/README.md) before relying on them for coverage.

## License

This repository uses multiple licenses to protect different components. See `LICENSE` for more details.
