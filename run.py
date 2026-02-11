#!/usr/bin/env python
"""Entry-point to run the Flask application.

Development:  python run.py
Production:   gunicorn -c gunicorn.conf.py run:app
"""

import os

from backend.app import create_app

env = os.environ.get("FLASK_ENV", "development")
app = create_app(env)

if __name__ == "__main__":
    # Only used in development — production uses gunicorn
    app.run(debug=True, port=5001)
