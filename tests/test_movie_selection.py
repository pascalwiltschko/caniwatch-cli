import io

import pytest
import typer
from rich.console import Console

from caniwatch.application.errors import AppError
from caniwatch.cli.main import choose_movie, resolve_movie
from caniwatch.domain.models import Movie


class FakeMetadata:
    def __init__(self, movies: list[Movie]):
        self.movies = movies
        self.detail_ids: list[int] = []
        self.search_inputs: list[tuple[str, int | None]] = []

    def search(self, title: str, year: int | None) -> list[Movie]:
        self.search_inputs.append((title, year))
        return [movie.model_copy(update={"director": None}) for movie in self.movies]

    def details(self, movie_id: int) -> Movie:
        self.detail_ids.append(movie_id)
        return next(movie for movie in self.movies if movie.id == movie_id)


@pytest.mark.parametrize("director", ["SMITH", " Jane   Smith ", "jane"])
def test_director_filter_uses_credits_and_accepts_case_insensitive_partial_names(director):
    metadata = FakeMetadata(
        [
            Movie(id=1, title="Film", year=2000, director="Alex Jones"),
            Movie(id=2, title="Film", year=2000, director="Jane Smith, Taylor Example"),
            Movie(id=3, title="Film", year=2000),
        ]
    )
    movie = resolve_movie(metadata, "Film", 2000, director, False, Console(file=io.StringIO()))
    assert movie is metadata.movies[1]
    assert metadata.search_inputs == [("Film", 2000)]
    assert metadata.detail_ids == [1, 2, 3]


@pytest.mark.parametrize("director", [None, "Jane", "unknown"])
def test_director_filter_does_not_choose_unmatched_or_missing_credits(director):
    metadata = FakeMetadata([Movie(id=1, title="Film", director="Alex Jones")])
    if director is None:
        metadata.movies = []
    with pytest.raises(AppError, match="No matching movie"):
        resolve_movie(metadata, "Film", None, director, False, Console(file=io.StringIO()))


def test_director_filter_keeps_multiple_matches_ambiguous():
    metadata = FakeMetadata(
        [
            Movie(id=1, title="Film", director="Alex Smith"),
            Movie(id=2, title="Film", director="Jane Smith"),
        ]
    )
    stream = io.StringIO()
    with pytest.raises(typer.BadParameter, match="--director"):
        resolve_movie(metadata, "Film", None, "Smith", False, Console(file=stream, width=160))
    assert "Director: Alex Smith" in stream.getvalue()
    assert "Director: Jane Smith" in stream.getvalue()


def test_interactive_selection_shows_directors_and_reuses_the_selected_details(monkeypatch):
    metadata = FakeMetadata(
        [
            Movie(id=index, title="Film", year=2000, director=f"Director {index}")
            for index in range(1, 13)
        ]
    )
    stream = io.StringIO()
    monkeypatch.setattr(typer, "prompt", lambda *args, **kwargs: 3)
    selected = resolve_movie(metadata, "Film", 2000, None, True, Console(file=stream, width=160))
    assert selected is metadata.movies[2]
    assert metadata.detail_ids == list(range(1, 11))
    assert "3. Film (2000) · Director: Director 3" in stream.getvalue()
    assert "Director 11" not in stream.getvalue()


def test_director_filter_checks_candidates_beyond_the_first_ten():
    metadata = FakeMetadata(
        [Movie(id=index, title="Film", director=f"Director {index}") for index in range(1, 13)]
    )
    movie = resolve_movie(metadata, "Film", None, "Director 12", False, Console(file=io.StringIO()))
    assert movie.id == 12
    assert metadata.detail_ids == list(range(1, 13))


def test_selection_labels_missing_director_and_year_without_guessing(monkeypatch):
    stream = io.StringIO()
    movies = [Movie(id=1, title="Film"), Movie(id=2, title="Film", director="Jane Smith")]
    monkeypatch.setattr(typer, "prompt", lambda *args, **kwargs: 1)
    assert choose_movie(movies, True, Console(file=stream, width=160)) is movies[0]
    assert "1. Film (unknown year) · Director: unknown" in stream.getvalue()
