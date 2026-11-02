from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import Iterable

from src.models import PaperRecord


class LiteratureProvider(ABC):
    """Abstract provider interface for scientific literature connectors.

    since/until bound the publication date (inclusive); None leaves that side open.
    """

    name: str = "base"

    @abstractmethod
    def search(
        self, topics: Iterable[str], limit: int = 20, since: date | None = None, until: date | None = None
    ) -> list[PaperRecord]:
        raise NotImplementedError
