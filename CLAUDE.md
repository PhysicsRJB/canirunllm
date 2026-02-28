# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview
- **Purpose** – A simple web‑app that detects the local machine’s hardware (CPU, RAM, GPU) and determines whether a given LLM can run on it.
- **Components** – A Flask backend (`backend/`), a static frontend (`frontend/`), and a pytest test suite (`backend/tests/`).
- **Data** – Model hardware requirements are stored in `backend/static/models_info.json`. The file is populated on first run by querying the HuggingFace Hub, but a pre‑populated version is already present.

## High‑Level Architecture
```
frontend/
│   index.html      ← UI layout
│   style.css       ← basic styling
│   script.js       ← client‑side logic:
│                     • fetch hardware info
│                     • load models_info.json
│                     • filter & sort models
│                     • search box & compatibility check
│
backend/
│   app.py          ← Flask application
│   static/
│       models_info.json ← model → hardware mapping
│   llm_models.json ← optional static LLM requirement overrides
│   requirements.txt← Python dependencies
│   tests/
│       test_*.py   ← pytest tests covering API endpoints and logic
│
```
- **Flask API** (`app.py`):
  - `/api/hardware` – returns detected hardware.
  - `/api/models` – returns the full `models_info.json`.
  - `/api/models/filter` – filters models by supplied `min_ram` / `min_vram`.
  - `/api/check_compatibility?llm=<model_id>` – runs the compatibility algorithm.
  - Debug routes (`/debug/*`) expose internal state for rapid inspection.
- **Hardware detection** uses `psutil` (CPU/RAM) and `GPUtil` (GPU/VRAM).
- **Compatibility logic** (`check_compatibility`) checks RAM, VRAM, and GPU presence against the model’s declared requirements.
- **Frontend** loads the static JSON, filters out models with unknown requirements, sorts by total resource demand, and provides a live search box.

## Development & Maintenance Commands

| Task | Command | Notes |
|------|---------|-------|
| Install Python dependencies | `pip install -r backend/requirements.txt` | Run inside the repository root or a virtual environment. |
| Run the Flask server (development) | `python backend/app.py` | Starts on `http://127.0.0.1:5000`. The script prints “App started” and loads `models_info.json`. |
| Run the server with Flask CLI (alternative) | `export FLASK_APP=backend/app.py && flask run` | Same effect; useful if you prefer Flask’s built‑in reloader. |
| Execute the full test suite | `pytest -q` | Discovers all `test_*.py` files under `backend/tests`. |
| Run a single test file | `pytest -q backend/tests/test_app.py` | Replace with any other test file as needed. |
| Lint Python code (optional) | `flake8 backend` | Requires `flake8` to be installed (`pip install flake8`). |
| Auto‑format Python code (optional) | `black backend` | Requires `black` (`pip install black`). |
| Verify the frontend manually | Open `http://127.0.0.1:5000` in a browser | The UI will display hardware info, a filtered model dropdown, and the search box. |
| Quick API sanity check | `curl http://127.0.0.1:5000/api/hardware` | Returns JSON with CPU, RAM, and GPU details. |
| Inspect all Flask routes (debug) | `curl http://127.0.0.1:5000/debug/all_routes` | Useful for confirming route registration. |
| Refresh model data (if you want to re‑fetch from HuggingFace) | Delete `backend/static/models_info.json` and restart the server | The app will re‑download the top‑500 models and recompute requirements. |

- **Commit policy** – When modifying any file, create a git commit with a concise, informative message summarizing the change.

## Important Files & Their Roles
- **`backend/app.py`** – Core server, request handlers, hardware detection, compatibility logic.
- **`backend/static/models_info.json`** – JSON map of model IDs → `{min_ram_gb, min_vram_gb, gpu_required}`. Generated automatically on first run.
- **`frontend/script.js`** – Client‑side orchestration: fetches hardware, loads models, filters by compatibility, handles UI interactions.
- **`backend/tests/*.py`** – Pytest suite covering API endpoints, hardware detection, and compatibility checks.
- **`backend/requirements.txt`** – Pinpointed Python packages needed for the backend and tests.
- **`package.json`** – Minimal Node metadata (currently only declares a `gh` dependency, not used by the app).

## Debug & Inspection Helpers
- **Debug routes** (`/debug/...`) expose:
  - `/debug/all_routes` – list of all Flask routes.
  - `/debug/models_info` – raw `models_info.json` content.
  - `/debug/get_model/<model>` – specific model entry.
  - `/debug/models_path` – filesystem path to `models_info.json`.
- These are intentionally lightweight and can be called with `curl` or a browser for quick debugging.

## Testing Philosophy
- Tests are written with **pytest** and use Flask’s `test_client` to avoid needing a running server.
- The suite validates:
  - Successful hardware endpoint response.
  - Compatibility handling for known and unknown models.
  - Model list retrieval and filtering logic.
  - Interaction between `MODELS_INFO` and `LLM_MODELS`.
- Adding new tests should follow the existing pattern: import `app`, configure `app.config['TESTING'] = True`, and use `client = app.test_client()`.

---
*This CLAUDE.md is intended to give Claude Code a concise, actionable view of the repository’s structure, development workflow, and key entry points.*