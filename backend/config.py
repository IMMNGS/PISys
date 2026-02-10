import os

# Project root (one level up from backend/)
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class Config:
    """Application configuration."""
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

    # MySQL connection — update these for your environment
    MYSQL_USER = os.environ.get("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "")
    MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
    MYSQL_PORT = os.environ.get("MYSQL_PORT", "3306")

    # Single database for everything
    MYSQL_DB = os.environ.get("MYSQL_DB", "patient_db")

    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}"
        f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}"
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Data directory — local by default, can point to a remote mount / S3-fuse
    # path in the future via DATA_DIR env var.
    DATA_DIR = os.environ.get("DATA_DIR", os.path.join(_PROJECT_ROOT, "data"))
    VCF_DIR = os.path.join(DATA_DIR, "vcf")

    # Max upload size for VCF files (default 5000 MB)
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_UPLOAD_MB", "5000")) * 1024 * 1024
