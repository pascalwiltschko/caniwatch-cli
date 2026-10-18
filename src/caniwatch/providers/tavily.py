"""Fixed, bounded public research with no preference-dependent decisions."""

import logging
from urllib.parse import urlsplit, urlunsplit

import httpx
from pydantic import ValidationError

from caniwatch.application.errors import AppError
from caniwatch.domain.models import Movie, Research, Source
from caniwatch.providers.http import request_json

logger = logging.getLogger(__name__)
QUERY_SUFFIXES = ("parents guide content advisory", "content warnings detailed review")
MAX_SOURCES = 4
MAX_SOURCE_CHARS = 12_000
EXCLUDED_DOMAINS = ["doesthedogdie.com"]


class Tavily:
    def __init__(self, client: httpx.Client, api_key: str):
        self.client = client
        self.api_key = api_key

    def research(self, movie: Movie) -> Research:
        sources: dict[str, Source] = {}
        limitations = []
        credits = 0.0
        usage_known = True
        for index, suffix in enumerate(QUERY_SUFFIXES, start=1):
            try:
                data = request_json(
                    self.client,
                    "POST",
                    "https://api.tavily.com/search",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "query": f'"{movie.title}" {movie.year or ""} {suffix}',
                        "search_depth": "basic",
                        "max_results": MAX_SOURCES,
                        "include_raw_content": "text",
                        "include_answer": False,
                        "include_images": False,
                        "auto_parameters": False,
                        "include_usage": True,
                        "exclude_domains": EXCLUDED_DOMAINS,
                    },
                )
                results = data.get("results")
                if not isinstance(results, list):
                    raise AppError("Search returned invalid results.")
                usage = data.get("usage", {})
                amount = usage.get("credits") if isinstance(usage, dict) else None
                if isinstance(amount, (int, float)):
                    credits += amount
                else:
                    usage_known = False
                for item in results[:MAX_SOURCES]:
                    if not isinstance(item, dict):
                        continue
                    try:
                        parts = urlsplit(str(item.get("url", "")))
                        hostname = (parts.hostname or "").lower()
                        if (
                            parts.scheme not in {"https", "http"}
                            or not hostname
                            or parts.username
                            or parts.password
                            or any(
                                hostname == d or hostname.endswith(f".{d}")
                                for d in EXCLUDED_DOMAINS
                            )
                        ):
                            continue
                        url = urlunsplit(parts._replace(fragment=""))
                        raw = item.get("raw_content")
                        full_text = isinstance(raw, str) and bool(raw.strip())
                        text = raw if full_text else item.get("content")
                        if not isinstance(text, str) or not text.strip():
                            continue
                        source = Source(
                            id=0,
                            title=str(item.get("title") or "Untitled source"),
                            url=url,
                            text=text[:MAX_SOURCE_CHARS],
                            full_text=full_text,
                        )
                        previous = sources.get(url)
                        if previous is None or (full_text and not previous.full_text):
                            sources[url] = source
                    except (ValueError, ValidationError):
                        continue
            except AppError as exc:
                logger.warning("stage=search_failed request=%d", index)
                limitations.append(f"Research query {index} failed: {exc}")
                usage_known = False

        selected = sorted(sources.values(), key=lambda source: not source.full_text)[:MAX_SOURCES]
        selected = [source.model_copy(update={"id": i}) for i, source in enumerate(selected, 1)]
        if not selected:
            limitations.append("No usable sources were retrieved; all concerns remain unknown.")
        if any(not source.full_text for source in selected):
            limitations.append(
                "Some evidence is limited to search excerpts rather than full pages."
            )
        limitations.append(
            "Bounded web research can miss content, rare triggers, or alternate cuts."
        )
        return Research(
            sources=selected,
            limitations=limitations,
            searches=len(QUERY_SUFFIXES),
            credits=credits if usage_known else None,
        )
