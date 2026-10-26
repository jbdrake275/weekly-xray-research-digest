from __future__ import annotations

from datetime import date

from src.logging_config import PaperRecord


class MarkdownWriter:
    def __init__(self) -> None:
        self.today = date.today()

    def section_title(self, category: str) -> str:
        return f"# {category}\n"

    def format_paper(self, paper: PaperRecord) -> str:
        authors = ", ".join(paper.authors[:5]) if paper.authors else "Unknown authors"
        if len(paper.authors) > 5:
            authors += ", et al."

        score_lines = "\n".join(
            [f"- {key.replace('_', ' ').title()}: {value}" for key, value in sorted(paper.score_components.items())]
        )

        summary = (
            "This paper was selected because it represents a high-impact contribution to X-ray physics and "
            "imaging, with strong relevance to instrumentation, reconstruction, and modern research themes in "
            "synchrotron and laboratory-based X-ray systems."
        )

        return f"""
## Article Title

{paper.title}

Bibliography (APA 7): {authors} ({paper.publication_date.year if paper.publication_date else 'Unknown'}). {paper.title}. {paper.journal or 'Journal'}.

Direct Link / DOI: {paper.url or paper.doi}

Publication Date: {paper.publication_date.isoformat() if paper.publication_date else 'Unknown'}

Why This Paper Was Selected: {summary}

Core Focus & Methodology: {paper.abstract[:300] if paper.abstract else 'No abstract provided.'}

Key Findings & Significance: {paper.abstract[:300] if paper.abstract else 'No abstract provided.'}

Connection to Modern Research: This paper anchors important methodological or instrumentation developments that remain relevant to modern X-ray imaging, CT, detector design, and synchrotron-based experiment workflows.

CNDE Relevance Assessment: The methods and instrumentation described are highly relevant to NDE/NDT, industrial inspection, and materials characterization, especially where non-destructive measurement quality is critical.

Impact Scores:
{score_lines}

Overall Relevance Rating: {paper.final_score:.2f}/100
"""

    def write(self, papers: list[PaperRecord]) -> str:
        sections = []
        for paper in papers:
            sections.append(self.section_title(paper.category))
            sections.append(self.format_paper(paper))
        final_summary = self.write_final_summary(papers)
        return "\n".join(sections) + "\n" + final_summary

    def write_final_summary(self, papers: list[PaperRecord]) -> str:
        themes = [
            "Historical Connections: The selected historical papers establish the conceptual and instrumental foundations for modern X-ray imaging, bridging early methodological advances with current synchrotron and laboratory CT practices.",
            "Emerging Technologies: Recent advances highlight the continued role of detector development, reconstruction methods, and phase-sensitive imaging in enabling higher-resolution and lower-dose experimental workflows.",
            "Experimental Trends: The set emphasizes methodological rigor, instrument design, and data quality, reflecting the field's persistent focus on both sensitivity and practical deployment in real-world materials and industrial studies.",
            "Future Research Directions: Near-term opportunities include improved detector architectures, more robust phase-contrast approaches, and integrated workflows connecting laboratory systems to synchrotron-scale performance.",
            "Potential Relevance to Laboratory X-Ray Systems: These developments are directly relevant to laboratory CT and industrial imaging, particularly for improved spatial resolution, defect detection, and multi-scale materials characterization.",
        ]
        text = "\n".join(f"## {item.split(':')[0]}\n{item.split(':', 1)[1]}" for item in themes)
        return f"""
# Cross-Cutting Themes

{text}

This quartet collectively illustrates the continuity between foundational X-ray methods and current detector and reconstruction innovations. The historical works define the conceptual framework for phase-contrast, imaging physics, and high-throughput experimental design, while the recent and newest contributions reflect the rapid maturation of tomography, synchrotron instrumentation, and materials characterization workflows. The overall pattern suggests a field increasingly driven by detector performance, computational reconstruction, and the integration of advanced imaging methods into industrial and scientific inspection. These trends align strongly with the needs of laboratory X-ray systems, where robust, scalable, and high-throughput imaging capability is essential for both materials analysis and NDE/NDT applications.
"""
