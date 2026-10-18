"""Render safe text and explicitly control scene-detail disclosure."""

from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from caniwatch.domain.models import Report, Status

LABELS = {
    Status.PRESENT: ("!", "Reported present", "red"),
    Status.ABSENT: ("○", "Reported absent", "green"),
    Status.CONFLICTING: ("±", "Conflicting reports", "red"),
    Status.UNKNOWN: ("?", "Unknown", "yellow"),
}

TMDB_ATTRIBUTION = (
    "Movie metadata: TMDB. This product uses the TMDB API but is not endorsed "
    "or certified by TMDB. https://www.themoviedb.org"
)


def assessment_status(report: Report) -> Status:
    statuses = {finding.status for finding in report.assessment.findings}
    if statuses & {Status.PRESENT, Status.CONFLICTING}:
        return Status.PRESENT
    if Status.UNKNOWN in statuses or not statuses:
        return Status.UNKNOWN
    return Status.ABSENT


def summary(report: Report) -> str:
    findings = report.assessment.findings
    for status in (Status.PRESENT, Status.CONFLICTING, Status.UNKNOWN):
        concerns = [" ".join(f.concern.split()) for f in findings if f.status == status]
        if not concerns:
            continue
        subject = ", ".join(concerns)
        if len(subject) > 80:
            subject = (
                "one of your concerns"
                if len(concerns) == 1
                else f"{len(concerns)} of your concerns"
            )
        if status == Status.PRESENT:
            text = f"I'd skip this one based on what you want to avoid. Sources report {subject}."
            if any(f.status in {Status.CONFLICTING, Status.UNKNOWN} for f in findings):
                text += " Some of your other concerns are still unclear."
            return text
        if status == Status.CONFLICTING:
            return (
                f"I'd hold off on this one. Sources disagree about {subject}, "
                "so I can't give you a clear go-ahead."
            )
        return f"I'd hold off for now. The sources don't give a clear answer about {subject}."
    if not findings:
        return "I'd hold off for now. There are no findings to base a recommendation on."
    return (
        "This looks like a reasonable pick for you. The sources specifically say the things "
        "you want to avoid don't occur, though research can miss things."
    )


def public_report(report: Report, details: bool, *, api_usage: bool = False) -> dict[str, Any]:
    data = report.model_dump(mode="json")
    if not report.movie.age_classifications:
        del data["movie"]["age_classifications"]
    del data["research"]["searches"]
    if not api_usage or report.tmdb_requests is None:
        del data["tmdb_requests"]
    if not api_usage or report.research.credits is None:
        del data["research"]["credits"]
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
        data["attribution"] = TMDB_ATTRIBUTION
    return data


def render_api_usage(report: Report, console: Console) -> None:
    credits = report.research.credits
    requests = report.tmdb_requests
    if credits is None and requests is None:
        return
    console.print()
    label = "API Usage: (fictional demo)" if report.demo else "API Usage:"
    console.print(Text(label, style="dim"))
    if requests is not None:
        console.print(Text(f"• TMDB: {requests} requests", style="dim"))
    if credits is not None:
        console.print(Text(f"• Tavily: {credits:g} credits used", style="dim"))


def render_report(
    report: Report, console: Console, details: bool, *, api_usage: bool = False
) -> None:
    if report.demo:
        console.print(
            Text("OFFLINE DEMO · Fictional evidence · No AI or web requests", style="yellow")
        )
    movie = report.movie
    facts = Text()
    facts.append(f"{movie.title} ({movie.year or 'year unknown'})\n", style="bold")
    facts.append(" · ".join(movie.genres) or "Genres unavailable", style="bold")
    facts.append(f"\nRuntime: {movie.runtime or 'unknown'} min")
    facts.append(f"\nDirector: {movie.director or 'unknown'}")
    classifications = [
        f"{label} {' / '.join(movie.age_classifications[country])}"
        for country, label in (("DE", "FSK"), ("US", "US"), ("GB", "UK"))
        if movie.age_classifications.get(country)
    ]
    if classifications:
        label = "Age classifications (fictional demo)" if report.demo else "Age classifications"
        facts.append(f"\n{label}: " + " · ".join(classifications))
    if details and movie.overview:
        facts.append(f"\n\n{movie.overview}")
    assessment = Text(summary(report))
    panels = [
        Panel(facts, title="Film", border_style="dim"),
        Panel(
            assessment,
            title="Your Assessment",
            border_style=LABELS[assessment_status(report)][2],
        ),
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
    table.add_column("Finding", width=21, no_wrap=True)
    table.add_column("Comment", ratio=3)
    table.add_column("Sources", width=7)
    for finding in report.assessment.findings:
        icon, label, color = LABELS[finding.status]
        concern = Text(finding.concern)
        ids = sorted({item.source_id for item in finding.evidence})
        table.add_row(
            concern,
            Text(f"{icon} {label}", style=color),
            Text(" ".join(finding.comment.split()) or "—", style="dim"),
            Text(", ".join(f"[{i}]" for i in ids) or "—"),
        )
    if console.width < 60:
        for finding in report.assessment.findings:
            icon, label, color = LABELS[finding.status]
            console.print(Text(finding.concern, style="bold"))
            console.print(Text(f"  {icon} {label}", style=color))
            if finding.comment:
                console.print(Text(" ".join(finding.comment.split()), style="dim"))
            ids = sorted({item.source_id for item in finding.evidence})
            console.print(Text("Sources: " + (", ".join(f"[{i}]" for i in ids) or "—")))
    else:
        console.print(table)

    if details:
        for finding in report.assessment.findings:
            if finding.explanation:
                console.print(Text(f"{finding.concern}: {finding.explanation}"))
            for item in finding.evidence:
                console.print(Text(f"[{item.source_id}] {finding.concern}: “{item.quote}”"))
    console.print()
    for source in report.research.sources:
        kind = "page text" if source.full_text else "search excerpt"
        console.print(Text(f"[{source.id}] {source.title} ({kind})", style="dim"))
        console.print(Text(str(source.url), style="cyan"))
    if report.research.sources:
        console.print()
    console.print(Text("Disclaimers", style="dim"))
    if not report.demo:
        console.print(Text("• AI assessments can be wrong.", style="dim"))
    for limitation in report.research.limitations:
        console.print(Text(f"• {limitation}", style="dim"))
    if not report.demo:
        console.print(Text(f"• {TMDB_ATTRIBUTION}", style="dim"))
    if api_usage or report.demo:
        render_api_usage(report, console)
