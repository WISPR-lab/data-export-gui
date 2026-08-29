# Evaluation

Scripts and instructions for running evaluations:
- **Entity Resolution Evaluation**: `evaluation/entity_resolution/`
- **Time/Memory Performance Benchmarking**: `evaluation/efficiency/`
- **User Study Data Analysis**: `evaluation/user_study/`

---

## Entity Resolution Evaluation

This measures how well the device entity resolution pipeline (`python_core/device_grouping2/`) decides
whether two authentication or session records came from the same device. Because data exports carry no
ground-truth device labels, we evaluate against the [FPStalker](https://github.com/Spirals-Team/FPStalker)
browser-fingerprint dataset, which does: its `tracking_id` marks records known to originate from the same
browser.

- `fetch_data.py` downloads the FPStalker dumps and converts them to a local DuckDB database.
- `sweep.py` runs the trials: for each cell of the parameter grid it samples K `tracking_id`s, groups their
  records with our matching rules, and scores the result with **BCubed precision/recall** against the known ids.
- `run.py` is the CLI entry point that ties those together and plots the output.

The grid defaults (`K_OPTIONS`, `MAX_DAYS_CLIENT_OPTIONS`, trial count, seed) live in `config.py` and can be
overridden with `--k`, `--days`, `--trials`, and `--seed`.

This is optional and requires substantial disk and memory resources; skip it if you only want to run the
web app.

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
* If you are _not_ using a VM to run Docker, proceed (adding the `--memory="8g"` flag).
* If you are using a VM, ensure disk/memory limits meet the requirements above.

### Run Instructions

1. **Start the container**:

   ```bash
      # from project root
      mkdir -p evaluation/entity_resolution/data_raw
      
      # mac/windows OR linux with VM
      docker compose run --rm eval

      # if linux w/o VM
      docker compose run --rm eval --memory="8g" # or "4g", etc.
   ```
   This will put you in an interactive bash session inside the container (at `/workspace`). The raw datasets will be downloaded to Docker named volume (`data_raw`) mounted at `evaluation/entity_resolution/data_raw` to speed up SQLite writes.

2. Inside the container shell, **download data and run evaluation**:
   ```bash
   uv run python -m evaluation.entity_resolution.run

   # Draw K tracking_ids active within a random 30-day timestamp window:
   uv run python -m evaluation.entity_resolution.run --window-days 30
   ```

---

## Time/Memory Performance Evaluation

The pipeline logs timing (duration, rows, DB calls per stage) on every run, printed as JSON to the console and downloaded as `<filename>_mem_perf.csv`. Column definitions are documented inline in `python_core/performance.py` and `webapp/src/utils/performanceExport.js`.

Memory sampling (JS heap + WASM heap, per stage) is optional — set `PERFORMANCE_MEMORY_SAMPLING=1` **before** `sync_assets.sh` runs (i.e. before `yarn serve`/`yarn build`):
```bash
PERFORMANCE_MEMORY_SAMPLING=1 yarn serve
```

### Using Data for Efficiency Evaluation

The 1x baseline archives are `evaluation/efficiency/data/{google,facebook}_original.zip`, and every augmented multiplier is derived from them. They originate from the open research dataset published by Nonnenkamp et al. [2] ([10.1145/3719027.3765147](https://doi.org/10.1145/3719027.3765147)). See [_Sample Data_](../README.md#sample-data) in the root README for citation details.

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

---

## User Study Analysis Scripts

Scripts for analyzing qualitative user study data (`evaluation/user_study/`):

- **Inter-Rater Reliability (`irr.py`)**: Computes Krippendorff's alpha from any coding CSV formatted with two coders' entries.
  ```bash
  uv run python evaluation/user_study/irr.py <path/to/codes.csv>
  ```
- **Feature Usage Chart (`feature_use_chart.py`)**: Generates feature usage plots (`feature_use.pdf`) from a summary CSV.
  ```bash
  uv run python evaluation/user_study/feature_use_chart.py
  ```

### Input CSV Formats

User study CSV files are omitted from the repository to protect participant privacy. To run these scripts on your own data, format your input CSVs as follows:

#### Qualitative Coding CSV (for `irr.py`)

| Participant | Row Number | Coder 1 - Feature Use | Coder 2 - Feature Use | Coder 1 - Prompted | Coder 2 - Prompted | Coder 1 - Reaction | Coder 2 - Reaction |
|---|---|---|---|---|---|---|---|
| pN | 1 | Event Type Filter | Event Type Filter | Unprompted | Unprompted | Positive | Mixed |


#### Feature Usage Summary CSV (for `feature_use_chart.py`)

| feature | P1 | P2 | ... |
|---|---|---|---|
| Add/Remove Tag | Unprompted | Prompted | ... |
| Devices View | Prompted | Unprompted | ... |


