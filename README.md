# Patient Information System

Patient Information System is a Flask + React application for managing patient records, phenotype terms, variant findings, VCF uploads, and report generation.

## What it includes

- Flask backend with MySQL persistence
- React + TypeScript frontend built with Vite
- Session authentication, CSRF protection, and audit logging
- Patient, singleton, trio, HPO, disease-term, report, and insights workflows
- Docker and Synology NAS deployment support

## Quick start

### 1. Configure the environment

Copy `.env.example` to `.env` and fill in the database and secret values. The app uses these defaults when values are missing:

- `MYSQL_HOST=localhost`
- `MYSQL_PORT=3306`
- `MYSQL_USER=root`
- `MYSQL_PASSWORD=`
- `MYSQL_DB=pisys_db`

Recommended production values:

- `SECRET_KEY` — required in production
- `ADMIN_USERNAME`, `ADMIN_PASSWORD`, `ADMIN_FULL_NAME` — bootstrap admin user
- `MAX_UPLOAD_MB` — upload size limit in MB
- `DATA_DIR` — override local data location if needed

### 2. Install dependencies and initialize the app

Unix/macOS:

```bash
bash run.sh setup
```

Windows:

```powershell
.\run_windows.ps1 setup
```

### 3. Run the app

Development:

```bash
bash run.sh development
```

Production:

```bash
bash run.sh production
```

Windows uses the same modes through `run_windows.ps1` or `run_windows.bat`.

## Runtime URLs

- Backend / production app: `http://127.0.0.1:8000`
- Frontend development server: `http://127.0.0.1:5173`

## Main documentation

- [Repository documentation](DOCUMENTATION.md)
- [Synology deployment guide](SYNOLOGY_SETUP.md)

## Project structure

- `backend/` — Flask app factory, models, security helpers, and API routes
- `frontend/` — React user interface
- `data/` — uploaded files, seeded reference data, and local RAG assets
- `scripts/` — maintenance and seed scripts
- `test/` — automated backend tests

## Key files

- `run.py` — Python entry point used for local development
- `run.sh` — Unix/macOS setup and launch script
- `run_windows.ps1` / `run_windows.bat` — Windows setup and launch scripts
- `docker-compose.yml` — Docker deployment for Synology and other hosts
- `Dockerfile` — production container build
- `gunicorn.conf.py` — Gunicorn production settings
- `requirements.txt` — Python dependencies

## Notes

- The app stores data in MySQL and persists uploaded files under `data/`.
- The production build serves the compiled React app from Flask.
- Legacy scripts under `backend/routes/patient_info*` are ignored by git and are not part of the main runtime.
