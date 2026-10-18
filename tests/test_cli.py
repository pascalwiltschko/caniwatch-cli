import io
import json
from pathlib import Path

import httpx
import pytest
import typer
from rich.console import Console
from typer.testing import CliRunner

from caniwatch.application.demo import DEMO_CONCERNS, demo_report
from caniwatch.cli.main import app, choose_movie, watch
from caniwatch.cli.render import render_report
from caniwatch.domain.models import Movie

runner = CliRunner()


def test_demo_runs_offline_and_json_hides_details():
    result = runner.invoke(app, ["--demo", "--json"])
    assert result.exit_code == 0, result.output
    report = json.loads(result.stdout)
    assert report["demo"] is True
    assert "searches" not in report["research"]
    assert "credits" not in report["research"]
    assert "tmdb_requests" not in report
    assert "overview" not in report["movie"]
    assert all("text" not in source for source in report["research"]["sources"])
    assert all("explanation" not in f for f in report["assessment"]["findings"])
    assert report["assessment"]["findings"][0]["comment"] == (
        "The fictional guide confirms this is in the film, so I'd keep that in mind."
    )
    assert "locked, narrow cellar" not in result.stdout
    assert [f["status"] for f in report["assessment"]["findings"]] == [
        "reported_present",
        "reported_absent",
        "unknown",
    ]


def test_details_are_explicit_and_terminal_demo_is_labeled():
    details = runner.invoke(app, ["--demo", "--json", "--details"])
    assert details.exit_code == 0
    assert "locked, narrow cellar" in details.stdout
    result = runner.invoke(app, ["--demo"])
    assert result.exit_code == 0
    assert "OFFLINE DEMO" in result.stdout
    assert "Reported present" in result.stdout


@pytest.mark.parametrize("details", [False, True])
def test_api_usage_requires_explicit_option_for_live_reports(monkeypatch, details):
    import importlib

    cli = importlib.import_module("caniwatch.cli.main")
    report = demo_report(DEMO_CONCERNS)
    report.demo = False
    monkeypatch.setattr(cli, "run_live", lambda *args, **kwargs: report)
    arguments = ["Film", "--avoid", "spiders", *(["--details"] if details else [])]
    hidden = runner.invoke(app, arguments)
    assert hidden.exit_code == 0, hidden.output
    assert "API Usage:" not in hidden.stdout
    assert "credits used" not in hidden.stdout
    visible = runner.invoke(app, [*arguments, "--api-usage"])
    assert visible.exit_code == 0, visible.output
    assert "API Usage:" in visible.stdout
    assert "API Usage:\n• TMDB: 2 requests\n• Tavily: 2 credits used" in visible.stdout


def test_demo_shows_fictional_api_usage_without_extra_option():
    result = runner.invoke(app, ["--demo"])
    assert result.exit_code == 0, result.output
    assert "API Usage: (fictional demo)" in result.stdout
    assert "• TMDB: 2 requests" in result.stdout
    assert result.stdout.rstrip().endswith("• Tavily: 2 credits used")


def test_demo_json_api_usage_is_explicit_and_offline():
    result = runner.invoke(app, ["--demo", "--json", "--api-usage"])
    assert result.exit_code == 0, result.output
    report = json.loads(result.stdout)
    assert report["demo"] is True
    assert "searches" not in report["research"]
    assert report["research"]["credits"] == 2
    assert report["tmdb_requests"] == 2


@pytest.mark.parametrize(
    "arguments",
    [
        [],
        ["Terrifier"],
        ["--demo", "Terrifier"],
        ["--doctor", "--json"],
        ["--doctor", "--api-usage"],
        ["--doctor", "--director", "Jane Smith"],
        ["--demo", "--director", "Jane Smith"],
        ["Film", "--director", "   "],
        ["Film", "--year", "1000"],
    ],
)
def test_usage_errors(arguments):
    result = runner.invoke(app, arguments)
    assert result.exit_code == 2


