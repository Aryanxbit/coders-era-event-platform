import os
import secrets
from pathlib import Path

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent

class Config:
    """Application configuration."""
    SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_hex(32))
    DATABASE_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "coders_era.db"))
    DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"
    TESTING = False
    
    # Session security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_NAME = "coders_era_session"
    PERMANENT_SESSION_LIFETIME = 86400  # 24 hours

class DevelopmentConfig(Config):
    DEBUG = True

class TestingConfig(Config):
    TESTING = True
    DATABASE_PATH = ":memory:"
    SECRET_KEY = "test-secret-key"

class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True

config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
