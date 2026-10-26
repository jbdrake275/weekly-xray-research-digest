from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    openalex_email: str = ""
    github_models_token: str = ""
    openai_api_key: str = ""
    azure_openai_endpoint: str = ""
    azure_openai_key: str = ""
    log_level: str = "INFO"
    max_results_per_provider: int = 20
    data_dir: Path = Path("data")
    report_dir: Path = Path("reports")

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            openalex_email=os.getenv("OPENALEX_EMAIL", ""),
            github_models_token=os.getenv("GITHUB_MODELS_TOKEN", ""),
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            azure_openai_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
            azure_openai_key=os.getenv("AZURE_OPENAI_KEY", ""),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            max_results_per_provider=int(os.getenv("MAX_RESULTS_PER_PROVIDER", "20")),
            data_dir=Path(os.getenv("DATA_DIR", "data")),
            report_dir=Path(os.getenv("REPORT_OUTPUT_DIR", "reports")),
        )


def get_settings() -> Settings:
    return Settings.from_env()
