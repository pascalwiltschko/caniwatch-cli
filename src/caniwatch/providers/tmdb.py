"""TMDB movie search and metadata; never receives private concerns."""

from typing import Any

import httpx
from pydantic import ValidationError

from caniwatch.application.errors import AppError
from caniwatch.domain.models import Movie
from caniwatch.providers.http import request_json

BASE_URL = "https://api.themoviedb.org/3"


def _movie(data: dict[str, Any]) -> Movie:
    date = str(data.get("release_date") or "")
    return Movie(
        id=data["id"],
        title=data["title"],
        year=int(date[:4]) if date[:4].isdigit() else None,
        overview=data.get("overview") or "",
    )


class TMDB:
    def __init__(self, client: httpx.Client, token: str):
        self.client = client
        self.headers = {"Authorization": f"Bearer {token}"}

    def search(self, title: str, year: int | None) -> list[Movie]:
        params: dict[str, str | int] = {"query": title, "include_adult": "true"}
        if year is not None:
            params["primary_release_year"] = year
        data = request_json(
            self.client,
            "GET",
            f"{BASE_URL}/search/movie",
            provider="TMDB",
            operation="search",
            headers=self.headers,
            params=params,
        )
        try:
            movies = [_movie(item) for item in data["results"]]
        except (KeyError, TypeError, ValueError, AttributeError, ValidationError):
            raise AppError("TMDB returned invalid movie data.") from None
        return [movie for movie in movies if year is None or movie.year == year]

    def details(self, movie_id: int) -> Movie:
        data = request_json(
            self.client,
            "GET",
            f"{BASE_URL}/movie/{movie_id}",
            provider="TMDB",
            operation="details",
            headers=self.headers,
            params={"append_to_response": "credits"},
        )
        try:
            movie = _movie(data)
            movie.runtime = data.get("runtime") or None
            movie.genres = [item["name"] for item in data.get("genres", [])]
            directors = [
                item["name"]
                for item in data.get("credits", {}).get("crew", [])
                if item.get("job") == "Director"
            ]
            movie.director = ", ".join(directors) or None
            return Movie.model_validate(movie.model_dump())
        except (KeyError, TypeError, ValueError, AttributeError, ValidationError):
            raise AppError("TMDB returned invalid movie details.") from None
