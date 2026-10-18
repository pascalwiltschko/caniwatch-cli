"""Coordinate public research and verify provenance for private findings."""

import logging
from collections import Counter
from time import perf_counter

from caniwatch.application.errors import AppError
from caniwatch.application.ports import Assessor, ResearchProvider
from caniwatch.domain.models import Assessment, Finding, Movie, Report, Research, Status

logger = logging.getLogger(__name__)


def normalize_concerns(values: list[str]) -> list[str]:
    concerns = list(dict.fromkeys(value.strip() for value in values if value.strip()))
    if not concerns or len(concerns) > 20 or any(len(value) > 200 for value in concerns):
        raise AppError("Provide 1-20 concerns, each at most 200 characters.")
    return concerns


def validate_assessment(
    assessment: Assessment, research: Research, concerns: list[str]
) -> Assessment:
    """Reject missing/extra findings and downgrade unsupported claims to unknown."""
    if Counter(f.concern for f in assessment.findings) != Counter(concerns):
        raise AppError(
            "The local model returned mismatched concerns. Try again or change the model."
        )
    sources = {source.id: " ".join(source.text.split()) for source in research.sources}
    by_concern = {finding.concern: finding for finding in assessment.findings}
    validated = []
    for concern in concerns:
        finding = by_concern[concern]
        valid = [
            item
            for item in finding.evidence
            if item.supports in {Status.PRESENT, Status.ABSENT}
            and item.source_id in sources
            and len(" ".join(item.quote.split())) >= 12
            and " ".join(item.quote.split()) in sources[item.source_id]
        ]
        supported = {item.supports for item in valid}
        required = (
            {Status.PRESENT, Status.ABSENT}
            if finding.status == Status.CONFLICTING
            else {finding.status}
        )
        if finding.status == Status.UNKNOWN or not required <= supported:
            validated.append(
                Finding(
                    concern=concern,
                    status=Status.UNKNOWN,
                    explanation="Insufficient verifiable evidence in the retrieved sources.",
                )
            )
        else:
            # Opposing evidence must not be hidden by a model's single-sided label.
            status = Status.CONFLICTING if len(supported) == 2 else finding.status
            validated.append(finding.model_copy(update={"status": status, "evidence": valid}))
    return Assessment(findings=validated)


def screen(
    movie: Movie, concerns: list[str], researcher: ResearchProvider, assessor: Assessor
) -> Report:
    concerns = normalize_concerns(concerns)
    start = perf_counter()
    logger.info("stage=research_started")
    research = researcher.research(movie)
    logger.info(
        "stage=research_finished sources=%d searches=%d elapsed_ms=%d",
        len(research.sources),
        research.searches,
        (perf_counter() - start) * 1000,
    )
    if research.sources:
        logger.info("stage=assessment_started")
        assessment = validate_assessment(
            assessor.assess(movie, research, concerns), research, concerns
        )
    else:
        assessment = Assessment(
            findings=[Finding(concern=value, status=Status.UNKNOWN) for value in concerns]
        )
    logger.info("stage=report_ready elapsed_ms=%d", (perf_counter() - start) * 1000)
    return Report(movie=movie, research=research, assessment=assessment)
