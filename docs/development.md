# Development

Requirements: Python 3.13+, [uv](https://docs.astral.sh/uv/),
[Task](https://taskfile.dev/), and Git. Run `git init` for a fresh checkout, then `task setup`.
The lockfile pins tooling and runtime dependencies. `task check` runs Ruff, ty, and pytest.
`task format` fixes lint/formatting; `task demo` exercises the offline fictional report.
Pre-commit runs lint/format/type checks; pre-push runs the offline test suite. CI runs all.

After moving the checkout or renaming a parent folder, rebuild the virtual environment:
run `uv venv --clear`, then `task setup`. Python launchers and Git hooks contain absolute
paths, so the old environment can fail with `Failed to spawn` or `bad interpreter`.
If you had activated it in your shell, run `deactivate` before rebuilding and then
`source .venv/bin/activate` again afterward.

For live use, install [Ollama](https://ollama.com/), run `ollama pull gemma4:e4b-it-q4_K_M`, and start
the local server. Create TMDB and Tavily developer credentials, copy `.env.example` to
`.env`, and fill its two credential values locally. Never paste secrets into issues/logs.
Run `uv run caniwatch --doctor`, then `uv run caniwatch 'Terrifier' --year 2018`.

Configuration uses `CANIWATCH_` environment variables; environment overrides `.env`.
`CANIWATCH_MODEL` defaults to `gemma4:e4b-it-q4_K_M`. `CANIWATCH_OLLAMA_URL` defaults to
`http://127.0.0.1:11434`; only literal loopback addresses are accepted. Connections to
`localhost` should use `127.0.0.1` instead to avoid hostname resolution/proxy ambiguity.

The explicit default tag uses GGUF. On Apple Silicon the shorter `gemma4:e4b` alias may
use MLX, whose structured-output support varies by installation. Existing `.env` files
must update `CANIWATCH_MODEL` too. The app requires schema-constrained generation and
does not retry without a schema. `--doctor` and live runs send a tiny synthetic local
probe that conflicts with its schema to detect ignored constraints. Live runs do this
before metadata or paid research. A successful probe establishes basic compatibility,
not model accuracy or support for every possible schema. It can take time to load a model.

For HTTP 501 during the compatibility check, pull `gemma4:e4b-it-q4_K_M`, select it with
`CANIWATCH_MODEL`, and rerun doctor. HTTP failures identify the provider, operation and
status in CLI errors and operational logs; response bodies are never printed or logged.
Timeouts and connection failures have distinct safe diagnostic reasons.

`--log-file PATH` enables rotating local logs, `--verbose` shows stage diagnostics on
stderr. Logs contain operational counts/timings, never personal concerns or raw payloads.
No remote observability service is required. Do not enable HTTP wire logging around
private inference. Stop the process with Ctrl-C; cancellation exits with code 130.

Save JSON with `--json --output report.json` rather than shell redirection to preserve
an existing report on error. The CLI writes a temporary file in the destination directory,
closes it, then atomically replaces the destination. Write/replace failures clean up the
temporary file and exit 1. The parent directory must exist. Shell `>` runs before the CLI
and can still create an empty file or truncate an earlier report.

Exit codes: 0 report/healthy doctor; 1 operational/configuration failure; 2 CLI usage,
missing concerns, or unresolved ambiguity. Unknown content findings still produce exit 0.
For ambiguous titles, add `--year` or `--director NAME`; director matching is
case-insensitive and accepts part of a name. A filter with no match exits 1 before
content research. The interactive selection list includes credited directors.

Run `uv run pytest --cov=caniwatch --cov-report=term-missing` for coverage. Tests use
HTTPX MockTransport and synthetic source text. No test requires internet or credentials.
Before publishing, manually inspect real reports on several films with known content;
test evidence about rare concerns, ambiguous titles, blocked pages, and conflicting claims.
