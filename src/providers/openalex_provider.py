from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable

from src.providers.base_provider import PaperRecord


class LiteratureProvider(ABC):
    """Abstract provider interface for scientific literature connectors."""

    name: str = "base"

    @abstractmethod
    def search(self, topics: Iterable[str], limit: int = 20) -> list[PaperRecord]:
        raise NotImplementedError
