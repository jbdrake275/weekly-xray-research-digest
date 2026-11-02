from __future__ import annotations

import csv

import pytest

from src.storage.duplicate_checker import DuplicateChecker
from src.storage.history_manager import HistoryManager


def test_history_roundtrip_and_csv(tmp_path, make_paper):
    history = HistoryManager(tmp_path / "data" / "history.json")
    assert history.load() == []
    paper = make_paper(title="Paper A", doi="10.1/a")
    history.add_papers([paper])
    assert [entry["doi"] for entry in history.load()] == ["10.1/a"]

    csv_path = history.export_selected_csv([paper], tmp_path / "out.csv")
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))
    assert rows[0]["title"] == "Paper A"


def test_same_doi_or_title_is_duplicate(tmp_path, make_paper):
    history = HistoryManager(tmp_path / "history.json")
    history.add_papers([make_paper(title="Paper A", doi="10.1/a", year=2020)])
    checker = DuplicateChecker(history)
    assert checker.is_duplicate(make_paper(title="Something else", doi="10.1/a", year=2021))
    assert checker.is_duplicate(make_paper(title="  paper a ", doi="10.1/zzz", year=2021))


def test_unrelated_paper_from_other_year_is_new(tmp_path, make_paper):
    history = HistoryManager(tmp_path / "history.json")
    history.add_papers([make_paper(title="Paper A", doi="10.1/a", year=2020)])
    assert not DuplicateChecker(history).is_duplicate(make_paper(title="Paper B", doi="10.1/b", year=2021))


@pytest.mark.xfail(strict=True, reason="Known bug: same_year is OR'd in, so any paper from a recorded year is a 'duplicate'.")
def test_unrelated_paper_from_same_year_is_new(tmp_path, make_paper):
    history = HistoryManager(tmp_path / "history.json")
    history.add_papers([make_paper(title="Paper A", doi="10.1/a", year=2024)])
    assert not DuplicateChecker(history).is_duplicate(make_paper(title="Paper B", doi="10.1/b", year=2024))
