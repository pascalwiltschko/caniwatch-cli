# caniwatch

Public movie research. Private content assessments.

A Python CLI that checks movie content against your concerns using public content guides
and a local model. Findings include source references and distinguish **reported present**,
**reported absent**, **conflicting**, and **unknown**. Missing evidence never means absence.

Your concerns stay with the local Ollama model; TMDB and Tavily receive only movie details
and fixed research queries. They can still see which movie you look up. Assessments can
be incomplete or wrong and do not guarantee a film is suitable for you.

## Get started

Install Python 3.13+, [uv](https://docs.astral.sh/uv/), and [Task](https://taskfile.dev/).
From the checkout, install dependencies and Git hooks, then try the offline demo:

```sh
task setup
task demo
```

The demo uses a fictional film and fixture assessment. After setup, it needs no API keys,
internet, or running model.

For real movie checks:

1. Install and start [Ollama](https://ollama.com/), then download a model that supports
   schema-constrained JSON output. The default is `gemma4:e4b-it-q4_K_M`:

   ```sh
   ollama pull gemma4:e4b-it-q4_K_M
   ```

   If your hardware supports a larger, more capable model, pull it and set
   `CANIWATCH_MODEL` to its tag in `.env` or your environment. Use `--doctor` to check
   compatibility.

2. Copy `.env.example` to `.env` and set `CANIWATCH_TMDB_TOKEN` to your
   [TMDB API Read Access Token](https://developer.themoviedb.org/docs/getting-started)
   and `CANIWATCH_TAVILY_API_KEY` to your [Tavily API key](https://www.tavily.com/).
3. Verify your configuration:

   ```sh
   uv run caniwatch --doctor
   ```

See [development and troubleshooting](docs/development.md) for model compatibility and
configuration details.

## Usage

```sh
# Enter comma-separated concerns at the prompt
uv run caniwatch 'Reanimator'

# Supply concerns directly and narrow the movie by director
uv run caniwatch 'The Thing' --director 'John Carpenter' --avoid gore --avoid 'animal harm'

# Include scene details and supporting evidence
uv run caniwatch 'The Descent' --year 2005 --avoid claustrophobia --details

# Save a JSON report; an existing file is preserved if the run fails
uv run caniwatch 'The Descent' --year 2005 --avoid claustrophobia --json --output report.json
```

Prefer the prompt if you do not want concerns recorded in shell history. Default reports
omit the synopsis and scene evidence, but findings and source titles may still reveal
content. For JSON or noninteractive use, provide `--avoid` and enough filters to identify
one movie.

## CLI arguments

`caniwatch [TITLE] [OPTIONS]`

| Argument / option | Description |
| --- | --- |
| `TITLE` | Movie title; quote titles containing spaces. Omit for `--demo` or `--doctor`. |
| `--year YEAR` | Filter by release year. |
| `--director NAME` | Filter by a case-insensitive part of a director's name. |
| `--avoid CONCERN` | Concern to check; repeat for multiple concerns. Prompts when omitted. |
| `--details` | Reveal the synopsis, scene explanations, and supporting excerpts. |
| `--json` | Write JSON to stdout, or to the file selected with `--output`. |
| `--output PATH` | Atomically save a report; requires `--json` and an existing parent directory. |
| `--api-usage` | Include TMDB request counts and Tavily's reported credits used. |
| `--demo` | Run the fictional offline demo without web or model calls. |
| `--doctor` | Check credentials are configured and test local model compatibility; use on its own. |
| `--verbose`, `-v` | Show operational diagnostics on stderr. |
| `--log-file PATH` | Write rotating local operational logs; must differ from `--output`. |
| `--help` | Show command help. |

## Development

`task setup` installs locked dependencies, pre-commit checks, and a pre-push test hook.

```sh
task format       # Fix lint issues and format code
task check        # Run Ruff, ty, and pytest
```

Checks run offline without credentials or a model. Live API and model quality need
separate testing with a configured local setup.

Further reading: [code and integration tutorial](docs/tutorial.md),
[development](docs/development.md), [architecture](docs/architecture.md),
[features](docs/features.md), [how it works](docs/how-it-works.md), and
[conventions](docs/conventions.md).

## License

Project code is licensed under [MIT](LICENSE). Third-party content, services, and models
retain their own terms.

Movie metadata is supplied by [TMDB](https://www.themoviedb.org/). This product uses the
TMDB API but is not endorsed or certified by TMDB. Commercial use requires reviewing
TMDB licensing.
