from __future__ import annotations

import pytest

from src.ranking.paper_ranker import PaperRanker
from src.ranking.scoring import DEFAULT_WEIGHTS, score_paper


def test_weights_sum_to_one():
    assert sum(DEFAULT_WEIGHTS.values()) == pytest.approx(1.0)


def test_components_bounded_and_final_score_is_weighted_sum(make_paper):
    paper = make_paper(
        title="Novel synchrotron phase contrast tomography detector for industrial NDE",
        abstract="A new reconstruction method for defect inspection of materials.",
        citations=1000,
    )
    components = score_paper(paper)
    assert set(components) == set(DEFAULT_WEIGHTS)
    assert all(0.0 <= value <= 100.0 for value in components.values())
    expected = sum(components[key] * DEFAULT_WEIGHTS[key] for key in DEFAULT_WEIGHTS)
    assert paper.final_score == pytest.approx(expected, abs=0.01)


def test_ranker_orders_relevant_paper_first(make_paper):
    relevant = make_paper(title="Synchrotron X-ray tomography detector for NDE inspection", doi="10.1/a")
    unrelated = make_paper(title="Soil moisture survey", doi="10.1/b")
    ranked = PaperRanker().rank([unrelated, relevant])
    assert ranked[0] is relevant
    assert ranked[0].final_score > ranked[1].final_score
