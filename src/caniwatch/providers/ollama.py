"""Local-only structured inference; no tools, redirects, or proxy inheritance."""

import json
from importlib.resources import files

import httpx
from pydantic import ValidationError

from caniwatch.application.errors import AppError
from caniwatch.config import Settings
from caniwatch.domain.models import Assessment, Movie, Research
from caniwatch.providers.http import request_json


class Ollama:
    def __init__(self, client: httpx.Client, settings: Settings):
        self.client = client
        self.url = settings.ollama_url
        self.model = settings.model

    def available_models(self) -> list[str]:
        data = request_json(self.client, "GET", f"{self.url}/api/tags")
        try:
            return [item["name"] for item in data["models"]]
        except (KeyError, TypeError):
            raise AppError("Ollama returned invalid model information.") from None

    def assess(self, movie: Movie, research: Research, concerns: list[str]) -> Assessment:
        prompt = files("caniwatch.prompts").joinpath("assessment.md").read_text(encoding="utf-8")
        data = request_json(
            self.client,
            "POST",
            f"{self.url}/api/chat",
            json={
                "model": self.model,
                "stream": False,
                "format": Assessment.model_json_schema(),
                "options": {"temperature": 0.1, "num_predict": 4096, "num_ctx": 16384},
                "messages": [
                    {"role": "system", "content": prompt},
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "movie": {"title": movie.title, "year": movie.year},
                                "sources": [
                                    source.model_dump(mode="json") for source in research.sources
                                ],
                                "concerns": concerns,
                            }
                        ),
                    },
                ],
            },
        )
        try:
            return Assessment.model_validate_json(data["message"]["content"])
        except (KeyError, TypeError, ValueError, ValidationError):
            raise AppError(
                "Ollama returned an invalid assessment. Retry or choose another local model."
            ) from None
