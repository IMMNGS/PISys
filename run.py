#!/usr/bin/env python
"""Entry-point to run the Flask application.

Development:  python run.py
Production:   gunicorn -c gunicorn.conf.py run:app
"""

import os
from pathlib import Path

from backend.app import create_app
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent


def _load_environment() -> str:
    """Load .env files and return normalized runtime environment name."""
    load_dotenv(PROJECT_ROOT / ".env", override=False)

    env_name = os.environ.get("FLASK_ENV", "development").strip().lower()
    env_file = PROJECT_ROOT / f".env.{env_name}"
    if env_file.exists():
        # Environment-specific values should override baseline .env values.
        load_dotenv(env_file, override=True)
        env_name = os.environ.get("FLASK_ENV", env_name).strip().lower()

    return env_name

env = _load_environment()
app = create_app(env)

if __name__ == "__main__":
    if env == "production":
        raise SystemExit(
            "Production must be started with Gunicorn: gunicorn -c gunicorn.conf.py run:app"
        )

    app.run(debug=True, port=int(os.environ.get("PORT", "5001")))
