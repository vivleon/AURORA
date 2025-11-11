# app/core/config.py
from __future__ import annotations
import os
from pathlib import Path
from typing import Optional
from pydantic import BaseSettings, Field, validator

class Settings(BaseSettings):
    # Core
    REDIS_URL: str = Field("redis://localhost:6379/0")
    POLICY_PATH: str = Field("data/policy.json")
    AUDIT_LOG_PATH: str = Field("data/audit.log")
    METRICS_DB_PATH: str = Field("data/metrics.db")
    BANDIT_STATE_PATH: str = Field("data/bandit_state.json")

    # Tools
    TESSERACT_PATH: Optional[str] = None
    FILES_ROOT: str = Field("data/files")

    # Mail (local .eml only, From display)
    SMTP_USER: Optional[str] = None
    SMTP_PASS: Optional[str] = None

    # Models
    MODEL_ROUTER_PATH: str = Field("app/router/model_router.json")
    MODEL_MANIFEST_PATH: str = Field("models/model_manifest.json")

    class Config:
        env_file = ".env"
        case_sensitive = False

    @validator("POLICY_PATH","AUDIT_LOG_PATH","METRICS_DB_PATH","BANDIT_STATE_PATH",
               "FILES_ROOT","MODEL_ROUTER_PATH","MODEL_MANIFEST_PATH", pre=True)
    def _normalize_path(cls, v: str) -> str:
        return str(Path(v).as_posix())

    @validator("TESSERACT_PATH", pre=True, always=True)
    def _normalize_tess(cls, v: Optional[str]) -> Optional[str]:
        return None if not v else str(Path(v).as_posix())

settings = Settings()

# Helper: ensure folders exist (idempotent)
def ensure_directories() -> None:
    for p in [
        Path(settings.POLICY_PATH).parent,
        Path(settings.AUDIT_LOG_PATH).parent,
        Path(settings.METRICS_DB_PATH).parent,
        Path(settings.FILES_ROOT),
        Path(settings.MODEL_ROUTER_PATH).parent,
        Path(settings.MODEL_MANIFEST_PATH).parent,
    ]:
        p.mkdir(parents=True, exist_ok=True)
