import os

# Project root
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class Config:
    """Base configuration."""
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

    # PostgreSQL connection — update these for your environment.
    # MYSQL_* fallback keeps older .env files working during migration.
    POSTGRES_USER = os.environ.get("POSTGRES_USER", os.environ.get("MYSQL_USER", "postgres"))
    POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", os.environ.get("MYSQL_PASSWORD", ""))
    POSTGRES_HOST = os.environ.get("POSTGRES_HOST", os.environ.get("MYSQL_HOST", "localhost"))
    POSTGRES_PORT = os.environ.get("POSTGRES_PORT", os.environ.get("MYSQL_PORT", "5432"))
    POSTGRES_DB = os.environ.get("POSTGRES_DB", os.environ.get("MYSQL_DB", "pisys_db"))

    # Local authentication bootstrap values.
    ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin12345")
    ADMIN_FULL_NAME = os.environ.get("ADMIN_FULL_NAME", "Administrator")

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        (
            f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
            f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
        ),
    )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Data directory — local by default, can point to a remote mount / S3-fuse
    # Define path DATA_DIR env var.
    DATA_DIR = os.environ.get("DATA_DIR", os.path.join(_PROJECT_ROOT, "data"))
    VCF_DIR = os.path.join(DATA_DIR, "vcf")
    VARIANT_UPLOAD_DIR = os.path.join(DATA_DIR, "variant_uploads")

    # Max upload size for VCF files (default 5000 MB)
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_UPLOAD_MB", "5000")) * 1024 * 1024


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False

    # Override the default secret key — require it from the environment
    SECRET_KEY = os.environ.get("SECRET_KEY")

    @classmethod
    def init_app(cls, app):
        if not cls.SECRET_KEY:
            raise RuntimeError(
                "SECRET_KEY environment variable must be set in production"
            )


# Map of config names to classes
config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
