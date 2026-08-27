# Evaluation

Evaluation scripts and data:
- **5.1 - Entity Resolution**: `evaluation/entity_resolution/`
- **5.2 - Time/Memory Performance**: `evaluation/efficiency/`
- **6 - Misc User Study Scripts**: `evaluation/user_study/`

---

## 5.2 - Time/Memory Performance

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

---

## 5.1 - Entity Resolution Evaluation

This is optional and requires substantial disk and memory resources; skip it if you only want to run the web app. (todo better explanation)

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

## 6 - Misc User Study Scripts

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


