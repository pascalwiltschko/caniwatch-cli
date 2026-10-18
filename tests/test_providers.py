import json

import httpx
import pytest
from pydantic import ValidationError

from caniwatch.application.errors import AppError
from caniwatch.application.service import screen
from caniwatch.config import Settings
from caniwatch.domain.models import Assessment, Finding, Movie, Research, Status
from caniwatch.providers.ollama import Ollama
from caniwatch.providers.tavily import Tavily
from caniwatch.providers.tmdb import TMDB

MOVIE = Movie(id=1, title="Fictional Film", year=2026)


def settings(**kwargs):
    return Settings(_env_file=None, **kwargs)


@pytest.mark.parametrize(
    "url",
    [
        "https://provider.example",
        "http://localhost:11434",
        "http://127.0.0.1.evil.example",
        "http://192.168.1.1:11434",
        "http://user:secret@127.0.0.1",
        "http://127.0.0.1/path",
        "http://127.0.0.1?remote=1",
        "http://127.0.0.1:invalid",
        "file:///tmp/socket",
    ],
)
def test_rejects_nonlocal_or_ambiguous_inference_urls(url):
    with pytest.raises(ValidationError):
        settings(ollama_url=url)


@pytest.mark.parametrize("url", ["http://127.0.0.1:11434", "http://[::1]:11434"])
def test_accepts_literal_loopback(url):
    assert settings(ollama_url=url).ollama_url == url


def test_privacy_research_requests_identical_for_different_concerns(caplog):
    requests = []

    def handle(request):
        requests.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "title": "Guide",
                        "url": "https://example.org/guide",
                        "raw_content": "A fictional content guide for Fictional Film (2026).",
                    }
                ],
                "usage": {"credits": 1},
            },
        )

    class UnknownAssessor:
        def assess(self, movie, research, concerns):
            return Assessment(
                findings=[Finding(concern=c, status=Status.UNKNOWN) for c in concerns]
            )

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        for concern in ("PRIVATE_FEAR_A", "PRIVATE_FEAR_B"):
            screen(MOVIE, [concern], Tavily(client, "SECRET_KEY"), UnknownAssessor())
    assert requests[:2] == requests[2:]
    assert all("PRIVATE_FEAR" not in json.dumps(request) for request in requests)
    assert all(request["auto_parameters"] is False for request in requests)
    assert all(request["include_answer"] is False for request in requests)
    assert "PRIVATE_FEAR" not in caplog.text
    assert "SECRET_KEY" not in caplog.text


def test_search_deduplicates_prefers_full_text_and_filters_excluded_domains():
    calls = 0

    def handle(request):
        nonlocal calls
        calls += 1
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "title": "Excerpt",
                        "url": "https://example.org/a#anchor",
                        "content": "Excerpt only",
                    },
                    {
                        "title": "Full",
                        "url": "https://example.org/a",
                        "raw_content": "Full source " * 2000,
                    },
                    {"url": "https://www.doesthedogdie.com/a", "content": "Excluded"},
                    {"url": "javascript:alert(1)", "content": "Bad URL"},
                ],
                "usage": {"credits": 1},
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        result = Tavily(client, "key").research(MOVIE)
    assert calls == result.searches == 2
    assert result.credits == 2
    assert len(result.sources) == 1
    assert result.sources[0].full_text
    assert len(result.sources[0].text) == 12_000


def test_search_partial_failure_retains_usable_excerpts():
    calls = 0

    def handle(request):
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(429, text="SECRET_PROVIDER_BODY")
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "url": "https://example.org/guide",
                        "content": "Partial evidence in a snippet.",
                    }
                ]
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        result = Tavily(client, "key").research(MOVIE)
    assert len(result.sources) == 1
    assert not result.sources[0].full_text
    assert result.credits is None
    assert any("failed" in item for item in result.limitations)
    assert "SECRET_PROVIDER_BODY" not in result.model_dump_json()


def test_tmdb_search_year_and_details():
    def handle(request):
        assert request.headers["Authorization"] == "Bearer secret"
        if request.url.path.endswith("search/movie"):
            assert request.url.params["primary_release_year"] == "2026"
            return httpx.Response(
                200,
                json={
                    "results": [
                        {
                            "id": 1,
                            "title": "Fictional Film",
                            "release_date": "2026-01-01",
                        }
                    ]
                },
            )
        return httpx.Response(
            200,
            json={
                "id": 1,
                "title": "Fictional Film",
                "release_date": "2026-01-01",
                "runtime": 90,
                "genres": [{"name": "Horror"}],
                "credits": {
                    "crew": [
                        {"name": "A Director", "job": "Director"},
                    ]
                },
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        provider = TMDB(client, "secret")
        assert provider.search("Fictional Film", 2026)[0].year == 2026
        movie = provider.details(1)
        assert movie.director == "A Director"
        assert movie.runtime == 90


def test_ollama_uses_schema_and_only_local_endpoint():
    def handle(request):
        assert request.url.host == "127.0.0.1"
        payload = json.loads(request.content)
        assert payload["model"] == "gemma4:e4b"
        assert payload["stream"] is False
        assert payload["format"]["properties"]["findings"]
        assert "tools" not in payload
        assert "PRIVATE_FEAR" in payload["messages"][1]["content"]
        assessment = Assessment(findings=[Finding(concern="PRIVATE_FEAR", status=Status.UNKNOWN)])
        return httpx.Response(200, json={"message": {"content": assessment.model_dump_json()}})

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        result = Ollama(client, settings()).assess(MOVIE, Research(), ["PRIVATE_FEAR"])
    assert result.findings[0].status == Status.UNKNOWN


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, json={"message": {"content": "PRIVATE_INVALID_OUTPUT"}}),
        httpx.Response(500, text="PRIVATE_FAILURE_BODY"),
        httpx.Response(200, text="PRIVATE_INVALID_JSON"),
    ],
)
def test_model_errors_are_sanitized(response):
    with (
        httpx.Client(transport=httpx.MockTransport(lambda _: response)) as client,
        pytest.raises(AppError) as exc,
    ):
        Ollama(client, settings()).assess(MOVIE, Research(), ["PRIVATE_FEAR"])
    assert "PRIVATE" not in str(exc.value)
