from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any


@dataclass
class PaperRecord:
    title: str
    authors: list[str]
    abstract: str = ""
    journal: str = ""
    publication_date: date | None = None
    doi: str = ""
    url: str = ""
    source: str = ""
    topics: list[str] = field(default_factory=list)
    citation_count: int = 0
    is_peer_reviewed: bool = True
    category: str = "Uncategorized"
    relevance: dict[str, float] = field(default_factory=dict)
    score_components: dict[str, float] = field(default_factory=dict)
    final_score: float = 0.0
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def publication_year(self) -> int | None:
        if self.publication_date is None:
            return None
        return self.publication_date.year

    @property
    def citation_label(self) -> str:
        return f"{self.citation_count} citations"

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "authors": self.authors,
            "abstract": self.abstract,
            "journal": self.journal,
            "publication_date": self.publication_date.isoformat() if self.publication_date else None,
            "doi": self.doi,
            "url": self.url,
            "source": self.source,
            "topics": self.topics,
            "citation_count": self.citation_count,
            "is_peer_reviewed": self.is_peer_reviewed,
            "category": self.category,
            "relevance": self.relevance,
            "score_components": self.score_components,
            "final_score": self.final_score,
        }
