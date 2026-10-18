"""Render safe text and explicitly control scene-detail disclosure."""

from collections import Counter
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from caniwatch.domain.models import Report, Status

LABELS = {
    Status.PRESENT: ("!", "Reported present", "red"),
    Status.ABSENT: ("○", "Reported absent", "cyan"),
    Status.CONFLICTING: ("±", "Conflicting reports", "yellow"),
    Status.UNKNOWN: ("?", "Unknown", "yellow"),
}


def summary(report: Report) -> str:
    counts = Counter(f.status for f in report.assessment.findings)
    if counts[Status.PRESENT] or counts[Status.CONFLICTING]:
        return "Relevant content is reported. Review your findings before deciding."
    if counts[Status.UNKNOWN]:
        return "Evidence is incomplete. Unknown does not mean absent."
    return "Sources report your concerns absent. Research coverage is limited."


def public_report(report: Report, details: bool) -> dict[str, Any]:
    data = report.model_dump(mode="json")
    for source in data["research"]["sources"]:
        del source["text"]
    if not details:
        del data["movie"]["overview"]
        for finding in data["assessment"]["findings"]:
            finding["source_ids"] = sorted({e["source_id"] for e in finding["evidence"]})
            del finding["explanation"]
            del finding["evidence"]
    data["summary"] = summary(report)
    if not report.demo:
        data["attribution"] = (
            "Movie metadata: TMDB. This product uses the TMDB API but is not endorsed "
            "or certified by TMDB. https://www.themoviedb.org"
        )
    return data


def render_report(report: Report, console: Console, details: bool) -> None:
    if report.demo:
        console.print(
            Text("OFFLINE DEMO · Fictional evidence · No AI or web requests", style="yellow")
        )
    movie = report.movie
    console.print(Text(f"{movie.title} ({movie.year or 'year unknown'})", style="bold magenta"))
    facts = Text()
    facts.append(" · ".join(movie.genres) or "Genres unavailable", style="bold")
    facts.append(f"\nRuntime: {movie.runtime or 'unknown'} min")
    facts.append(f"\nDirector: {movie.director or 'unknown'}")
    if details and movie.overview:
        facts.append(f"\n\n{movie.overview}")
    assessment = Text(summary(report))
    assessment.append("\n\nPrivate matching: local. Public research: movie only.", style="dim")
    panels = [
        Panel(facts, title="Film", border_style="magenta"),
        Panel(assessment, title="Your assessment", border_style="cyan"),
    ]
    if console.width >= 90:
        layout = Table.grid(expand=True, padding=(0, 1))
        layout.add_column(ratio=1)
        layout.add_column(ratio=1)
        layout.add_row(*panels)
        console.print(layout)
    else:
        for panel in panels:
            console.print(panel)

    table = Table(expand=True, header_style="bold", show_lines=details)
    table.add_column("Concern", ratio=2)
    table.add_column("Finding", ratio=2)
    table.add_column("Sources", ratio=1)
    for finding in report.assessment.findings:
        icon, label, color = LABELS[finding.status]
        concern = Text(finding.concern)
        if details and finding.explanation:
            concern.append(f"\n{finding.explanation}", style="dim")
        ids = sorted({item.source_id for item in finding.evidence})
        table.add_row(
            concern,
            Text(f"{icon} {label}", style=color),
            Text(", ".join(f"[{i}]" for i in ids) or "—"),
        )
    if console.width < 60:
        for finding in report.assessment.findings:
            icon, label, color = LABELS[finding.status]
            console.print(Text(finding.concern, style="bold"))
            console.print(Text(f"  {icon} {label}", style=color))
            if details and finding.explanation:
                console.print(Text(finding.explanation))
    else:
        console.print(table)

    if details:
        for finding in report.assessment.findings:
            for item in finding.evidence:
                console.print(Text(f"[{item.source_id}] {finding.concern}: “{item.quote}”"))
    for source in report.research.sources:
        kind = "page text" if source.full_text else "search excerpt"
        console.print(Text(f"[{source.id}] {source.title} ({kind})", style="dim"))
        console.print(Text(str(source.url), style="cyan"))
    for limitation in report.research.limitations:
        console.print(Text(f"• {limitation}", style="dim"))
    credits = report.research.credits
    console.print(
        Text(
            f"Research: {report.research.searches} searches · "
            f"credits: {credits if credits is not None else 'unavailable'}",
            style="dim",
        )
    )
    if not report.demo:
        console.print(
            Text(
                "Movie metadata: TMDB. This product uses the TMDB API but is not endorsed "
                "or certified by TMDB. https://www.themoviedb.org",
                style="dim",
            )
        )
