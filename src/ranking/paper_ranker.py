from __future__ import annotations

from src.logging_config import PaperRecord

DEFAULT_WEIGHTS = {
    "scientific_significance": 0.25,
    "experimental_novelty": 0.20,
    "technical_impact": 0.20,
    "instrumentation_relevance": 0.15,
    "citation_influence": 0.10,
    "cnde_relevance": 0.10,
}

KEYWORD_MAP = {
    "scientific_significance": ["phase contrast", "tomography", "synchrotron", "xfel", "diffraction", "spectroscopy"],
    "experimental_novelty": ["new", "novel", "first", "development", "method", "instrumentation", "technique"],
    "technical_impact": ["reconstruction", "detector", "optics", "imaging", "contrast", "modality"],
    "instrumentation_relevance": ["detector", "instrument", "source", "optics", "beamline", "sensor"],
    "cnde_relevance": ["nde", "ndt", "inspection", "industrial", "materials", "defect"],
}


def normalized_score(value: float, ceiling: float) -> float:
    if ceiling <= 0:
        return 0.0
    return min(100.0, max(0.0, (value / ceiling) * 100.0))


def score_paper(paper: PaperRecord) -> dict[str, float]:
    text = " ".join([
        paper.title,
        paper.abstract,
        " ".join(paper.topics),
        paper.journal,
    ]).lower()

    citation_score = normalized_score(float(paper.citation_count), 300.0)
    scientific = score_keywords(text, KEYWORD_MAP["scientific_significance"]) * 1.2
    novelty = score_keywords(text, KEYWORD_MAP["experimental_novelty"]) * 1.1
    technical = score_keywords(text, KEYWORD_MAP["technical_impact"]) * 1.3
    instrumentation = score_keywords(text, KEYWORD_MAP["instrumentation_relevance"]) * 1.2
    cnde = score_keywords(text, KEYWORD_MAP["cnde_relevance"]) * 1.15

    components = {
        "scientific_significance": round(min(100.0, scientific), 2),
        "experimental_novelty": round(min(100.0, novelty), 2),
        "technical_impact": round(min(100.0, technical), 2),
        "instrumentation_relevance": round(min(100.0, instrumentation), 2),
        "citation_influence": round(citation_score, 2),
        "cnde_relevance": round(min(100.0, cnde), 2),
    }
    weighted = sum(components[key] * DEFAULT_WEIGHTS[key] for key in DEFAULT_WEIGHTS)
    paper.score_components = components
    paper.final_score = round(weighted, 2)
    return components


def score_keywords(text: str, keywords: list[str]) -> float:
    matches = 0
    for keyword in keywords:
        if keyword in text:
            matches += 1
    return min(100.0, (matches / max(1, len(keywords))) * 100.0)