def test_missing_credentials_is_actionable():
    result = runner.invoke(app, ["Terrifier", "--avoid", "spiders", "--json"])
    assert result.exit_code == 1
    assert result.stdout == ""
    assert "CANIWATCH_TMDB_TOKEN" in result.stderr
    assert "Traceback" not in result.output


def test_rejects_remote_model_without_leaking_config(monkeypatch):
    monkeypatch.setenv("CANIWATCH_OLLAMA_URL", "https://private-fear.example")
    result = runner.invoke(app, ["Film", "--avoid", "spiders", "--json"])
    assert result.exit_code == 1
    assert "loopback" in result.stderr
    assert "private-fear" not in result.output


@pytest.mark.parametrize("api_usage", [False, True])
@pytest.mark.parametrize("director", [None, "  TEST   director  "])
def test_live_pipeline_with_mocked_http_and_no_private_research(monkeypatch, api_usage, director):
    monkeypatch.setenv("CANIWATCH_TMDB_TOKEN", "TMDB_SECRET")
    monkeypatch.setenv("CANIWATCH_TAVILY_API_KEY", "TAVILY_SECRET")
    requests = []
    clients = []
    original_client = httpx.Client

    def handle(request):
        requests.append(request)
        if request.url.path.endswith("search/movie"):
            assert "director" not in request.url.params
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "id": 1,
                            "title": "Test Film",
                            "release_date": "2026-01-01",
                        },
                        *(
                            [{"id": 2, "title": "Test Film", "release_date": "2026-01-01"}]
                            if director
                            else []
                        ),
                    ]
                },
            )
        if request.url.host == "api.themoviedb.org":
            return httpx.Response(
                200,
                json={
                    "id": 2 if request.url.path.endswith("/2") else 1,
                    "title": "Test Film",
                    "release_date": "2026-01-01",
                    "runtime": 90,
                    "credits": {
                        "crew": [
                            {
                                "job": "Director",
                                "name": "Other Director"
                                if request.url.path.endswith("/2")
                                else "Test Director",
                            }
                        ]
                    },
                },
            )
        if request.url.host == "api.tavily.com":
            assert request.url.path == "/search"
            assert request.method == "POST"
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "title": "Test Film (2026) guide",
                            "url": "https://example.org/guide",
                            "raw_content": "Test Film (2026): There are spiders in the cellar.",
                        }
                    ],
                    "usage": {"credits": 1},
                },
            )
        assert request.url.host == "127.0.0.1"
        payload = json.loads(request.content)
        if "ready" in payload["format"]["properties"]:
            return httpx.Response(200, json={"message": {"content": '{"ready": true}'}})
        assert "PRIVATE_CONCERN" in payload["messages"][1]["content"]
        return httpx.Response(
            200,
            json={
                "message": {
                    "content": json.dumps(
                        {
                            "findings": [
                                {
                                    "concern": "PRIVATE_CONCERN",
                                    "status": "reported_present",
                                    "explanation": "Relevant content described.",
                                    "evidence": [
                                        {
                                            "source_id": 1,
                                            "quote": "There are spiders in the cellar.",
                                            "supports": "reported_present",
                                        }
                                    ],
                                }
                            ]
                        }
                    )
                }
            },
        )

    def client(**kwargs):
        clients.append(kwargs)
        return original_client(transport=httpx.MockTransport(handle), **kwargs)

    monkeypatch.setattr(httpx, "Client", client)
    result = runner.invoke(
        app,
        [
            "Test Film",
            "--year",
            "2026",
            "--avoid",
            "PRIVATE_CONCERN",
            "--json",
            "--verbose",
            "--log-file",
            "test.log",
            *(["--api-usage"] if api_usage else []),
            *(["--director", director] if director else []),
        ],
    )
    assert result.exit_code == 0, result.output
    report = json.loads(result.stdout)
    assert report["assessment"]["findings"][0]["status"] == "reported_present"
    assert report["movie"]["id"] == 1
    assert report["movie"]["director"] == "Test Director"
    # Compatibility, movie search/candidate details, two content searches, assessment.
    assert len(requests) == (7 if director else 6)
    assert "searches" not in report["research"]
    if api_usage:
        assert report["research"]["credits"] == 2
        assert report["tmdb_requests"] == (3 if director else 2)
    else:
        assert "credits" not in report["research"]
        assert "tmdb_requests" not in report
    for request in requests:
        if request.url.host != "127.0.0.1":
            assert "PRIVATE_CONCERN" not in str(request.url)
            assert b"PRIVATE_CONCERN" not in request.content
    assert clients[1]["trust_env"] is False
    assert all(client["follow_redirects"] is False for client in clients)
    logs = Path("test.log").read_text()
    for private in (
        "PRIVATE_CONCERN",
        "TMDB_SECRET",
        "TAVILY_SECRET",
        "spiders in the cellar",
    ):
        assert private not in logs
        assert private not in result.stderr
    assert "stage=report_ready" in logs


