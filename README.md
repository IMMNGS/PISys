# PISys

PISys is a patient information system with a Flask backend and React frontend.

## Prerequisites

- Python 3.9+
- Node.js + npm
- MySQL server (local or remote)

## Environment configuration

Create a `.env` file in the project root (or copy from `.env.example` if present). The launchers use these defaults when values are missing:

- `MYSQL_HOST=localhost`
- `MYSQL_PORT=3306`
- `MYSQL_USER=root`
- `MYSQL_PASSWORD=`
- `MYSQL_DB=pisys_db`

Optional:

- `SECRET_KEY` (recommended for production)
- `PORT` (used by `run.py` in development, default `5001`)

Note:
If MYSQL is already installed, please use the existing root password as `MYSQL_PASSWORD`.

## Setup

Run setup once to create `.venv`, install backend/frontend dependencies, create data folders, ensure the MySQL database exists, and seed initial HPO terms.

Unix/macOS:

```bash
bash run.sh setup
```

Windows:

Follow the instruction upon running run_windows.bat

## Start the server

The scripts support three modes: `setup`, `development`, `production`. If no mode is provided, they start in `production` mode.

Development mode

- Backend runs with `python run.py`.
- Frontend dev server is separate.

Unix/macOS:

```bash
bash run.sh development
```

Windows:

Follow the instruction upon running run_windows.bat

Frontend dev server (both platforms, in another terminal):

```bash
cd frontend
npm run dev
```

Production mode

- Unix/macOS launches Gunicorn (`gunicorn -c gunicorn.conf.py run:app`) on port `8000` by default.
- Windows launches Waitress on `0.0.0.0:8000`.

Unix/macOS:

```bash
bash run.sh production
```

Windows:

Follow the instruction upon running run_windows.bat

You can then open `http://127.0.0.1:8000`.

## Manual quick start (optional)

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
   - Database defaults are MySQL (`MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DB`).

## Project layout

- `backend/`: Flask API routes, config, models.
- `frontend/`: React app.
- `data/`: local data files.
- `test/`: backend tests.
- `run.sh`, `run_windows.ps1`: setup and launch scripts.
