from __future__ import annotations

from src.logging_config import PaperRecord
from src.ranking.scoring import DEFAULT_WEIGHTS, score_paper


class PaperRanker:
    def __init__(self, weights: dict[str, float] | None = None) -> None:
        self.weights = weights or DEFAULT_WEIGHTS

    def rank(self, papers: list[PaperRecord]) -> list[PaperRecord]:
        for paper in papers:
            score_paper(paper)
        return sorted(papers, key=lambda paper: paper.final_score, reverse=True)

    def score_components(self, paper: PaperRecord) -> dict[str, float]:
        return score_paper(paper)