def test_doctor_only_contacts_local_model(monkeypatch):
    original_client = httpx.Client

    def handle(request):
        assert request.url.host == "127.0.0.1"
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "gemma4:e4b-it-q4_K_M"}]})
        return httpx.Response(200, json={"message": {"content": '{"ready": true}'}})

    monkeypatch.setattr(
        httpx,
        "Client",
        lambda **kw: original_client(
            transport=httpx.MockTransport(handle),
            **kw,
        ),
    )
    result = runner.invoke(app, ["--doctor"])
    assert result.exit_code == 1  # Credentials absent, even though model is ready.
    assert "missing credential" in result.stderr
    assert "model available" in result.stderr


def test_ambiguous_title_requires_selection_and_does_not_silently_pick():
    console = Console(file=io.StringIO())
    movies = [Movie(id=1, title="Film", year=2000), Movie(id=2, title="Film", year=2020)]
    with pytest.raises(typer.BadParameter, match="Ambiguous"):
        choose_movie(movies, interactive=False, console=console)


def test_interactive_concern_prompt_is_visible(monkeypatch):
    import importlib

    cli = importlib.import_module("caniwatch.cli.main")
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: True)
    observed = []

    def prompt(message, **kwargs):
        assert kwargs["hide_input"] is False
        assert kwargs["err"] is True
        return "claustrophobia, animal harm"

    def live(settings, title, year, concerns, *args, **kwargs):
        observed.extend(concerns)
        return demo_report(concerns)

    monkeypatch.setattr(typer, "prompt", prompt)
    monkeypatch.setattr(cli, "run_live", live)
    watch(
        title="Film",
        year=None,
        avoid=None,
        details=False,
        json_output=False,
        demo=False,
        doctor=False,
        verbose=False,
        log_file=None,
    )
    assert observed == ["claustrophobia", "animal harm"]


def test_prompt_cancellation_returns_130(monkeypatch):
    import importlib

    cli = importlib.import_module("caniwatch.cli.main")
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: True)

    def cancel(*args, **kwargs):
        raise typer.Abort()

    monkeypatch.setattr(typer, "prompt", cancel)
    with pytest.raises(typer.Exit) as exc:
        watch(
            title="Film",
            year=None,
            avoid=None,
            details=False,
            json_output=False,
            demo=False,
            doctor=False,
            verbose=False,
            log_file=None,
        )
    assert exc.value.exit_code == 130


@pytest.mark.parametrize("width", [40, 80, 120])
def test_report_handles_narrow_and_wide_terminals(width):
    stream = io.StringIO()
    render_report(demo_report(DEMO_CONCERNS), Console(file=stream, width=width), details=False)
    output = stream.getvalue()
    assert "OFFLINE DEMO" in output
    assert "claustrophobia" in output
    assert "locked, narrow cellar" not in output


def test_json_output_file_is_complete_and_stdout_empty(tmp_path):
    output = tmp_path / "report.json"
    output.write_text("old report")
    result = runner.invoke(app, ["--demo", "--json", "--details", "--output", str(output)])
    assert result.exit_code == 0, result.output
    assert result.stdout == ""
    assert json.loads(output.read_text())["demo"] is True
    assert "locked, narrow cellar" in output.read_text()
    assert not list(tmp_path.glob(".caniwatch-*"))


