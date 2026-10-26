from __future__ import annotations

import csv
import json
from pathlib import Path

from src.logging_config import PaperRecord


class HistoryManager:
    def __init__(self, history_path: str | Path) -> None:
        self.history_path = Path(history_path)
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.history_path.exists():
            self.history_path.write_text(json.dumps({"papers": []}, indent=2), encoding="utf-8")

    def load(self) -> list[dict]:
        payload = json.loads(self.history_path.read_text(encoding="utf-8"))
        return payload.get("papers", [])

    def add_papers(self, papers: list[PaperRecord]) -> None:
        current = self.load()
        for paper in papers:
            current.append({
                "title": paper.title,
                "doi": paper.doi,
                "publication_date": paper.publication_date.isoformat() if paper.publication_date else None,
                "category": paper.category,
                "source": paper.source,
                "final_score": paper.final_score,
            })
        self.history_path.write_text(json.dumps({"papers": current}, indent=2), encoding="utf-8")

    def export_selected_csv(self, papers: list[PaperRecord], output_path: str | Path) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = ["title", "doi", "publication_date", "category", "source", "score"]
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            for paper in papers:
                writer.writerow({
                    "title": paper.title,
                    "doi": paper.doi,
                    "publication_date": paper.publication_date.isoformat() if paper.publication_date else "",
                    "category": paper.category,
                    "source": paper.source,
                    "score": paper.final_score,
                })
        return path
