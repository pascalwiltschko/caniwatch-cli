"""Validated values shared across provider and application boundaries."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Movie(Model):
    id: int
    title: str
    year: int | None = None
    runtime: int | None = None
    genres: list[str] = Field(default_factory=list)
    director: str | None = None
    overview: str = ""


class Source(Model):
    id: int
    title: str
    url: HttpUrl
    text: str
    full_text: bool = False


class Research(Model):
    sources: list[Source] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    searches: int = 0
    credits: float | None = None


class Status(StrEnum):
    PRESENT = "reported_present"
    ABSENT = "reported_absent"
    CONFLICTING = "conflicting"
    UNKNOWN = "unknown"


class Evidence(Model):
    source_id: int
    quote: str = Field(min_length=1, max_length=400)
    supports: Status


class Finding(Model):
    concern: str
    status: Status
    comment: str = Field(
        default="",
        max_length=160,
        description="One short sentence about the evidence, without scene or plot details.",
    )
    explanation: str = ""
    evidence: list[Evidence] = Field(default_factory=list)


class Assessment(Model):
    findings: list[Finding]


class Report(Model):
    movie: Movie
    research: Research
    assessment: Assessment
    demo: bool = False
    tmdb_requests: int | None = None
