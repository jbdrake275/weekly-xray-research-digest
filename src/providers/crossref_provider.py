from __future__ import annotations

import html
import re
from datetime import date
from typing import Iterable

import requests

from src.config import get_settings
from src.models import PaperRecord
from src.providers.base_provider import LiteratureProvider


def clean_jats(abstract: str) -> str:
    # Crossref passes publisher abstracts through as JATS XML (<jats:p>, <title>, ...).
    # Drop the "Abstract" heading, strip remaining tags, decode entities, and collapse whitespace.
    text = re.sub(r"<(jats:)?title>\s*Abstract\s*</(jats:)?title>", " ", abstract, flags=re.IGNORECASE)
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    return " ".join(text.split())


class CrossrefProvider(LiteratureProvider):
    name = "crossref"

    def __init__(self, email: str | None = None) -> None:
        settings = get_settings()
        self.email = email or settings.openalex_email

    def search(
        self, topics: Iterable[str], limit: int = 20, since: date | None = None, until: date | None = None
    ) -> list[PaperRecord]:
        topic_terms = list(topics)
        if not topic_terms:
            topic_terms = ["X-ray tomography", "synchrotron radiation"]
        query = " OR ".join(topic_terms)
        headers = {}
        if self.email:
            headers["User-Agent"] = f"weekly-xray-research-digest/{self.email}"
        url = "https://api.crossref.org/works"
        params = {
            "select": "DOI,title,author,abstract,published-print,published-online,container-title,URL,score,is-referenced-by-count",
            "query.title": query,
            "rows": min(limit, 50),
        }
        filters = []
        if since:
            filters.append(f"from-pub-date:{since.isoformat()}")
        if until:
            filters.append(f"until-pub-date:{until.isoformat()}")
        if filters:
            params["filter"] = ",".join(filters)
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        payload = response.json().get("message", {})
        items = payload.get("items", [])

        papers: list[PaperRecord] = []
        for item in items:
            doi = item.get("DOI", "")
            if not doi:
                continue
            title = item.get("title", ["Untitled"])[0] if item.get("title") else "Untitled"
            authors = [author.get("family", "") for author in item.get("author", []) if author.get("family")]
            abstract = clean_jats(item.get("abstract") or "")
            published = item.get("published-print") or item.get("published-online") or {}
            date_value = None
            if published:
                # Crossref date-parts holds [year], [year, month] or [year, month, day];
                # pad so partial dates fall back to the first month/day.
                parts = ((published.get("date-parts") or [[]])[0] or []) + [None, None, None]
                year, month, day = parts[:3]
                if year is not None:
                    try:
                        date_value = date(year, month or 1, day or 1)
                    except ValueError:
                        date_value = None
            journal = ", ".join(item.get("container-title", []))
            url = item.get("URL", "")
            citation_count = item.get("is-referenced-by-count", 0)
            paper = PaperRecord(
                title=title,
                authors=authors,
                abstract=abstract,
                journal=journal,
                publication_date=date_value,
                doi=doi,
                url=url,
                source=self.name,
                topics=["X-ray", "imaging"],
                citation_count=citation_count,
                is_peer_reviewed=True,
                raw=item,
            )
            papers.append(paper)
        return papers
