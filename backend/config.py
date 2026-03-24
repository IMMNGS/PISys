import os

# Project root
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class Config:
    """Base configuration."""
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
    # Define path DATA_DIR env var.
    DATA_DIR = os.environ.get("DATA_DIR", os.path.join(_PROJECT_ROOT, "data"))
    VCF_DIR = os.path.join(DATA_DIR, "vcf")
    VARIANT_UPLOAD_DIR = os.path.join(DATA_DIR, "variant_uploads")

    # Local AI/model storage — keep runtime bits and weights in one ignored root.
    # Suggested layout:
    #   LOCAL_AI_DIR/
    #     bin/      -> llama.cpp binaries or wrappers
    #     models/   -> gguf / other model weights
    LOCAL_AI_DIR = os.environ.get("LOCAL_AI_DIR", os.path.join(DATA_DIR, "local_ai"))
    LOCAL_AI_BIN_DIR = os.path.join(LOCAL_AI_DIR, "bin")
    LOCAL_AI_MODELS_DIR = os.path.join(LOCAL_AI_DIR, "models")

    # Local LLM server — default to a loopback OpenAI-compatible endpoint.
    LOCAL_LLM_BASE_URL = os.environ.get(
        "LOCAL_LLM_BASE_URL",
        "http://127.0.0.1:8080/v1/chat/completions",
    )
    LOCAL_LLM_MODEL_FILE = os.environ.get(
        "LOCAL_LLM_MODEL_FILE",
        os.path.join(LOCAL_AI_MODELS_DIR, "Qwen3.5-4B-Q4_K_M.gguf"),
    )
    LOCAL_LLM_MODEL = os.environ.get(
        "LOCAL_LLM_MODEL",
        "qwen3.5-4b-instruct",
    )
    LOCAL_LLM_TIMEOUT = int(os.environ.get("LOCAL_LLM_TIMEOUT", "120"))

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
