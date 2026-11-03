from __future__ import annotations

import argparse
from datetime import date, timedelta
from pathlib import Path

import requests

from src.config import get_settings
from src.logging_config import configure_logging, ensure_directory
from src.models import EXCLUDED_WORK_TYPES, PaperRecord
from src.providers.base_provider import LiteratureProvider
from src.providers.crossref_provider import CrossrefProvider
from src.providers.openalex_provider import OpenAlexProvider
from src.ranking.paper_ranker import PaperRanker
from src.reporting.report_generator import ReportGenerator
from src.storage.duplicate_checker import DuplicateChecker
from src.storage.history_manager import HistoryManager

DEFAULT_TOPICS = [
    "X-ray computed tomography",
    "synchrotron radiation",
    "X-ray detector",
    "X-ray phase contrast imaging",
    "X-ray nondestructive evaluation",
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    settings = get_settings()
    parser = argparse.ArgumentParser(description="Generate the weekly X-ray research digest.")
    parser.add_argument("--output-dir", type=Path, default=settings.report_dir, help="Directory for the Markdown report.")
    parser.add_argument("--data-dir", type=Path, default=settings.data_dir, help="Directory for history and CSV exports.")
    parser.add_argument("--topic", dest="topics", action="append", help="Search topic; repeat for several. Defaults to DEFAULT_TOPICS.")
    parser.add_argument("--limit", type=int, default=settings.max_results_per_provider, help="Maximum results per provider.")
    parser.add_argument("--top-n", type=int, default=4, help="Number of ranked papers to include in the report.")
    parser.add_argument(
        "--days",
        type=int,
        default=settings.lookback_days,
        help="Only fetch papers published in the last N days (through today).",
    )
    parser.add_argument(
        "--publish-report",
        action="store_true",
        help="Record selected papers in the history and export a CSV. Without this flag the run is a dry run.",
    )
    return parser.parse_args(argv)


def collect_papers(
    providers: list[LiteratureProvider], topics: list[str], limit: int, since: date, until: date, logger
) -> list[PaperRecord]:
    papers: list[PaperRecord] = []
    for provider in providers:
        try:
            results = provider.search(topics, limit=limit, since=since, until=until)
        except requests.RequestException as exc:
            logger.warning("Provider %s failed: %s", provider.name, exc)
            continue
        logger.info("Provider %s returned %d papers", provider.name, len(results))
        papers.extend(results)
    return papers


def dedupe_by_doi(papers: list[PaperRecord]) -> list[PaperRecord]:
    # OpenAlex and Crossref index the same works, so one run can return a paper twice.
    seen: set[str] = set()
    unique: list[PaperRecord] = []
    for paper in papers:
        key = paper.doi.strip().lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(paper)
    return unique


def main(argv: list[str] | None = None, providers: list[LiteratureProvider] | None = None) -> int:
    args = parse_args(argv)
    settings = get_settings()
    logger = configure_logging(settings.log_level)
    topics = args.topics or DEFAULT_TOPICS
    providers = providers if providers is not None else [OpenAlexProvider(), CrossrefProvider()]

    # The window is deliberately longer than the weekly cadence: indexes lag behind
    # publication, so overlapping windows catch late arrivals and the history check
    # below keeps the overlap from repeating papers.
    until = date.today()
    since = until - timedelta(days=args.days)
    logger.info("Searching publications from %s to %s", since, until)
    papers = dedupe_by_doi(collect_papers(providers, topics, args.limit, since, until, logger))
    papers = [paper for paper in papers if paper.work_type not in EXCLUDED_WORK_TYPES]
    history = HistoryManager(ensure_directory(args.data_dir) / "history.json")
    new_papers = DuplicateChecker(history).filter_new(papers)
    logger.info("%d unique papers, %d not in history", len(papers), len(new_papers))
    if not new_papers:
        # Fail loudly: an empty report would let the workflow re-release last week's file.
        logger.error("No new papers found; no report written.")
        return 1

    selected = PaperRanker().rank(new_papers)[: args.top_n]
    today = until.isoformat()
    report_path = ReportGenerator().write_report(
        selected,
        ensure_directory(args.output_dir) / f"weekly-xray-digest-{today}.md",
        since=since,
        until=until,
        candidate_count=len(new_papers),
    )
    logger.info("Report written to %s", report_path)

    if args.publish_report:
        history.add_papers(selected)
        csv_path = history.export_selected_csv(selected, args.data_dir / f"selected-{today}.csv")
        logger.info("History updated; selection exported to %s", csv_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
