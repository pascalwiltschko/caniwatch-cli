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
    finding.evidence = evidence
    assert (
        validate_assessment(Assessment(findings=[finding]), research(), ["test"]).findings[0].status
        == Status.CONFLICTING
    )


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


def test_concern_limits_and_deduplication():
    assert normalize_concerns([" spiders ", "", "spiders"]) == ["spiders"]
    for values in ([], ["x" * 201], [str(i) for i in range(21)]):
        with pytest.raises(AppError):
            normalize_concerns(values)
