"""Freeze a week of candidates and write a blind labelling sheet.

Usage (from the repo root):
    python -m eval.build_label_set --since 2026-11-04 --until 2026-11-10 --exclude eval/candidates-2026-11-03.json

Writes eval/candidates-<until>.json (full records, plus each paper's rank under the
pipeline's current scorer) and eval/labels-<until>.csv (shuffled, no scores shown, so
the labels are not anchored on the ranking being tested).
"""
from __future__ import annotations

import argparse
import csv
import json
import random
from datetime import date
from pathlib import Path

from src.main import DEFAULT_TOPICS, dedupe_by_doi
from src.models import EXCLUDED_WORK_TYPES
from src.providers.crossref_provider import CrossrefProvider
from src.providers.openalex_provider import OpenAlexProvider
from src.ranking.paper_ranker import PaperRanker

EVAL_DIR = Path(__file__).parent


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--since", type=date.fromisoformat, required=True)
    parser.add_argument("--until", type=date.fromisoformat, default=date.today())
    parser.add_argument("--limit", type=int, default=20, help="Results per provider (the pipeline default is 20).")
    parser.add_argument("--exclude", type=Path, action="append", default=[], help="Earlier snapshot(s) whose DOIs to drop.")
    args = parser.parse_args()

    seen = set()
    for path in args.exclude:
        seen |= {p["doi"].strip().lower() for p in json.loads(path.read_text(encoding="utf-8"))["papers"]}

    papers = []
    for provider in (OpenAlexProvider(), CrossrefProvider()):
        papers += provider.search(DEFAULT_TOPICS, limit=args.limit, since=args.since, until=args.until)
    papers = [p for p in dedupe_by_doi(papers) if p.work_type not in EXCLUDED_WORK_TYPES and p.doi.strip().lower() not in seen]
    papers = PaperRanker().rank(papers)

    records = []
    for rank, paper in enumerate(papers, 1):
        record = paper.to_dict()
        record["current_rank"] = rank
        records.append(record)
    # Fixed seed: the sheet order is reproducible but carries no ranking signal.
    random.Random(int(args.until.strftime("%Y%m%d"))).shuffle(records)
    for i, record in enumerate(records, 1):
        record["id"] = f"P{i:02d}"

    stamp = args.until.isoformat()
    snapshot = {
        "created": date.today().isoformat(),
        "window": [args.since.isoformat(), stamp],
        "topics": DEFAULT_TOPICS,
        "limit_per_provider": args.limit,
        "excluded_snapshots": [str(p) for p in args.exclude],
        "papers": records,
    }
    (EVAL_DIR / f"candidates-{stamp}.json").write_text(json.dumps(snapshot, indent=2, ensure_ascii=False), encoding="utf-8")

    # utf-8-sig so Excel shows accented names and symbols correctly.
    with (EVAL_DIR / f"labels-{stamp}.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["id", "label (must-read / maybe / skip)", "notes", "title", "authors", "journal", "published", "type", "link", "abstract"])
        for r in records:
            authors = ", ".join(r["authors"][:3]) + (", et al." if len(r["authors"]) > 3 else "")
            link = f"https://doi.org/{r['doi']}" if r["doi"] else r["url"]
            writer.writerow([r["id"], "", "", r["title"], authors, r["journal"], r["publication_date"] or "", r["work_type"], link, r["abstract"] or "(no abstract)"])

    print(f"{len(records)} candidates, window {args.since} to {args.until}, {len(seen)} DOIs excluded")


if __name__ == "__main__":
    main()
