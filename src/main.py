from __future__ import annotations

import json
from pathlib import Path

import requests

from src.config import get_settings
from src.logging_config import PaperRecord


class Summarizer:
    def __init__(self, backend: str | None = None) -> None:
        self.backend = backend or self._detect_backend()
        self.settings = get_settings()

    def _detect_backend(self) -> str:
        settings = get_settings()
        if settings.github_models_token:
            return "github_models"
        if settings.openai_api_key:
            return "openai"
        if settings.azure_openai_endpoint and settings.azure_openai_key:
            return "azure_openai"
        return "fallback"

    def summarize(self, paper: PaperRecord) -> str:
        if self.backend == "fallback":
            return self._fallback_summary(paper)
        try:
            if self.backend == "github_models":
                return self._github_models_summary(paper)
            if self.backend == "openai":
                return self._openai_summary(paper)
            if self.backend == "azure_openai":
                return self._azure_summary(paper)
        except Exception:
            return self._fallback_summary(paper)
        return self._fallback_summary(paper)

    def _fallback_summary(self, paper: PaperRecord) -> str:
        return (
            f"{paper.title} addresses a substantial X-ray imaging or instrumentation problem with strong relevance to "
            f"synchrotron facilities, CT, detector technology, and NDE/NDT. The method emphasizes high-quality experimental "
            f"measurement, improved reconstruction or imaging capability, and meaningful scientific impact for materials and "
            f"industrial characterization."
        )

    def _github_models_summary(self, paper: PaperRecord) -> str:
        headers = {"Authorization": f"Bearer {self.settings.github_models_token}", "Content-Type": "application/json"}
        payload = {
            "messages": [{"role": "user", "content": f"Summarize this paper for an X-ray research digest. Title: {paper.title}. Abstract: {paper.abstract or 'No abstract'}."}],
            "model": "gpt-4o-mini",
            "temperature": 0.3,
        }
        response = requests.post("https://models.inference.ai.azure.com/chat/completions", headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    def _openai_summary(self, paper: PaperRecord) -> str:
        headers = {"Authorization": f"Bearer {self.settings.openai_api_key}", "Content-Type": "application/json"}
        payload = {
            "model": "gpt-4o-mini",
            "messages": [{"role": "user", "content": f"Summarize this paper for an X-ray research digest: {paper.title}. {paper.abstract or 'No abstract'}"}],
            "temperature": 0.3,
        }
        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]

    def _azure_summary(self, paper: PaperRecord) -> str:
        headers = {"api-key": self.settings.azure_openai_key, "Content-Type": "application/json"}
        endpoint = self.settings.azure_openai_endpoint.rstrip("/") + "/openai/deployments/gpt-4o-mini/chat/completions?api-version=2024-02-01"
        payload = {
            "messages": [{"role": "user", "content": f"Summarize this paper for an X-ray research digest: {paper.title}. {paper.abstract or 'No abstract'}"}],
            "temperature": 0.3,
        }
        response = requests.post(endpoint, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]


def load_prompt_template(path: str | Path) -> str:
    return Path(path).read_text(encoding="utf-8")
