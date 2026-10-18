"""Fictional offline fixtures; never presented as real movie research."""

from caniwatch.application.service import screen
from caniwatch.domain.models import (
    Assessment,
    Evidence,
    Finding,
    Movie,
    Report,
    Research,
    Source,
    Status,
)

DEMO_CONCERNS = ["claustrophobia", "animal harm", "spiders"]


class DemoResearch:
    def research(self, movie: Movie) -> Research:
        return Research(
            sources=[
                Source(
                    id=1,
                    title="Fictional demonstration guide (not a real source)",
                    url="https://example.org/caniwatch-demo",
                    text="Several scenes occur in a locked, narrow cellar. No animals are harmed.",
                    full_text=True,
                )
            ],
            limitations=[
                "OFFLINE DEMO: fictional film, evidence, and fixture assessment. No AI used."
            ],
        )


class DemoAssessor:
    def assess(self, movie: Movie, research: Research, concerns: list[str]) -> Assessment:
        known = {
            "claustrophobia": (
                Status.PRESENT,
                "Several scenes occur in a locked, narrow cellar.",
                "Enclosed-space scenes are described in the fictional guide.",
            ),
            "animal harm": (
                Status.ABSENT,
                "No animals are harmed.",
                "The fictional guide explicitly reports no animal harm.",
            ),
        }
        findings = []
        for concern in concerns:
            if concern.casefold() in known:
                status, quote, explanation = known[concern.casefold()]
                findings.append(
                    Finding(
                        concern=concern,
                        status=status,
                        comment=(
                            "The fictional guide explicitly reports this content."
                            if status == Status.PRESENT
                            else "The fictional guide explicitly reports this content absent."
                        ),
                        explanation=explanation,
                        evidence=[Evidence(source_id=1, quote=quote, supports=status)],
                    )
                )
            else:
                findings.append(Finding(concern=concern, status=Status.UNKNOWN))
        return Assessment(findings=findings)


def demo_report(concerns: list[str]) -> Report:
    movie = Movie(
        id=0,
        title="The Hollow House (fictional demo)",
        year=2026,
        runtime=93,
        genres=["Horror", "Mystery"],
        director="A. Example",
        overview="A caretaker investigates a house whose rooms keep getting smaller.",
    )
    report = screen(movie, concerns, DemoResearch(), DemoAssessor())
    report.demo = True
    return report
