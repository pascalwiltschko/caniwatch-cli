"""Composition root: a single Typer command with a natural movie argument."""

import json
import logging
import sys
from contextlib import nullcontext
from pathlib import Path
from typing import Annotated

import httpx
import typer
from pydantic import ValidationError
from rich.console import Console
from rich.text import Text

from caniwatch.application.demo import DEMO_CONCERNS, demo_report
from caniwatch.application.errors import AppError
from caniwatch.application.service import normalize_concerns, screen
from caniwatch.cli.render import public_report, render_report
from caniwatch.config import Settings
from caniwatch.domain.models import Movie, Report
from caniwatch.logging import configure_logging
from caniwatch.providers.ollama import Ollama
from caniwatch.providers.tavily import Tavily
from caniwatch.providers.tmdb import TMDB

app = typer.Typer(pretty_exceptions_enable=False, add_completion=False)
logger = logging.getLogger(__name__)


def choose_movie(movies: list[Movie], interactive: bool, console: Console) -> Movie:
    if not movies:
        raise AppError("No matching movie found. Try a different title or year.")
    if len(movies) == 1:
        return movies[0]
    for index, movie in enumerate(movies[:10], 1):
        console.print(Text(f"{index}. {movie.title} ({movie.year or 'unknown year'})"))
    if not interactive:
        raise typer.BadParameter("Ambiguous movie title. Specify --year or use a terminal.")
    while True:
        selected = typer.prompt("Select movie number", type=int, err=True)
        if 1 <= selected <= min(10, len(movies)):
            return movies[selected - 1]
        console.print("Choose a number from the list.")


def check_doctor(settings: Settings, console: Console) -> bool:
    healthy = True
    for name, credential in (("TMDB", settings.tmdb_token), ("Tavily", settings.tavily_api_key)):
        present = bool(credential.get_secret_value())
        healthy = healthy and present
        console.print(
            f"{name}: {'configured (not authenticated)' if present else 'missing credential'}"
        )
    try:
        with httpx.Client(timeout=5, trust_env=False, follow_redirects=False) as client:
            names = Ollama(client, settings).available_models()
        if settings.model not in names:
            console.print(
                "Ollama: reachable; configured model missing. Run ollama pull for your model."
            )
            healthy = False
        else:
            console.print("Ollama: reachable; configured model available.")
    except AppError:
        console.print("Ollama: unavailable. Start Ollama and pull the configured model.")
        healthy = False
    return healthy


def run_live(
    settings: Settings,
    title: str,
    year: int | None,
    concerns: list[str],
    interactive: bool,
    console: Console,
    show_progress: bool,
) -> Report:
    if not settings.tmdb_token.get_secret_value() or not settings.tavily_api_key.get_secret_value():
        raise AppError(
            "Set CANIWATCH_TMDB_TOKEN and CANIWATCH_TAVILY_API_KEY in .env or your environment. "
            "Use --demo to try the offline report."
        )
    with (
        httpx.Client(timeout=30, follow_redirects=False) as public_client,
        httpx.Client(timeout=180, follow_redirects=False, trust_env=False) as local_client,
    ):
        metadata = TMDB(public_client, settings.tmdb_token.get_secret_value())
        if show_progress:
            console.print("Looking up movie…")
        logger.info("stage=metadata_started")
        movie = choose_movie(metadata.search(title, year), interactive, console)
        movie = metadata.details(movie.id)
        logger.info("stage=metadata_finished")
        if show_progress:
            console.print("Researching general content guides, then assessing locally…")
        with console.status("Researching and assessing…") if show_progress else nullcontext():
            return screen(
                movie,
                concerns,
                Tavily(public_client, settings.tavily_api_key.get_secret_value()),
                Ollama(local_client, settings),
            )


@app.command()
def watch(
    title: Annotated[str | None, typer.Argument(help="Movie title to research.")] = None,
    year: Annotated[int | None, typer.Option(min=1888, max=2100, help="Release year.")] = None,
    avoid: Annotated[
        list[str] | None,
        typer.Option(
            "--avoid", help="Concern to check; repeatable. Shell history may retain this argument."
        ),
    ] = None,
    details: Annotated[
        bool, typer.Option(help="Reveal synopsis, scene details, and evidence.")
    ] = False,
    json_output: Annotated[
        bool, typer.Option("--json", help="Write a JSON report to stdout.")
    ] = False,
    demo: Annotated[
        bool, typer.Option(help="Fictional offline demo; no web or model calls.")
    ] = False,
    doctor: Annotated[
        bool, typer.Option("--doctor", help="Check credentials and local model.")
    ] = False,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Show safe diagnostics.")
    ] = False,
    log_file: Annotated[Path | None, typer.Option(help="Write rotating operational logs.")] = None,
) -> None:
    """Can I watch this? Public movie research, private local assessment."""
    console = Console(stderr=True, markup=False, highlight=False)
    try:
        configure_logging(verbose, log_file)
        if doctor:
            if title or demo or avoid or json_output:
                raise typer.BadParameter("Use --doctor on its own.")
            raise typer.Exit(0 if check_doctor(Settings(), console) else 1)
        if not title and not demo:
            raise typer.BadParameter("Provide a movie title, or use --demo or --doctor.")
        if demo and title:
            raise typer.BadParameter("The demo uses a fictional film; omit the movie title.")
        concerns = avoid or (DEMO_CONCERNS if demo else [])
        interactive = sys.stdin.isatty() and not json_output
        if not concerns:
            if not interactive:
                raise typer.BadParameter(
                    "Provide --avoid when input is noninteractive or using JSON."
                )
            private_input = typer.prompt(
                "Concerns (comma-separated; stay on this machine)",
                hide_input=True,
                err=True,
            )
            concerns = private_input.split(",")
        concerns = normalize_concerns(concerns)
        report = (
            demo_report(concerns)
            if demo
            else run_live(
                Settings(),
                title or "",
                year,
                concerns,
                interactive,
                console,
                show_progress=not json_output,
            )
        )
        if json_output:
            typer.echo(json.dumps(public_report(report, details), ensure_ascii=False))
        else:
            render_report(report, Console(markup=False, highlight=False), details)
    except ValidationError:
        console.print("Invalid configuration. Check .env and the loopback-only Ollama URL.")
        raise typer.Exit(1) from None
    except AppError as exc:
        logger.error("stage=failed reason=application_error")
        console.print(Text(str(exc), style="red"))
        raise typer.Exit(1) from None
    except OSError:
        console.print("Could not access a required local file. Check paths and permissions.")
        raise typer.Exit(1) from None


def main() -> None:
    try:
        app()
    except KeyboardInterrupt:
        raise SystemExit(130) from None
