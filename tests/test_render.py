import io

import pytest
from rich.console import Console

from caniwatch.application.demo import DEMO_CONCERNS, demo_report
from caniwatch.application.service import validate_assessment
from caniwatch.cli.render import public_report, render_api_usage, render_report, summary
from caniwatch.domain.models import Assessment, Finding, Status


@pytest.mark.parametrize(
    ("statuses", "verdict", "reason"),
    [
        ([Status.PRESENT, Status.ABSENT], "I'd skip", "Sources report concern 0"),
        ([Status.CONFLICTING, Status.UNKNOWN], "I'd hold off", "disagree about concern 0"),
        ([Status.UNKNOWN, Status.ABSENT], "I'd hold off", "clear answer about concern 0"),
        (
            [Status.ABSENT, Status.ABSENT],
            "reasonable pick",
            "you want to avoid don't occur",
        ),
        ([], "I'd hold off", "no findings"),
    ],
)
def test_recommendation_explains_the_deciding_findings(statuses, verdict, reason):
    report = demo_report(DEMO_CONCERNS)
    report.assessment = Assessment(
        findings=[
            Finding(concern=f"concern {index}", status=status)
            for index, status in enumerate(statuses)
        ]
    )
    advice = summary(report)
    assert verdict in advice
    assert reason in advice
    assert public_report(report, details=False)["summary"] == advice


def test_present_content_takes_priority_but_acknowledges_unresolved_findings():
    report = demo_report(DEMO_CONCERNS)
    advice = summary(report)
    assert "I'd skip" in advice
    assert "claustrophobia" in advice
    assert "other concerns are still unclear" in advice
    assert "reasonable pick" not in advice


def test_recommendation_uses_validated_findings_instead_of_unsupported_model_claims():
    report = demo_report(["animal harm"])
    # Removing the cited source invalidates the model's absence claim.
    report.research.sources = []
    report.assessment = validate_assessment(report.assessment, report.research, ["animal harm"])
    assert "I'd hold off" in summary(report)
    assert "animal harm" in summary(report)
    assert "reasonable pick" not in summary(report)


@pytest.mark.parametrize("count", [1, 20])
def test_long_concerns_keep_recommendation_compact(count):
    report = demo_report(DEMO_CONCERNS)
    report.assessment = Assessment(
        findings=[
            Finding(concern=f"{index} " + "x" * 190, status=Status.PRESENT)
            for index in range(count)
        ]
    )
    advice = summary(report)
    assert "I'd skip" in advice
    assert "one of your concerns" in advice if count == 1 else "20 of your concerns" in advice
    assert len(advice) < 240


def test_classifications_are_compact_in_the_film_panel_and_in_json():
    report = demo_report(DEMO_CONCERNS)
    report.demo = False
    stream = io.StringIO()
    render_report(report, Console(file=stream, width=80), details=False)
    output = stream.getvalue()
    assert "Your Assessment" in output
    assert "Private matching:" not in output
    assert "Public research:" not in output
    assert "Age classifications: FSK 16 · US R · UK 15" in output
    assert (
        output.index(" Film ")
        < output.index("Age classifications")
        < output.index("Your Assessment")
    )
    data = public_report(report, details=False)
    assert data["movie"]["age_classifications"] == {"DE": ["16"], "US": ["R"], "GB": ["15"]}


def test_long_classification_line_wraps_without_losing_certifications():
    report = demo_report(DEMO_CONCERNS)
    report.demo = False
    report.movie.age_classifications = {
        "DE": ["16", "18"],
        "US": ["R", "NC-17"],
        "GB": ["15", "18"],
    }
    stream = io.StringIO()
    render_report(report, Console(file=stream, width=40), details=False)
    film = stream.getvalue().split("Your Assessment", 1)[0]
    unwrapped = " ".join(film.replace("│", " ").split())
    assert "Age classifications: FSK 16 / 18 · US R / NC-17 · UK 15 / 18" in unwrapped


def test_missing_classifications_are_omitted():
    report = demo_report(DEMO_CONCERNS)
    report.movie.age_classifications = {}
    stream = io.StringIO()
    render_report(report, Console(file=stream, width=80), details=False)
    assert "Age classifications" not in stream.getvalue()
    assert "age_classifications" not in public_report(report, details=False)["movie"]


def test_demo_classifications_are_labeled_fictional():
    stream = io.StringIO()
    render_report(demo_report(DEMO_CONCERNS), Console(file=stream, width=80), details=False)
    assert "Age classifications (fictional demo): FSK 16 · US R · UK 15" in stream.getvalue()


