import io

import pytest
from rich.console import Console

from caniwatch.application.demo import DEMO_CONCERNS, demo_report
from caniwatch.cli.render import render_report
from caniwatch.domain.models import Assessment, Finding, Status


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
    verdict_border = next(line for line in lines if "Your assessment" in line)
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
    assert "Evidence is explicit." in output
    assert ("SCENE_DETAIL" in output) is details
    assert ("locked, narrow cellar" in output) is details
    assert "[1]" in output
    if width >= 60:
        assert output.index("Finding") < output.index("Comment") < output.index("Sources")
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
    render_report(report, Console(file=stream, width=160), details=False)
    output = stream.getvalue()
    assert (
        "https://example.org/caniwatch-demo\n\nDisclaimers\n• AI assessments can be wrong."
        in output
    )
    assert "\n• Bounded web research can miss content" in output
    assert "\n• Research query 2 failed" in output
    assert "\n• Movie metadata: TMDB. This product uses the TMDB API" in output
    assert "not endorsed or certified by TMDB" in output
    assert "https://www.themoviedb.org\n\nResearch:" in output
    assert output.rstrip().endswith("Research: 2 searches · credits: 2.0")
