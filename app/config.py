"""Configuration classes.

Secrets come only from environment variables. There are deliberately no
hardcoded fallback secrets: production refuses to start without them.
"""
import os


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")
    APP_NAME = "Ask Barry"
    # Stage marker shown on /health so the deployed state is always explicit.
    BUILD_STAGE = "5-rag"
    # Build the Azure-backed answerer from AZURE_* environment variables when present.
    ANSWERING_FROM_ENV = True
    BEHIND_PROXY = False
    # Protect the Azure bill on a public endpoint.
    RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "6"))
    RATE_LIMIT_PER_DAY = int(os.getenv("RATE_LIMIT_PER_DAY", "300"))


class DevelopmentConfig(Config):
    DEBUG = True
    # Throwaway key for local development only; never used in production.
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-not-secret")


class TestingConfig(Config):
    TESTING = True
    SECRET_KEY = "test-only-not-secret"
    ANSWERING_FROM_ENV = False          # tests never touch real Azure


class ProductionConfig(Config):
    DEBUG = False
    BEHIND_PROXY = True                 # Render's load balancer


CONFIGS = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