@pytest.mark.parametrize(
    ("statuses", "color"),
    [
        ([Status.ABSENT], "32"),
        ([Status.ABSENT, Status.UNKNOWN], "33"),
        ([Status.UNKNOWN, Status.PRESENT], "31"),
        ([Status.CONFLICTING, Status.UNKNOWN], "31"),
    ],
)
def test_panel_colors_follow_verdict_and_film_stays_neutral(statuses, color):
    report = demo_report(DEMO_CONCERNS)
    report.assessment = Assessment(
        findings=[
            Finding(concern=str(index), status=status) for index, status in enumerate(statuses)
        ]
    )
    stream = io.StringIO()
    render_report(
        report,
        Console(
            file=stream, width=80, force_terminal=True, color_system="standard", no_color=False
        ),
        details=False,
    )
    lines = stream.getvalue().splitlines()
    verdict_border = next(line for line in lines if "Your Assessment" in line)
    assert f"\x1b[{color}m" in verdict_border
    film_border = next(line for line in lines if " Film " in line)
    assert "\x1b[2m" in film_border
    assert all(f"\x1b[{code}m" not in film_border for code in ("31", "32", "33", "35", "36"))


@pytest.mark.parametrize("width", [40, 80, 120])
@pytest.mark.parametrize("details", [False, True])
def test_comments_are_visible_without_disclosing_scene_details(width, details):
    report = demo_report(["claustrophobia"])
    finding = report.assessment.findings[0]
    finding.comment = "Evidence is explicit."
    finding.explanation = "SCENE_DETAIL"
    stream = io.StringIO()
    render_report(report, Console(file=stream, width=width), details=details)
    output = stream.getvalue()
    if width >= 60:
        rows = [
            line.split("│")[1:-1]
            for line in output.splitlines()
            if line.count("│") == (6 if details else 5)
        ]
        comment = " ".join(row[2].strip() for row in rows)
        scenes = " ".join(row[3].strip() for row in rows) if details else output
    else:
        comment = scenes = " ".join(output.split())
    assert "Evidence is explicit." in comment
    assert ("SCENE_DETAIL" in scenes) is details
    assert ("locked, narrow cellar" in scenes) is details
    assert "[1]" in output
    if width >= 60:
        header = next(
            line for line in output.splitlines() if "Finding" in line and "Comment" in line
        )
        assert header.index("Finding") < header.index("Comment") < header.index("Sources")
        assert ("Details" in header) is details
        if details:
            assert header.index("Comment") < header.index("Details") < header.index("Sources")
            after_table = output.split("└", 1)[1]
            assert "SCENE_DETAIL" not in after_table
            assert "locked, narrow cellar" not in after_table
    else:
        assert "Sources: [1]" in output


def test_footer_separates_sources_disclaimers_and_final_usage():
    report = demo_report(DEMO_CONCERNS)
    report.demo = False
    report.research.limitations = [
        "Bounded web research can miss content, rare triggers, or alternate cuts.",
        "Research query 2 failed: Search timed out.",
    ]
    report.research.searches = 2
    report.research.credits = 2.0
    stream = io.StringIO()
    render_report(report, Console(file=stream, width=160), details=False, api_usage=True)
    output = stream.getvalue()
    assert (
        "https://example.org/caniwatch-demo\n\nDisclaimers\n• AI assessments can be wrong."
        in output
    )
    assert "\n• Bounded web research can miss content" in output
    assert "\n• Research query 2 failed" in output
    assert "\n• Movie metadata: TMDB. This product uses the TMDB API" in output
    assert "not endorsed or certified by TMDB" in output
    assert "https://www.themoviedb.org\n\nAPI Usage:\n" in output
    assert output.rstrip().endswith("API Usage:\n• TMDB: 2 requests\n• Tavily: 2 credits used")


@pytest.mark.parametrize("credits", [2, 0, 0.5, None])
def test_usage_displays_only_reported_credits(credits):
    report = demo_report(DEMO_CONCERNS)
    report.demo = False
    report.tmdb_requests = None
    report.research.credits = credits
    stream = io.StringIO()
    render_api_usage(report, Console(file=stream, width=80))
    output = stream.getvalue()
    data = public_report(report, details=False, api_usage=True)
    if credits is None:
        assert output == ""
        assert "credits" not in data["research"]
    else:
        assert output == f"\nAPI Usage:\n• Tavily: {credits:g} credits used\n"
        assert data["research"]["credits"] == credits


def test_tmdb_requests_remain_visible_without_tavily_credit_data():
    report = demo_report(DEMO_CONCERNS)
    report.demo = False
    report.research.credits = None
    stream = io.StringIO()
    render_api_usage(report, Console(file=stream, width=80))
    assert stream.getvalue() == "\nAPI Usage:\n• TMDB: 2 requests\n"
