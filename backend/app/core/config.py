import json
import os
from typing import List, Optional, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_ENV_PATH = os.path.join(_BACKEND_DIR, ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(_ENV_PATH, ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # --- Application Core ---
    app_name: str = "Email Based Candidate Screening Backend"
    app_env: str = "development"
    debug: bool = True
    host: str = "0.0.0.0"
    port: int = 8000
    public_base_url: str = "http://localhost:8000"
    cors_origins: Union[List[str], str] = Field(default_factory=lambda: ["*"])

    @field_validator("public_base_url", mode="before")
    @classmethod
    def validate_public_base_url(cls, v):
        if isinstance(v, str):
            clean = v.split("#")[0].strip()
            if clean:
                return clean.rstrip("/")
        return "http://localhost:8000"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            clean = v.split("#")[0].strip()
            if not clean:
                return ["*"]
            try:
                parsed = json.loads(clean)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                pass
            return [s.strip() for s in clean.split(",") if s.strip()] or ["*"]
        return v or ["*"]

    @field_validator(
        "database_url",
        "ms_tenant_id",
        "ms_client_id",
        "ms_client_secret",
        "ms_mailbox_upn",
        "scoring_agent_mode",
        "scoring_igentic_executor_url",
        "scoring_igentic_app_id",
        "scoring_igentic_api_key",
        "scoring_igentic_bearer_token",
        "scoring_igentic_username",
        "igentic_executor_url",
        "igentic_app_id",
        "igentic_api_key",
        "igentic_bearer_token",
        "igentic_username",
        mode="before",
    )
    @classmethod
    def clean_commented_strings(cls, v):
        if isinstance(v, str):
            clean = v.split("#")[0].strip()
            return clean if clean else None
        return v

    @field_validator(
        "port",
        "postgres_port",
        "max_resume_mb",
        "queue_poll_interval_seconds",
        "max_job_attempts",
        "circuit_breaker_failures",
        "circuit_breaker_reset_seconds",
        "daily_scoring_budget",
        "max_parallel_scoring",
        mode="before",
    )
    @classmethod
    def clean_commented_numerics(cls, v):
        if isinstance(v, str):
            clean = v.split("#")[0].strip()
            return clean if clean else None
        return v

    # --- PostgreSQL Database ---
    postgres_db: str = "talentpool"
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    database_url: Optional[str] = None

    @property
    def async_database_url(self) -> str:
        if self.database_url:
            # Ensure asyncpg dialect is used
            url = self.database_url
            if url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            elif url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+asyncpg://", 1)
            return url
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    @property
    def sync_database_url(self) -> str:
        if self.database_url:
            url = self.database_url
            if url.startswith("postgresql+asyncpg://"):
                url = url.replace("postgresql+asyncpg://", "postgresql://", 1)
            return url
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    # --- Ingestion & Resume Limits ---
    max_resume_mb: int = 10
    default_country: str = "IN"

    # --- Microsoft Graph API (Mailbox Sync) ---
    ms_tenant_id: Optional[str] = None
    ms_client_id: Optional[str] = None
    ms_client_secret: Optional[str] = None
    ms_mailbox_upn: Optional[str] = None

    @property
    def is_graph_configured(self) -> bool:
        return bool(
            self.ms_tenant_id
            and self.ms_client_id
            and self.ms_client_secret
            and self.ms_mailbox_upn
        )

    # --- Recruiter Agent (iGentic) ---
    igentic_executor_url: Optional[str] = None
    igentic_app_id: Optional[str] = "iGentic-2.0"
    igentic_api_key: Optional[str] = None
    igentic_bearer_token: Optional[str] = None
    igentic_username: Optional[str] = None

    # --- Scoring Agent Connectivity Mode ---
    # fake | igentic (NO other mode exists)
    scoring_agent_mode: str = "fake"

    # --- Scoring Agent via iGentic ---
    scoring_igentic_executor_url: Optional[str] = None
    scoring_igentic_app_id: Optional[str] = "iGentic-2.0"
    scoring_igentic_api_key: Optional[str] = None
    scoring_igentic_bearer_token: Optional[str] = None
    scoring_igentic_username: Optional[str] = None

    @property
    def is_scoring_igentic_configured(self) -> bool:
        return bool(
            self.scoring_igentic_executor_url
            and self.scoring_igentic_app_id
            and self.scoring_igentic_api_key
            and self.scoring_igentic_bearer_token
        )

    # --- Queue Workers, Retries & Cost Circuit Breaker ---
    queue_poll_interval_seconds: float = 2.0
    max_job_attempts: int = 3
    circuit_breaker_failures: int = 5
    circuit_breaker_reset_seconds: int = 300
    daily_scoring_budget: int = 5000
    max_parallel_scoring: int = 10
    scorer_prompt_version: str = "score-v1"
    scorer_model_version: str = "v1.0"


_settings: Optional[Settings] = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
