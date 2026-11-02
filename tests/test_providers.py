from __future__ import annotations

from datetime import date

import pytest

from src.providers import crossref_provider, openalex_provider


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


@pytest.fixture
def fake_get(monkeypatch):
    calls = {}

    def install(module, payload):
        def _get(url, params=None, headers=None, timeout=None):
            calls.update(url=url, params=params)
            return FakeResponse(payload)

        monkeypatch.setattr(module.requests, "get", _get)
        return calls

    return install


def test_openalex_parses_works_and_strips_doi_prefix(fake_get):
    payload = {
        "results": [
            {
                "doi": "https://doi.org/10.1/xyz",
                "title": "X-ray tomography of foams",
                "abstract_inverted_index": {"of": [1, 4], "Tomography": [0], "foams": [2], "and": [3], "gels.": [5]},
                "publication_date": "2025-03-04",
                "primary_location": {"source": {"display_name": "J. Synchrotron Rad."}, "landing_page_url": "https://example.org/p"},
                "authorships": [{"author": {"display_name": "Ada Lovelace"}}],
                "concepts": [{"display_name": "Tomography"}],
                "cited_by_count": 7,
            },
            {"title": "No DOI, skipped"},
        ]
    }
    calls = fake_get(openalex_provider, payload)
    papers = openalex_provider.OpenAlexProvider(email="me@example.org").search(["X-ray CT"], limit=5)
    assert calls["params"]["mailto"] == "me@example.org"
    assert len(papers) == 1
    paper = papers[0]
    assert paper.doi == "10.1/xyz"
    assert paper.publication_date == date(2025, 3, 4)
    assert paper.journal == "J. Synchrotron Rad."
    assert paper.authors == ["Ada Lovelace"]
    assert paper.citation_count == 7
    assert paper.abstract == "Tomography of foams and of gels."


def test_clean_jats_strips_markup():
    raw = "<jats:title>Abstract</jats:title>\n  <jats:p>Phase  contrast &amp; <jats:italic>in situ</jats:italic> CT.</jats:p>"
    assert crossref_provider.clean_jats(raw) == "Phase contrast & in situ CT."
    assert crossref_provider.clean_jats("<title>Abstract</title> <p>Plain.</p>") == "Plain."
    assert crossref_provider.clean_jats("") == ""


def test_date_window_becomes_api_filters(fake_get):
    window = {"since": date(2026, 10, 19), "until": date(2026, 11, 2)}

    calls = fake_get(openalex_provider, {"results": []})
    openalex_provider.OpenAlexProvider().search(["CT"], **window)
    assert calls["params"]["filter"] == "has_doi:true,from_publication_date:2026-10-19,to_publication_date:2026-11-02"

    calls = fake_get(crossref_provider, {"message": {"items": []}})
    crossref_provider.CrossrefProvider().search(["CT"], **window)
    assert calls["params"]["filter"] == "from-pub-date:2026-10-19,until-pub-date:2026-11-02"

    calls = fake_get(crossref_provider, {"message": {"items": []}})
    crossref_provider.CrossrefProvider().search(["CT"])
    assert "filter" not in calls["params"]


def test_reconstruct_abstract_handles_missing_index():
    assert openalex_provider.reconstruct_abstract(None) == ""
    assert openalex_provider.reconstruct_abstract({}) == ""


def crossref_payload(date_parts):
    return {
        "message": {
            "items": [
                {
                    "DOI": "10.2/abc",
                    "title": ["Detector calibration"],
                    "author": [{"family": "Curie"}],
                    "published-print": {"date-parts": [date_parts]},
                    "container-title": ["NDT&E Int."],
                    "is-referenced-by-count": 3,
                }
            ]
        }
    }


def test_crossref_parses_full_date(fake_get):
    calls = fake_get(crossref_provider, crossref_payload([2024, 6, 15]))
    papers = crossref_provider.CrossrefProvider().search(["detector"], limit=5)
    # Crossref /works rejects has-doi with HTTP 400 (checked against the live API 2026-11-02).
    assert "has-doi" not in calls["params"].get("filter", "")
    assert len(papers) == 1
    assert papers[0].publication_date == date(2024, 6, 15)
    assert papers[0].authors == ["Curie"]
    assert papers[0].journal == "NDT&E Int."


@pytest.mark.parametrize(
    ("date_parts", "expected"),
    [([2024, 6], date(2024, 6, 1)), ([2024], date(2024, 1, 1)), ([None], None), ([], None)],
)
def test_crossref_parses_partial_date(fake_get, date_parts, expected):
    fake_get(crossref_provider, crossref_payload(date_parts))
    papers = crossref_provider.CrossrefProvider().search(["detector"], limit=5)
    assert papers[0].publication_date == expected
