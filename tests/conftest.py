from __future__ import annotations

from datetime import date

import pytest

from src.models import PaperRecord

LLM_ENV_VARS = ["GITHUB_MODELS_TOKEN", "OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_KEY"]


@pytest.fixture(autouse=True)
def offline_summarizer(monkeypatch):
    # Clear LLM credentials (including any loaded from a local .env) so the
    # Summarizer has no backend and tests never hit the network.
    for name in LLM_ENV_VARS:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def make_paper():
    def _make(title="Untitled", doi="10.0000/test", year=2024, abstract="", citations=0, topics=None):
        return PaperRecord(
            title=title,
            authors=["A. Author"],
            abstract=abstract,
            journal="Test Journal",
            publication_date=date(year, 1, 1),
            doi=doi,
            url=f"https://doi.org/{doi}",
            source="test",
            topics=topics or [],
            citation_count=citations,
        )

    return _make
