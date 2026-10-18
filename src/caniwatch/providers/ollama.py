"""Local-only structured inference; no tools, redirects, or proxy inheritance."""

import json
import logging
from importlib.resources import files
from typing import Literal

import httpx
from pydantic import ValidationError

from caniwatch.application.errors import AppError
from caniwatch.config import Settings
from caniwatch.domain.models import Assessment, Movie, Research
from caniwatch.providers.http import request_json

logger = logging.getLogger(__name__)


class Ollama:
    def __init__(self, client: httpx.Client, settings: Settings):
        self.client = client
        self.url = settings.ollama_url
        self.model = settings.model

    def available_models(self) -> list[str]:
        data = request_json(
            self.client, "GET", f"{self.url}/api/tags", provider="Ollama", operation="models"
        )
        try:
            return [item["name"] for item in data["models"]]
        except (KeyError, TypeError):
            raise AppError("Ollama returned invalid model information.") from None

    def check_compatibility(self) -> None:
        """Probe constrained generation locally before spending public research credits."""
        logger.info("provider=Ollama operation=compatibility stage=started")
        data = self._chat(
            {
                "model": self.model,
                "stream": False,
                "think": False,
                "format": {
                    "type": "object",
                    "properties": {"ready": {"type": "boolean", "const": True}},
                    "required": ["ready"],
                    "additionalProperties": False,
                },
                "options": {"temperature": 0, "num_predict": 32, "num_ctx": 16384},
                # Deliberately conflicts with the schema to detect ignored constraints.
                "messages": [{"role": "user", "content": 'Return {"ready": false}.'}],
            },
            operation="compatibility",
        )
        try:
            content = json.loads(data["message"]["content"])
            if (
                not isinstance(content, dict)
                or set(content) != {"ready"}
                or content["ready"] is not True
            ):
                raise ValueError
        except (KeyError, TypeError, ValueError):
            logger.error("provider=Ollama operation=compatibility reason=schema_not_enforced")
            raise AppError(
                "Ollama compatibility check failed: JSON schema constraints were not enforced. "
                "Use a GGUF model such as gemma4:e4b-it-q4_K_M, set CANIWATCH_MODEL, "
                "and run --doctor. No public research was performed."
            ) from None
        logger.info("provider=Ollama operation=compatibility stage=passed")

    def assess(self, movie: Movie, research: Research, concerns: list[str]) -> Assessment:
        prompt = files("caniwatch.prompts").joinpath("assessment.md").read_text(encoding="utf-8")
        schema = Assessment.model_json_schema()
        payload = {
            "model": self.model,
            "stream": False,
            "think": False,
            "format": schema,
            "options": {"temperature": 0.1, "num_predict": 4096, "num_ctx": 16384},
            "messages": [
                {"role": "system", "content": prompt + "\nJSON schema:\n" + json.dumps(schema)},
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
        }
        data = self._chat(payload)
        try:
            return Assessment.model_validate_json(data["message"]["content"])
        except (KeyError, TypeError, ValueError, ValidationError):
            logger.error("provider=Ollama operation=assessment reason=invalid_assessment")
            raise AppError(
                "Ollama returned an invalid assessment. Retry or choose another local model."
            ) from None

    def _chat(
        self, payload: dict, *, operation: Literal["assessment", "compatibility"] = "assessment"
    ) -> dict:
        return request_json(
            self.client,
            "POST",
            f"{self.url}/api/chat",
            provider="Ollama",
            operation=operation,
            json=payload,
        )
