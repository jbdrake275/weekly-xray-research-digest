from __future__ import annotations

from datetime import date

from src.models import PaperRecord

# Every line of the report is derived from the paper metadata or the scores; nothing
# here asserts significance or relevance that the data does not support.


class MarkdownWriter:
    def __init__(self) -> None:
        self.today = date.today()

    def header(self, count: int, since: date | None, until: date | None, candidate_count: int | None) -> str:
        lines = [f"# Weekly X-Ray Research Digest: {self.today.isoformat()}", ""]
        if since and until:
            lines.append(f"Publications from {since.isoformat()} to {until.isoformat()}.")
        if candidate_count is not None:
            lines.append(f"Top {count} of {candidate_count} new candidates, ranked by keyword relevance score.")
        return "\n".join(lines) + "\n"

    def format_paper(self, rank: int, paper: PaperRecord) -> str:
        authors = ", ".join(paper.authors[:5]) if paper.authors else "Unknown authors"
        if len(paper.authors) > 5:
            authors += ", et al."
        year = paper.publication_date.year if paper.publication_date else "n.d."
        published = paper.publication_date.isoformat() if paper.publication_date else "Unknown"
        link = f"https://doi.org/{paper.doi}" if paper.doi else paper.url

        lines = [
            f"## {rank}. {paper.title}",
            "",
            f"**Citation:** {authors} ({year}). {paper.title}. *{paper.journal or 'Unknown venue'}*.",
            "",
            f"**Link:** {link}  ",
            f"**Published:** {published}  ",
            f"**Found via:** {paper.source or 'unknown'}  ",
            f"**Citations so far:** {paper.citation_count}",
            "",
        ]
        if paper.summary:
            lines += [f"**Summary (AI-generated, verify against the paper):** {paper.summary}", ""]
        abstract = paper.abstract or f"No abstract available from {paper.source or 'the provider'}."
        lines += [f"**Abstract:** {abstract}", ""]

        lines += [f"**Relevance score:** {paper.final_score:.2f}/100", ""]
        lines += [f"- {key.replace('_', ' ').capitalize()}: {value:.1f}" for key, value in sorted(paper.score_components.items())]
        return "\n".join(lines) + "\n"

    def footer(self) -> str:
        return (
            "---\n\n"
            "Scores are keyword-match heuristics over title, abstract, topics and venue, plus citation count. "
            "They rank candidates for reading; they are not an assessment of scientific quality.\n"
        )

    def write(
        self,
        papers: list[PaperRecord],
        since: date | None = None,
        until: date | None = None,
        candidate_count: int | None = None,
    ) -> str:
        sections = [self.header(len(papers), since, until, candidate_count)]
        sections += [self.format_paper(rank, paper) for rank, paper in enumerate(papers, start=1)]
        sections.append(self.footer())
        return "\n".join(sections)
