from __future__ import annotations

from datetime import date

from src.ai.summarizer import Summarizer
from src.reporting.report_generator import ReportGenerator

BOILERPLATE = ["quartet", "Why This Paper Was Selected", "CNDE Relevance Assessment", "Cross-Cutting Themes", "APA 7"]


class StubSummarizer:
    def summarize(self, paper):
        return f"Stub summary of {paper.title}"


def test_no_llm_backend_gives_no_summary(make_paper):
    summarizer = Summarizer()
    assert summarizer.backend == "none"
    assert summarizer.summarize(make_paper(abstract="Some abstract.")) == ""


def test_backend_failure_gives_no_summary(make_paper, monkeypatch):
    summarizer = Summarizer(backend="openai")

    def boom(paper):
        raise RuntimeError("API down")

    monkeypatch.setattr(summarizer, "_openai_summary", boom)
    assert summarizer.summarize(make_paper(abstract="Some abstract.")) == ""


def test_report_keeps_abstract_and_has_no_boilerplate(make_paper):
    paper = make_paper(title="Detector paper", doi="10.1/a", abstract="We measured things.")
    report = ReportGenerator().generate([paper], since=date(2026, 10, 19), until=date(2026, 11, 2), candidate_count=12)
    assert paper.abstract == "We measured things."
    assert "**Abstract:** We measured things." in report
    assert "AI-generated" not in report
    assert "Publications from 2026-10-19 to 2026-11-02." in report
    assert "Top 1 of 12 new candidates" in report
    assert "https://doi.org/10.1/a" in report
    for phrase in BOILERPLATE:
        assert phrase not in report


def test_report_labels_ai_summary_and_missing_abstract(make_paper):
    paper = make_paper(title="Optics paper", abstract="")
    paper.work_type = "posted-content"
    report = ReportGenerator(summarizer=StubSummarizer()).generate([paper])
    assert "**Type:** Preprint (not peer reviewed)" in report
    assert "**Summary (AI-generated, verify against the paper):** Stub summary of Optics paper" in report
    assert "No abstract available from test." in report
    assert paper.abstract == ""
