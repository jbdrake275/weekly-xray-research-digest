from __future__ import annotations

import json
from datetime import date
from typing import Iterable

import requests

from src.config import get_settings
from src.logging_config import PaperRecord
from src.providers.base_provider import LiteratureProvider


class OpenAlexProvider(LiteratureProvider):
    name = "openalex"

    def __init__(self, email: str | None = None) -> None:
        settings = get_settings()
        self.email = email or settings.openalex_email

    def search(self, topics: Iterable[str], limit: int = 20) -> list[PaperRecord]:
        query_terms = list(topics)
        if not query_terms:
            query_terms = ["X-ray tomography", "synchrotron radiation"]

        query = " OR ".join(f'"{term}"' for term in query_terms)
        params = {
            "search": query,
            "per-page": min(limit, 50),
            "mailto": self.email or "research-digest@example.com",
            "filter": "has_doi:true,publication_year:>2000",
        }
        response = requests.get("https://api.openalex.org/works", params=params, timeout=30)
        response.raise_for_status()
        payload = response.json()
        results = payload.get("results", [])

        papers: list[PaperRecord] = []
        for item in results:
            doi = item.get("doi") or item.get("ids", {}).get("doi")
            if not doi:
                continue
            doi = doi.replace("https://doi.org/", "") if doi.startswith("https://") else doi
            title = item.get("title") or "Untitled"
            abstract = item.get("abstract") or ""
            abstract = abstract.replace("\n", " ") if abstract else ""
            publication_date_value = item.get("publication_date")
            publication_date = None
            if publication_date_value:
                try:
                    publication_date = date.fromisoformat(publication_date_value)
                except ValueError:
                    publication_date = None

            primary = item.get("primary_location") or {}
            source_name = ""
            if primary.get("source"):
                source_name = primary["source"].get("display_name", "")
            journal = source_name

            authors = []
            for authorship in item.get("authorships", []):
                author = authorship.get("author") or {}
                name = author.get("display_name")
                if name:
                    authors.append(name)

            url = primary.get("landing_page_url") or item.get("id") or ""
            topics_list = [concept.get("display_name", "") for concept in item.get("concepts", [])[:5] if concept.get("display_name")]
            citation_count = item.get("cited_by_count", 0)
            paper = PaperRecord(
                title=title,
                authors=authors,
                abstract=abstract,
                journal=journal,
                publication_date=publication_date,
                doi=doi,
                url=url,
                source=self.name,
                topics=topics_list,
                citation_count=citation_count,
                is_peer_reviewed=True,
                raw=item,
            )
            papers.append(paper)
        return papers
