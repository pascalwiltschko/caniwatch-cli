# caniwatch

Public movie research. Private content assessments.

A Python CLI that researches a movie using general content-advisory queries, then compares
the evidence against your concerns using a local open-weight model. Personal concerns are
never sent to the metadata or search provider.

```sh
caniwatch terrifier --year 2018
```

Enter your concerns when prompted, separated by commas. The tool retrieves general film
content guides and reports **reported present**, **reported absent**, **conflicting**, or **unknown**
for each concern, with source references. It never interprets missing evidence as absence.

## Try the prototype

Install [uv](https://docs.astral.sh/uv/) and [Task](https://taskfile.dev/), then:

```sh
task setup
task demo
```

The offline demo needs no API keys, internet, or running model after dependency installation.
It uses a **fictional film and fixture assessment**, clearly labeled; it demonstrates the
workflow and terminal report rather than AI accuracy.

```sh
uv run caniwatch --demo --details
uv run caniwatch --demo --json
uv run caniwatch --help
```

## Live movie checks

1. Install and start [Ollama](https://ollama.com/), then download the model:

   ```sh
   ollama pull gemma4:e4b-it-q4_K_M
   ```

   Use this explicit GGUF tag rather than `gemma4:e4b`, which can select an MLX backend
   on Apple Silicon. The workflow requires schema-constrained JSON generation. Some
   Ollama MLX installations reject or ignore that capability. If you already have a
   `.env`, set `CANIWATCH_MODEL=gemma4:e4b-it-q4_K_M` there too; environment variables
   override `.env` and the application default.

2. Obtain a [TMDB API Read Access Token](https://developer.themoviedb.org/docs/getting-started)
   and a [Tavily API key](https://www.tavily.com/). Copy `.env.example` to `.env` and fill in
   `CANIWATCH_TMDB_TOKEN` and `CANIWATCH_TAVILY_API_KEY`. Keep credentials on your machine.

3. Check the setup and run a film assessment:

   ```sh
   uv run caniwatch --doctor
   uv run caniwatch terrifier --year 2018
   ```

For scripting, use repeatable `--avoid` arguments (your shell may record them). Quote
multiword titles and concerns:

```sh
uv run caniwatch 'The Descent' --year 2005 --avoid claustrophobia --avoid 'animal harm'
uv run caniwatch terrifier --year 2018 --avoid gore --json
uv run caniwatch terrifier --year 2018 --avoid gore --json --output report.json
uv run caniwatch terrifier --year 2018 --avoid gore --details
```

Default reports omit the synopsis and scene evidence. `--details` reveals them; finding
labels and source titles can themselves reveal content. JSON goes to stdout, diagnostics
to stderr. Ambiguous titles prompt for selection; noninteractive runs require a narrower
title/year match. Reports do not make a universal “safe to watch” determination.

Use `--json --output PATH` to save a complete report atomically: failures leave an existing
report unchanged and do not create an empty destination. Shell redirection (`> PATH`)
creates or truncates the file before the CLI starts, so it cannot offer that guarantee.
The output path must differ from `--log-file`.

Before any public research, a small local generation check tests whether the configured
model/backend enforces JSON schema constraints. `--doctor` runs the same check without
contacting the public providers. Unsupported generation fails explicitly; the app never
falls back to unconstrained text. This checks protocol compatibility, not assessment accuracy.

## Privacy by architecture

- **Public research:** TMDB and Tavily receive movie identity and fixed general-advisory
  queries. They still see your movie interest and network identity.
- **Private assessment:** only the loopback Ollama endpoint receives your concerns. Remote
  inference URLs, redirects, and proxy inheritance for local inference are disabled.
- **No adaptive disclosure:** concerns never affect research queries, page selection, or
  stopping decisions. Changing concerns produces identical research request payloads.
- **No remote telemetry or preference storage:** operational logs omit concerns, secrets,
  prompts, source text, and model responses. Reports are not saved automatically.

The open-weight model and inspectable prompts make this separation possible without
requiring a hosted inference service. Research still needs internet access. Model downloads
require storage and sufficient memory. Free search allowances can support a prototype;
they are not a guarantee of free service forever.

## Development and code

Python 3.13+, Typer, Rich, HTTPX, Pydantic, and Ollama. `uv.lock` pins dependencies.

```sh
task format       # Ruff fixes and formatting
task check        # Ruff, ty, pytest; entirely offline
uv run pytest --cov=caniwatch --cov-report=term-missing
uv run caniwatch --demo --verbose --log-file caniwatch.log
```

`task setup` installs pre-commit lint/format/type hooks and a pre-push test hook.
GitHub Actions runs the same checks. Tests prohibit real network connections and use
mocked HTTP responses, including a complete CLI-to-provider workflow and privacy checks.
Real API/model quality requires a separate live smoke test once credentials are configured.

The package separates CLI presentation, application orchestration, domain models, and
provider adapters. Start with:

- [Architecture and extension points](docs/architecture.md)
- [Detailed walkthrough and limitations](docs/how-it-works.md)
- [Features and acceptance criteria](docs/features.md)
- [Development and troubleshooting](docs/development.md)
- [Code and commit conventions](docs/conventions.md)
- [Contributor/agent entry point](AGENTS.md)

## Data and limitations

Research is bounded to two basic search requests and four deduplicated sources. Blocked,
missing, excerpt-only, or contradictory pages reduce coverage. Citation validation checks
that supporting excerpts occur in retrieved text; it cannot prove that a model interpreted
them correctly. Film editions may differ. Rare triggers often remain unknown.

No persistent research cache, autonomous agent, direct website scraping, or targeted
concern searches are included in this first prototype.

Movie metadata is supplied by [TMDB](https://www.themoviedb.org/). This product uses the
TMDB API but is not endorsed or certified by TMDB. The prototype uses its non-commercial
developer offering; commercial use requires reviewing TMDB licensing. Source material and
models retain their respective terms. Project code is licensed under [MIT](LICENSE).
