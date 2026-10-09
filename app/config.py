"""Configuration classes.

Secrets come only from environment variables. There are deliberately no
hardcoded fallback secrets: production refuses to start without them.
"""
import os


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")
    APP_NAME = "Ask Barry"
    # Stage marker shown on /health so the deployed state is always explicit.
    BUILD_STAGE = "8-job-agent"
    # Build the Azure-backed answerer from AZURE_* environment variables when present.
    ANSWERING_FROM_ENV = True
    BEHIND_PROXY = False
    # Protect the Azure bill on a public endpoint.
    RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "6"))
    RATE_LIMIT_PER_DAY = int(os.getenv("RATE_LIMIT_PER_DAY", "300"))
    # Job-ad evidence agent (Stage 8d): about 2 cents of Azure usage per ad, so much tighter limits.
    AGENT_RATE_PER_HOUR = int(os.getenv("AGENT_RATE_PER_HOUR", "3"))
    AGENT_RATE_PER_DAY = int(os.getenv("AGENT_RATE_PER_DAY", "20"))
    # "Scan a job ad" (Stage 8e): about a cent per photo; separate limit so scanning doesn't use up agent runs.
    SCAN_RATE_PER_HOUR = int(os.getenv("SCAN_RATE_PER_HOUR", "8"))
    SCAN_RATE_PER_DAY = int(os.getenv("SCAN_RATE_PER_DAY", "60"))
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024        # Flask rejects bigger uploads with 413 before reading them
    # ASK-42: where capability.json is read from (a path, or an https URL such as the raw file on main, so the
    # nightly rebuild shows without a redeploy). Blank means data/capability.json in this checkout.
    CAPABILITY_SOURCE = os.getenv("CAPABILITY_SOURCE") or None


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
