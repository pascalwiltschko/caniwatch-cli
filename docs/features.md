# Features and acceptance criteria

`caniwatch TITLE [--year YEAR]` resolves a film, performs fixed public research, prompts
for private concerns when needed, and renders a report. Repeat `--avoid` for scripted use;
these arguments can be stored by your shell. Interactive concern input is hidden.

- Resolve ambiguous titles through an interactive selection; JSON/noninteractive runs
  require an unambiguous title/year and never silently choose between matches.
- Research uses two fixed queries, independent of concerns, with at most four deduplicated
  sources. Page text comes from the search API; no autonomous browsing or direct scraping.
- Findings: reported present, reported absent, conflicting, unknown. Missing evidence
  cannot mean absent. Known source IDs and matching excerpts are required for claims.
- `--details` reveals scene explanations and evidence. Default output hides those details
  and omits the plot synopsis to reduce spoilers; metadata and finding labels remain.
- `--json` writes one report object to stdout; progress/errors go to stderr. JSON includes
  details only when explicitly requested. `--verbose` increases safe diagnostics.
- `--demo` uses fictional evidence and a fixture assessor; makes no network/model calls
  and is labeled throughout. It demonstrates presentation, not inference accuracy.
- `--doctor` checks configuration, local model connectivity, and model availability.
  It does not send API credentials to providers or perform paid searches.

No accounts, preference persistence, remote inference, hosted tracing, browser automation,
TV episodes, targeted searches, or persistent research cache in this prototype.

Acceptance: offline CLI demo, mocked end-to-end provider workflow, privacy request
invariance, citation rejection, ambiguity handling, provider failures, JSON output,
narrow terminals, and all lint/type/test gates pass. Real-provider smoke testing is
separate and requires local credentials and Ollama.
