from __future__ import annotations

from datetime import date
from pathlib import Path

from src.ai.summarizer import Summarizer
from src.models import PaperRecord
from src.reporting.markdown_writer import MarkdownWriter


class ReportGenerator:
    def __init__(self, summarizer: Summarizer | None = None) -> None:
        self.summarizer = summarizer or Summarizer()
        self.markdown_writer = MarkdownWriter()

    def generate(
        self, papers: list[PaperRecord], since: date | None = None, until: date | None = None, candidate_count: int | None = None
    ) -> str:
        for paper in papers:
            paper.summary = self.summarizer.summarize(paper)
        return self.markdown_writer.write(papers, since=since, until=until, candidate_count=candidate_count)

    def write_report(
        self,
        papers: list[PaperRecord],
        output_path: str | Path,
        since: date | None = None,
        until: date | None = None,
        candidate_count: int | None = None,
    ) -> Path:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        content = self.generate(papers, since=since, until=until, candidate_count=candidate_count)
        output.write_text(content, encoding="utf-8")
        return output
