import pytest

from caniwatch.application.errors import AppError
from caniwatch.application.service import normalize_concerns, screen, validate_assessment
from caniwatch.domain.models import (
    Assessment,
    Evidence,
    Finding,
    Movie,
    Research,
    Source,
    Status,
)


def research() -> Research:
    return Research(
        sources=[
            Source(
                id=1,
                title="Guide",
                url="https://example.org/guide",
                text="There are spiders on screen. No animals are harmed.",
                full_text=True,
            )
        ]
    )


def test_rejects_hallucinated_quotes_and_source_ids():
    findings = [
        Finding(
            concern="spiders",
            status=Status.PRESENT,
            comment="Unsupported private model claim.",
            evidence=[
                Evidence(
                    source_id=1, quote="A spider attacks the protagonist.", supports=Status.PRESENT
                ),
            ],
        ),
        Finding(
            concern="animals",
            status=Status.ABSENT,
            evidence=[
                Evidence(source_id=9, quote="No animals are harmed.", supports=Status.ABSENT),
            ],
        ),
    ]
    result = validate_assessment(Assessment(findings=findings), research(), ["spiders", "animals"])
    assert all(f.status == Status.UNKNOWN and not f.evidence for f in result.findings)
    assert all(
        f.comment == "I couldn't find clear evidence for this in the available sources."
        for f in result.findings
    )


def test_accepts_traceable_evidence_and_preserves_order():
    assessment = Assessment(
        findings=[
            Finding(
                concern="animals",
                status=Status.ABSENT,
                evidence=[
                    Evidence(
                        source_id=1,
                        quote="No animals are harmed.",
                        supports=Status.ABSENT,
                    )
                ],
            ),
            Finding(
                concern="spiders",
                status=Status.PRESENT,
                comment="The guide explicitly reports this content.",
                evidence=[
                    Evidence(
                        source_id=1,
                        quote="There are spiders on screen.",
                        supports=Status.PRESENT,
                    )
                ],
            ),
        ]
    )
    result = validate_assessment(assessment, research(), ["spiders", "animals"])
    assert [f.status for f in result.findings] == [Status.PRESENT, Status.ABSENT]
    assert result.findings[0].comment == "The guide explicitly reports this content."


def test_conflict_requires_both_sides_and_promotes_opposing_evidence():
    evidence = [
        Evidence(source_id=1, quote="There are spiders on screen.", supports=Status.PRESENT),
        Evidence(source_id=1, quote="No animals are harmed.", supports=Status.ABSENT),
    ]
    # Provenance alone cannot establish semantic relevance; this is an explicit limitation.
    finding = Finding(concern="test", status=Status.CONFLICTING, evidence=evidence[:1])
    assert (
        validate_assessment(Assessment(findings=[finding]), research(), ["test"]).findings[0].status
        == Status.UNKNOWN
    )
    finding.status = Status.PRESENT
    finding.comment = "The sources agree."
    finding.evidence = evidence
    result = validate_assessment(Assessment(findings=[finding]), research(), ["test"]).findings[0]
    assert result.status == Status.CONFLICTING
    assert result.comment == "The sources disagree on this, so I'd treat it with caution."


@pytest.mark.parametrize("findings", [[], [Finding(concern="extra", status=Status.UNKNOWN)]])
def test_rejects_missing_or_extra_concerns(findings):
    with pytest.raises(AppError, match="mismatched"):
        validate_assessment(Assessment(findings=findings), research(), ["spiders"])


def test_no_sources_does_not_call_model():
    class EmptyResearch:
        def research(self, movie):
            return Research()

    class NeverAssess:
        def assess(self, movie, research, concerns):
            pytest.fail("No source material must not invoke inference")

    report = screen(Movie(id=1, title="Test"), ["spiders"], EmptyResearch(), NeverAssess())
    assert report.assessment.findings[0].status == Status.UNKNOWN
    assert (
        report.assessment.findings[0].comment
        == "I couldn't find usable sources to check this for you."
    )


def test_concern_limits_and_deduplication():
    assert normalize_concerns([" spiders ", "", "spiders"]) == ["spiders"]
    for values in ([], ["x" * 201], [str(i) for i in range(21)]):
        with pytest.raises(AppError):
            normalize_concerns(values)
