"""Configuration classes.

Secrets come only from environment variables. There are deliberately no
hardcoded fallback secrets: production refuses to start without them.
"""
import os


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")
    APP_NAME = "Ask Barry"
    # Stage marker shown on /health so the deployed state is always explicit.
    BUILD_STAGE = "1-ingestion"


class DevelopmentConfig(Config):
    DEBUG = True
    # Throwaway key for local development only; never used in production.
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-not-secret")


class TestingConfig(Config):
    TESTING = True
    SECRET_KEY = "test-only-not-secret"


class ProductionConfig(Config):
    DEBUG = False


CONFIGS = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
