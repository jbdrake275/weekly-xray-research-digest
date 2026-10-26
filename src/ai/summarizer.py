from __future__ import annotations

from pathlib import Path

from src.ai.summarizer import Summarizer
from src.logging_config import PaperRecord
from src.reporting.markdown_writer import MarkdownWriter


class ReportGenerator:
    def __init__(self, summarizer: Summarizer | None = None) -> None:
        self.summarizer = summarizer or Summarizer()
        self.markdown_writer = MarkdownWriter()

    def generate(self, papers: list[PaperRecord]) -> str:
        for paper in papers:
            paper.abstract = self.summarizer.summarize(paper)
        return self.markdown_writer.write(papers)

    def write_report(self, papers: list[PaperRecord], output_path: str | Path) -> Path:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        content = self.generate(papers)
        output.write_text(content, encoding="utf-8")
        return output
