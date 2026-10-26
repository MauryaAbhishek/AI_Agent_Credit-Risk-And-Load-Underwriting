
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    app_name: str = "Credit Risk Underwriting API"

    api_key: str | None = Field(default=None, repr=False)

    database_url: str = "sqlite:///./credit_risk.db"
    chroma_path: str = "./.chroma"
    policy_collection: str = "underwriting_policies"
    policy_version: str = "demo-policy-v1"
    log_level: str = "INFO"
    cors_origins: str = ""

    @model_validator(mode="after")
    def validate_security_settings(self):
        environment = self.app_env.strip().lower()

        if environment not in {"development", "test", "staging", "production"}:
            raise ValueError(
                "APP_ENV must be development, test, staging, or production."
            )

        if environment == "production":
            if not self.api_key:
                raise ValueError(
                    "Production requires API_KEY with at least 32 characters."
                )

            if self.api_key != self.api_key.strip():
                raise ValueError("Production API_KEY must not contain outer whitespace.")

            if len(self.api_key) < 32:
                raise ValueError(
                    "Production requires API_KEY with at least 32 characters."
                )

            if self.api_key.lower() in {
                "replace-with-a-long-random-secret",
                "changeme",
                "change-me",
                "your-api-key",
                "secret",
            }:
                raise ValueError("Set a unique production API_KEY.")

        return self


settings = Settings()
