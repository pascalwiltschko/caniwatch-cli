# Development

Requirements: Python 3.13+, [uv](https://docs.astral.sh/uv/),
[Task](https://taskfile.dev/), and Git. Run `git init` for a fresh checkout, then `task setup`.
The lockfile pins tooling and runtime dependencies. `task check` runs Ruff, ty, and pytest.
`task format` fixes lint/formatting; `task demo` exercises the offline fictional report.
Pre-commit runs lint/format/type checks; pre-push runs the offline test suite. CI runs all.

For live use, install [Ollama](https://ollama.com/), run `ollama pull gemma4:e4b`, and start
the local server. Create TMDB and Tavily developer credentials, copy `.env.example` to
`.env`, and fill its two credential values locally. Never paste secrets into issues/logs.
Run `uv run caniwatch --doctor`, then `uv run caniwatch 'Terrifier' --year 2016`.

Configuration uses `CANIWATCH_` environment variables; environment overrides `.env`.
`CANIWATCH_MODEL` defaults to `gemma4:e4b`. `CANIWATCH_OLLAMA_URL` defaults to
`http://127.0.0.1:11434`; only literal loopback addresses are accepted. Connections to
`localhost` should use `127.0.0.1` instead to avoid hostname resolution/proxy ambiguity.

`--log-file PATH` enables rotating local logs, `--verbose` shows stage diagnostics on
stderr. Logs contain operational counts/timings, never personal concerns or raw payloads.
No remote observability service is required. Do not enable HTTP wire logging around
private inference. Stop the process with Ctrl-C; cancellation exits with code 130.

Exit codes: 0 report/healthy doctor; 1 operational/configuration failure; 2 CLI usage,
missing concerns, or unresolved ambiguity. Unknown content findings still produce exit 0.

Run `uv run pytest --cov=caniwatch --cov-report=term-missing` for coverage. Tests use
HTTPX MockTransport and synthetic source text. No test requires internet or credentials.
Before publishing, manually inspect real reports on several films with known content;
test evidence about rare concerns, ambiguous titles, blocked pages, and conflicting claims.
