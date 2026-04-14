# HA

HA is a patient information system with a Flask backend and React frontend.

## Quick start

1. Create and activate a virtual environment.
2. Install backend dependencies:

```bash
pip install -r requirements.txt
```

3. Install frontend dependencies:

```bash
cd frontend && npm install
```

4. Configure `.env` using `.env.example`.
   - Database defaults are PostgreSQL (`POSTGRES_HOST`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`).

## Run

Development:

```bash
bash run.sh development
```

Production:

```bash
bash run.sh production
```

On Windows:

```bat
run_windows.bat development
```

## Project layout

- `backend/`: Flask API routes, config, models.
- `frontend/`: React app.
- `data/`: local data files.
- `test/`: backend tests.
- `run.sh`, `run_windows.ps1`: setup and launch scripts.