@pytest.mark.parametrize("existing", [False, True])
def test_failed_assessment_preserves_output_and_logs_safe_diagnostics(
    monkeypatch, tmp_path, existing
):
    import importlib

    from caniwatch.application.errors import AppError

    cli = importlib.import_module("caniwatch.cli.main")
    output = tmp_path / "report.json"
    if existing:
        output.write_text("previous report")

    def fail(*args, **kwargs):
        raise AppError("Ollama assessment failed (HTTP 501). Requested capability is unavailable.")

    monkeypatch.setattr(cli, "run_live", fail)
    log = tmp_path / "run.log"
    result = runner.invoke(
        app,
        [
            "Film",
            "--avoid",
            "PRIVATE_CONCERN",
            "--json",
            "--output",
            str(output),
            "--log-file",
            str(log),
        ],
    )
    assert result.exit_code == 1
    assert result.stdout == ""
    assert "Ollama assessment failed (HTTP 501)" in result.stderr
    assert "Ollama assessment failed (HTTP 501)" in log.read_text()
    assert "PRIVATE_CONCERN" not in log.read_text() + result.stderr
    if existing:
        assert output.read_text() == "previous report"
    else:
        assert not output.exists()
    assert not list(tmp_path.glob(".caniwatch-*"))


def test_output_replace_failure_keeps_existing_report_and_cleans_temporary(monkeypatch, tmp_path):
    output = tmp_path / "report.json"
    output.write_text("previous report")

    def fail(*args, **kwargs):
        raise OSError("PRIVATE filesystem message")

    monkeypatch.setattr(Path, "replace", fail)
    result = runner.invoke(app, ["--demo", "--json", "--output", str(output)])
    assert result.exit_code == 1
    assert output.read_text() == "previous report"
    assert "PRIVATE" not in result.output
    assert not list(tmp_path.glob(".caniwatch-*"))


def test_output_requires_json(tmp_path):
    output = tmp_path / "report.json"
    result = runner.invoke(app, ["--demo", "--output", str(output)])
    assert result.exit_code == 2
    assert not output.exists()


@pytest.mark.parametrize("doctor", [False, True])
def test_incompatible_backend_fails_before_public_research(monkeypatch, tmp_path, doctor):
    monkeypatch.setenv("CANIWATCH_TMDB_TOKEN", "TMDB_SECRET")
    monkeypatch.setenv("CANIWATCH_TAVILY_API_KEY", "TAVILY_SECRET")
    original_client = httpx.Client
    requests = []

    def handle(request):
        requests.append(request)
        assert request.url.host == "127.0.0.1"
        if request.url.path == "/api/tags":
            return httpx.Response(200, json={"models": [{"name": "gemma4:e4b-it-q4_K_M"}]})
        assert b"PRIVATE_CONCERN" not in request.content
        return httpx.Response(501, json={"error": "PRIVATE_BODY"})

    monkeypatch.setattr(
        httpx, "Client", lambda **kw: original_client(transport=httpx.MockTransport(handle), **kw)
    )
    output = tmp_path / "report.json"
    log = tmp_path / "run.log"
    arguments = (
        ["--doctor"]
        if doctor
        else ["Film", "--avoid", "PRIVATE_CONCERN", "--json", "--output", str(output)]
    )
    result = runner.invoke(app, [*arguments, "--log-file", str(log)])
    assert result.exit_code == 1, result.output
    assert not output.exists()
    assert result.stdout == ""
    assert "Ollama compatibility failed (HTTP 501)" in result.stderr
    assert "GGUF" in result.stderr
    logs = log.read_text()
    assert "operation=compatibility" in logs
    assert "http_status=501" in logs
    assert "PRIVATE" not in logs + result.stderr
    assert len(requests) == (2 if doctor else 1)


def test_report_cannot_also_be_the_log_file(tmp_path):
    output = tmp_path / "report.json"
    output.write_text("previous report")
    result = runner.invoke(
        app,
        ["--demo", "--json", "--output", str(output), "--log-file", str(output)],
    )
    assert result.exit_code == 2
    assert output.read_text() == "previous report"
