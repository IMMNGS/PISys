#!/usr/bin/env python
"""Entry-point to run the Flask application."""

from backend.app import create_app

app = create_app()

if __name__ == "__main__":
    app.run(debug=True, port=5001)
