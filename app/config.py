from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

_PROJECT_ROOT = Path(__file__).resolve().parents[1]


# some Pydnantic magic that makes it easy to read in environment variables
# with type hinting / validation
class EnvSecrets(BaseSettings):
    YNAB_API_KEY: str
    GOOGLE_OAUTH_CLIENT_ID: str

    model_config = SettingsConfigDict(
        env_file=str(_PROJECT_ROOT / ".env"), env_file_encoding="utf-8"
    )


def load_secrets() -> EnvSecrets:
    secrets = EnvSecrets()
    return secrets
