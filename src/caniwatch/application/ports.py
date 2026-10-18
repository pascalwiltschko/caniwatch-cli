"""Small interfaces for substituting providers in tests or future integrations."""

from typing import Protocol

from caniwatch.domain.models import Assessment, Movie, Research


class MetadataProvider(Protocol):
    def search(self, title: str, year: int | None) -> list[Movie]: ...

    def details(self, movie_id: int) -> Movie: ...


class ResearchProvider(Protocol):
    # Deliberately no concern, profile, or assessment parameter.
    def research(self, movie: Movie) -> Research: ...


class Assessor(Protocol):
    def assess(self, movie: Movie, research: Research, concerns: list[str]) -> Assessment: ...
