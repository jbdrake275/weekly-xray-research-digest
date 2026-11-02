from __future__ import annotations

from src.models import PaperRecord
from src.storage.history_manager import HistoryManager


class DuplicateChecker:
    def __init__(self, history_manager: HistoryManager) -> None:
        self.history_manager = history_manager

    def is_duplicate(self, paper: PaperRecord) -> bool:
        for entry in self.history_manager.load():
            if not entry:
                continue
            # DOIs are case-insensitive, and providers differ in the case they return.
            same_doi = bool(entry.get("doi")) and entry.get("doi").strip().lower() == paper.doi.strip().lower()
            same_title = bool(entry.get("title")) and entry.get("title").strip().lower() == paper.title.strip().lower()
            if same_doi or same_title:
                return True
        return False

    def filter_new(self, papers: list[PaperRecord]) -> list[PaperRecord]:
        return [paper for paper in papers if not self.is_duplicate(paper)]
