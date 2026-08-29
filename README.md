# LEStrADE 
**L**ocal **E**ngine for **Str**uctured **A**nalysis of **D**ata **E**xports (named after the minor Sherlock Holmes character, [Inspector Lestrade](https://en.wikipedia.org/wiki/Inspector_Lestrade)) is an open-source visualization tool that helps users understand their account security history using data exports from online platforms.

Instead of uploading user data files to a server, this project processes everything locally in the browser using Pyodide, a port of CPython to WebAssembly that runs a full Python environment in the web browser.

The Vue frontend is forked and heavily modified from Google's Timesketch [1] (`timesketch/frontend-ng`). See the *License* section below.

## Architecture & Repository Structure

### Data Flow (Pyodide in Browser)
1. **Frontend**: Vue worker downloads Pyodide WASM + package wheels (pandas, regex, sqlite3) on load.
2. **Local Storage**: Data export ZIP files are unzipped locally in JavaScript and stored in the browser's [Origin Private File System (OPFS)](https://developer.mozilla.org/en-US/docs/Web/API/File_System_API/Origin_private_file_system).
3. **Parsing**: `python_core/` parses export files into standardized representations using YAML manifests in `manifests/`.
4. **Database**: Normalized records are written to a local WASM SQLite database (`schema.sql`) on OPFS.
5. **Visualization**: Vue queries the local SQLite database to render analytics views.

### Repository Layout
* **`webapp/`**: Vue 2 / Vuetify frontend (forked and heavily modified from Timesketch).
* **`python_core/`**: Python data engine, entity resolution, and parsing logic.
* **`manifests/`**: Platform YAML configurations defining mappings to ECS.
* **`evaluation/`**: Paper's evaluation scripts and datasets (Secs. 5, 6).
* **`supplementary_materials/`**: User study survey questionnaire and consultant screening flowcharts.
* **`UA-Extract-purepy/`**: Pure-Python user-agent parsing package, usually a submodule
* **`scripts/`**: Developer utilities.
* **`schema.sql`**: SQLite database schema.
* **`tests/`**: Pytest suite for the Python engine (see [`tests/README.md`](tests/README.md)).


## Quickstart (Web App)

Run it locally on your own machine. No submodule initialization is needed: the user-agent parser
(`UA-Extract-purepy/`) is vendored directly into this repository, so a plain clone or a downloaded
ZIP of the source is enough to build and run everything below.

### With Docker
**Prerequisites**: [Docker](https://www.docker.com/products/cli/) or [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running. 

```bash
docker compose up --build web
# there are slightly different instructions for docker if running the 
# paper evaluation since it requires more resources, see Evaluation below
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

You do not need your own data export to try the tool (although you are welcome to try, see more below). Two exports are checked into this repository:

* `evaluation/efficiency/data/google_original.zip` (Google)
* `evaluation/efficiency/data/facebook_original.zip` (Facebook)


Start the web app, go to Explore your Data --> Add Data Export, choose the matching platform, and select the ZIP as-is.

These are the same 1x archives the efficiency evaluation augments to 10x/100x/1000x, which is why they live
under `evaluation/`. See [`evaluation/README.md`](evaluation/README.md).

These datasets originate from the open research dataset published by Nonnenkamp et al. [2].



## Evaluation

Evaluation scripts and instructions live in [`evaluation/README.md`](evaluation/README.md).


## Supported Platforms

The tool can parse English language data exports:
* **Google**
* **Apple / iCloud**
* **Facebook**
* **Instagram**
* **Discord**
* **Snapchat**

For instructions on how to request your data exports, see the *How to Request Data* guide in the web application (`http://localhost:5001/#/how-to-request`). 
To try the tool without requesting your own export, see [_Sample Data_](#sample-data) above.


## Security & Privacy

When you import your data export file, it is never transmitted over the network; all unzipping, parsing, and database transactions happen entirely inside your local browser sandbox. The codebase does not make external API requests containing your data (such as querying a remote service to parse User Agents or geolocate IP addresses).

Pyodide binaries, WASM files, and Python package wheels are fully vendored and served locally from the web app bundle (`/pyodide/` and `/wheels/`). The web app can run offline once loaded.



## Contributing

Feel free to submit UI bugs under Issues or post there if you're interested in contributing to the project.
To add support for a new platform (or augment supported keys for an existing one), follow the instructions in the [Manifests Schema Guide](manifests/README.md), then validate your changes:
```bash
uv run python scripts/validate_manifests.py
```
This checks every manifest against the field vocabulary in `manifests/__taxonomy.yaml` and exits non-zero on error. It catches the mistakes that otherwise fail silently at runtime: an unknown `entity.type` or `event.kind`, a view pointing at a file id that doesn't exist, an unimplemented `transform`. Run it before opening a PR.

### Testing
To run unit tests for `python_core`, follow the instructions in [`tests/README.md`](tests/README.md).

## License

This repository uses multiple licenses to protect different components. See `LICENSE` for more details.

---

## References

* **[1]** Google. 2024. **Timesketch: Collaborative forensic timeline analysis.** Software repository. https://github.com/google/timesketch
* **[2]** Julia Nonnenkamp, Naman Gupta, Abhimanyu Dev Gupta, and Rahul Chatterjee. 2025. **Hidden in Plain Bytes: Investigating Interpersonal Account Compromise with Data Exports.** In *Proceedings of the 2025 ACM SIGSAC Conference on Computer and Communications Security (CCS '25)*, Taipei, Taiwan. ACM, New York, NY, USA, 4304–4318. https://doi.org/10.1145/3719027.3765147
* **[3]** Antoine Vastel, Walter Rudametkin, Romain Rouvoy, and Pierre Laperdrix. 2018. **FPStalker: Tracking Browser Fingerprint Evolutions.** In *Proceedings of the 2018 IEEE Symposium on Security and Privacy (SP)*. IEEE, 728–741. https://doi.org/10.1109/SP.2018.00008
* **[4]** Pierre Laperdrix, Walter Rudametkin, and Romain Rouvoy. 2016. **Beauty and the Beast: Diverting Modern Web Browsers to Build Unique Browser Fingerprints.** In *Proceedings of the 2016 IEEE Symposium on Security and Privacy (SP)*. IEEE, 878–894. https://doi.org/10.1109/SP.2016.57

