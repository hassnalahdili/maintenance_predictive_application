from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    app_name: str = "Predictive Maintenance API"
    app_env: Literal["development", "production", "test"] = "development"
    database_url: str | None = None
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "predictive_maintenance"
    db_user: str = "postgres"
    db_password: str = "1234"
    secret_key: str = "dev-secret-key-change-me-please-2026"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    allowed_origins_csv: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173",
        validation_alias="ALLOWED_ORIGINS",
    )
    allowed_hosts_csv: str = Field(default="localhost,127.0.0.1", validation_alias="ALLOWED_HOSTS")
    frontend_public_url: str = "http://localhost:5173"
    api_public_url: str = "http://localhost:8000"
    proxy_headers: bool = True
    enforce_https: bool = False
    auto_create_schema: bool = True
    auto_seed_data: bool = True
    rate_limit_per_minute: int = 100
    alert_probability_threshold: float = 0.2
    alert_escalation_hours: int = 24
    login_lock_minutes: int = 30

    @property
    def allowed_origins(self) -> list[str]:
        values = [item.strip() for item in self.allowed_origins_csv.split(",") if item.strip()]
        if self.frontend_public_url not in values:
            values.append(self.frontend_public_url)
        return values

    @property
    def allowed_hosts(self) -> list[str]:
        return [item.strip() for item in self.allowed_hosts_csv.split(",") if item.strip()]

    @model_validator(mode="after")
    def finalize_runtime_settings(self):
        if not self.database_url:
            self.database_url = (
                f"postgresql+psycopg2://{self.db_user}:{self.db_password}@"
                f"{self.db_host}:{self.db_port}/{self.db_name}"
            )

        if self.app_env == "production":
            default_like_secrets = {
                "1234",
                "change_me",
                "super_secret_key_change_me",
                "dev-secret-key-change-me-please-2026",
            }
            if len(self.secret_key) < 32 or self.secret_key in default_like_secrets:
                raise ValueError("SECRET_KEY doit etre fort et unique en production.")
            if not self.enforce_https:
                raise ValueError("ENFORCE_HTTPS doit etre active en production.")
            if self.auto_create_schema:
                raise ValueError("AUTO_CREATE_SCHEMA doit etre desactive en production avec Alembic.")
            if self.auto_seed_data:
                raise ValueError("AUTO_SEED_DATA doit etre desactive en production.")

        return self

    model_config = SettingsConfigDict(env_file=BACKEND_ENV_FILE, extra="ignore")


settings = Settings()
