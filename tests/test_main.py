from __future__ import annotations

import json
from datetime import date, timedelta

import requests

from src import main as main_module
from src.providers.base_provider import LiteratureProvider


class StaticProvider(LiteratureProvider):
    def __init__(self, name, papers):
        self.name = name
        self._papers = papers
        self.window = None

    def search(self, topics, limit=20, since=None, until=None):
        self.window = (since, until)
        return list(self._papers)


class FailingProvider(LiteratureProvider):
    name = "failing"

    def search(self, topics, limit=20, since=None, until=None):
        raise requests.ConnectionError("offline")


def run(tmp_path, providers, *extra):
    argv = ["--output-dir", str(tmp_path / "reports"), "--data-dir", str(tmp_path / "data"), *extra]
    return main_module.main(argv, providers=providers)


def test_dry_run_writes_report_without_history(tmp_path, make_paper):
    papers = [make_paper(title="Synchrotron tomography detector", doi="10.1/a")]
    assert run(tmp_path, [StaticProvider("one", papers)]) == 0
    reports = list((tmp_path / "reports").glob("weekly-xray-digest-*.md"))
    assert len(reports) == 1
    assert "Synchrotron tomography detector" in reports[0].read_text(encoding="utf-8")
    history = json.loads((tmp_path / "data" / "history.json").read_text(encoding="utf-8"))
    assert history["papers"] == []


def test_publish_records_history_dedupes_and_tolerates_failed_provider(tmp_path, make_paper):
    shared = make_paper(title="Shared paper", doi="10.1/A", year=2023)
    providers = [
        StaticProvider("one", [shared]),
        StaticProvider("two", [make_paper(title="Shared paper (Crossref)", doi="10.1/a", year=2023)]),
        FailingProvider(),
    ]
    assert run(tmp_path, providers, "--publish-report") == 0
    history = json.loads((tmp_path / "data" / "history.json").read_text(encoding="utf-8"))
    assert [entry["doi"] for entry in history["papers"]] == ["10.1/A"]
    assert list((tmp_path / "data").glob("selected-*.csv"))


def test_top_n_limits_selection(tmp_path, make_paper):
    papers = [make_paper(title=f"Paper {i}", doi=f"10.1/{i}", year=2000 + i) for i in range(6)]
    assert run(tmp_path, [StaticProvider("one", papers)], "--top-n", "2", "--publish-report") == 0
    history = json.loads((tmp_path / "data" / "history.json").read_text(encoding="utf-8"))
    assert len(history["papers"]) == 2


def test_date_window_passed_to_providers(tmp_path, make_paper, monkeypatch):
    monkeypatch.delenv("LOOKBACK_DAYS", raising=False)
    provider = StaticProvider("one", [make_paper(doi="10.1/a")])
    run(tmp_path, [provider])
    assert provider.window == (date.today() - timedelta(days=14), date.today())

    run(tmp_path, [provider], "--days", "30")
    assert provider.window[0] == date.today() - timedelta(days=30)


def test_no_new_papers_returns_error(tmp_path):
    assert run(tmp_path, [FailingProvider()]) == 1
    assert not (tmp_path / "reports").exists() or not list((tmp_path / "reports").iterdir())
