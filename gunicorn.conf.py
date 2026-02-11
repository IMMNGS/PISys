"""Gunicorn production configuration.

Usage:
    gunicorn -c gunicorn.conf.py run:app
"""

import multiprocessing
import os

# ── Server socket ────────────────────────────────────────────────────────
bind = os.environ.get("GUNICORN_BIND", "0.0.0.0:8000")

# ── Worker processes ─────────────────────────────────────────────────────
# Recommended: 2-4 × $(nproc).  Default to (cores × 2) + 1.
workers = int(os.environ.get("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))
worker_class = os.environ.get("GUNICORN_WORKER_CLASS", "gthread")
threads = int(os.environ.get("GUNICORN_THREADS", "4"))

# ── Timeouts ─────────────────────────────────────────────────────────────
# Generous timeout for large VCF uploads / heavy analysis
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "120"))
graceful_timeout = int(os.environ.get("GUNICORN_GRACEFUL_TIMEOUT", "30"))
keepalive = int(os.environ.get("GUNICORN_KEEPALIVE", "5"))

# ── Logging ──────────────────────────────────────────────────────────────
accesslog = os.environ.get("GUNICORN_ACCESS_LOG", "-")  # stdout
errorlog = os.environ.get("GUNICORN_ERROR_LOG", "-")    # stderr
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")

# ── Security ─────────────────────────────────────────────────────────────
# Limit request sizes (body handled by Flask MAX_CONTENT_LENGTH)
limit_request_line = 8190
limit_request_fields = 100
limit_request_field_size = 8190

# ── Process naming ───────────────────────────────────────────────────────
proc_name = "patient-information-system"

# ── Server hooks ─────────────────────────────────────────────────────────
def on_starting(server):
    """Called just before the master process is initialized."""
    server.log.info("Starting Patient Information System (production)")


def post_fork(server, worker):
    """Called just after a worker has been forked."""
    server.log.info("Worker spawned (pid: %s)", worker.pid)


def pre_exec(server):
    """Called before a new master process is forked (on SIGHUP)."""
    server.log.info("Forked child, re-executing.")


def worker_exit(server, worker):
    """Called when a worker exits."""
    server.log.info("Worker exited (pid: %s)", worker.pid)
