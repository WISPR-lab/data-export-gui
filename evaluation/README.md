# Evaluation

Scripts and instructions for running evaluations:
- **Entity Resolution Evaluation**: `evaluation/entity_resolution/`
- **Time/Memory Performance Benchmarking**: `evaluation/efficiency/`
- **User Study Data Analysis**: `evaluation/user_study/`

> **Docker Containers**:
> * **`web`**: Web application server (`docker compose up web`).
> * **`eval`**: Terminal CLI for running Python evaluation scripts (`docker compose run --rm eval`).


---

## Entity Resolution Evaluation

This measures how well the device entity resolution pipeline (`python_core/device_grouping2/`) decides whether two authentication or session records came from the same device. Because data exports have very few stable device ID (e.g., serial numbers) and mostly rely on user agent strings, we evaluate against the FPStalker dataset [3] (collected via the AmIUnique platform [4]), where persistent `tracking_id` labels mark records known to originate from the same browser.

* **Scripts**:
  - `fetch_data.py`: Downloads the FPStalker raw dumps and converts them to a local DuckDB database (`evaluation/entity_resolution/data_raw/fp_stalker.duckdb`).
  - `sweep.py`: Runs parameter sweeps over parameter grid combinations (active timestamp window days, $K$ sampled tracking IDs) and computes **BCubed precision and recall**.
  - `run.py`: Main CLI entry point orchestrating fetching, parameter grid sweeps, and plot generation.

* **Configuration**:
  - Default parameters (`K_OPTIONS`, `MAX_DAYS_CLIENT_OPTIONS`, trial count, random seed) live in `config.py`.
  - Override grid options via CLI flags: `--k`, `--days`, `--trials`, and `--seed`.


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

> [!NOTE]
> Entity Resolution is a standalone CLI benchmark that runs inside the `eval` container. It operates independently of the web application (`web`).

1. **Start the evaluation container**:

   ```bash
   # from project root
   mkdir -p evaluation/entity_resolution/data_raw
   
   # mac/windows OR linux with VM
   docker compose run --rm eval

   # linux without VM (optional memory limit)
   docker compose run --rm eval --memory="8g"
   ```
   This opens an interactive bash shell inside the container (`/workspace`). Type `exit` (or press `Ctrl+D`) to leave when finished.




2. Inside the container shell, **run the evaluation**:
   ```bash
   # Sweeps all 3 regimes (Full Dataset, Window N=30d, Window N=60d), outputs 3-panel heatmaps and summary_table.csv in 1 command:
   uv run python -m evaluation.entity_resolution.plot_all_sampling --metric bcubed_f1 --table

   # (Optional) Re-plot metrics from saved results without re-computing sweeps:
   # <timestamp> is the run data folder created by the first step
   uv run python -m evaluation.entity_resolution.plot_all_sampling \
       --full evaluation/entity_resolution/runs/fp_stalker_<timestamp>/full/results.csv \
       --n30  evaluation/entity_resolution/runs/fp_stalker_<timestamp>/n30/results.csv \
       --n60  evaluation/entity_resolution/runs/fp_stalker_<timestamp>/n60/results.csv \
       --metric bcubed_f1 # (or mean_bcubed_precision, mean_bcubed_recall, bcubed_f05)

   ```


---

## Time/Memory Performance Evaluation

All python evaluation commands below are run inside the interactive `eval` container environment from Section 5.1 (`docker compose run --rm eval`).

Pre-computed trial logs across 1x, 10x, 100x, and 1000x runs are already committed in `evaluation/efficiency/trials/`.

### 1. Reproduce Performance Summary Table (Pre-computed Data)

Generate the paper's efficiency benchmark summary table:
```bash
uv run python -m evaluation.efficiency.summarize_trials
```
*Outputs `evaluation/efficiency/stats_by_export.csv` (overall summary) and `stats_by_stage.csv` (per-stage breakdown).*

### 2. (Optional) Run Fresh Profiling from Scratch

To generate new augmented datasets (derived from 1x baseline archives [2]) and profile fresh runs:

1. **Generate augmented datasets**:
   ```bash
   uv run python -m evaluation.efficiency.batch_augment
   ```

2. **Profile runs in Web UI**:
   If the web application (`web`) is running in another terminal window, stop it first:

   ```bash
   docker compose down
   ```
   Relaunch with memory sampling enabled:
   ```bash
   PERFORMANCE_MEMORY_SAMPLING=1 docker compose up web
   ```
   Upload each archive at `http://localhost:5001`. Move downloaded CSV log files from your Downloads folder into `evaluation/efficiency/trials/`:
   ```bash
   mkdir -p evaluation/efficiency/trials
   mv ~/Downloads/*_mem_perf.csv evaluation/efficiency/trials/
   ```

3. **Re-generate table**: Re-run `uv run python -m evaluation.efficiency.summarize_trials` above.


---

## User Study Analysis Scripts

User study CSV files are omitted from the repository to protect participant privacy.

### Execution

- **Inter-Rater Reliability (`irr.py`)**:
  ```bash
  uv run python evaluation/user_study/irr.py <path/to/codes.csv>
  ```
- **Feature Usage Chart (`feature_use_chart.py`)**:
  ```bash
  uv run python evaluation/user_study/feature_use_chart.py
  ```

### Input CSV Formats

#### Qualitative Coding CSV (for `irr.py`)

| Participant | Row Number | Coder 1 - Feature Use | Coder 2 - Feature Use | Coder 1 - Prompted | Coder 2 - Prompted | Coder 1 - Reaction | Coder 2 - Reaction |
|---|---|---|---|---|---|---|---|
| pN | 1 | Event Type Filter | Event Type Filter | Unprompted | Unprompted | Positive | Mixed |

#### Feature Usage Summary CSV (for `feature_use_chart.py`)

| feature | P1 | P2 | ... |
|---|---|---|---|
| Add/Remove Tag | Unprompted | Prompted | ... |
| Devices View | Prompted | Unprompted | ... |

---

## References

See main root [`README.md`](../README.md#references).


