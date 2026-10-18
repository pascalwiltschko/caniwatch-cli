# Features and acceptance criteria

`caniwatch TITLE [--year YEAR]` resolves a film, performs fixed public research, prompts
for private concerns when needed, and renders a report. Repeat `--avoid` for scripted use;
these arguments can be stored by your shell. Separate concerns with commas at the prompt.

- Resolve ambiguous titles through an interactive selection; JSON/noninteractive runs
  require an unambiguous title/year and never silently choose between matches.
- Research uses two fixed queries, independent of concerns, with at most four deduplicated
  sources. Page text comes from the search API; no autonomous browsing or direct scraping.
- Findings: reported present, reported absent, conflicting, unknown. Missing evidence
  cannot mean absent. Known source IDs and matching excerpts are required for claims.
- `--details` reveals scene explanations and evidence. Default output hides those details
  and omits the plot synopsis to reduce spoilers; metadata, finding labels, and compact
  evidence comments remain. Comments describe evidence coverage without scene details.
- The film panel uses neutral styling. The assessment panel is red for reported present
  or conflicting content, yellow for unknown findings, and green only when all concerns
  are reported absent. These colors summarize evidence, not universal viewing safety.
  A subdued bullet list under “Disclaimers” groups limitations, the AI disclaimer, and TMDB
  attribution.
- API usage is hidden by default in live terminal reports and JSON. `--api-usage`
  adds a dim “API Usage” list at the bottom with locally counted TMDB requests and
  provider-reported Tavily credits used for this run. Missing usage data is omitted.
  The option makes no additional requests.
  The terminal demo always displays clearly labeled fictional usage without API calls;
  demo JSON includes these with `--api-usage`.
- `--json` writes one report object to stdout; progress/errors go to stderr. JSON includes
  details only when explicitly requested. `--verbose` increases safe diagnostics.
- `--json --output PATH` saves the report using atomic replacement after successful
  completion. Errors leave an existing report untouched or a new destination absent.
  `--output` requires `--json` and a path different from `--log-file`. Ordinary shell
  redirection can still create/truncate files before the application runs.
- `--demo` uses fictional evidence and a fixture assessor; makes no network/model calls
  and is labeled throughout. It demonstrates presentation, not inference accuracy.
- `--doctor` checks configuration, local model connectivity, and model availability.
  It also performs a small synthetic schema-enforcement check against the local model.
  Live runs perform this check before public research. Unsupported or ignored constraints
  fail explicitly, without unconstrained retries. No credentials or concerns are used in
  the probe. Doctor does not send API credentials to providers or perform paid searches.

No accounts, preference persistence, remote inference, hosted tracing, browser automation,
TV episodes, targeted searches, or persistent research cache in this prototype.

Acceptance: offline CLI demo, mocked end-to-end provider workflow, privacy request
invariance, citation rejection, ambiguity handling, provider failures, JSON output,
narrow terminals, and all lint/type/test gates pass. Real-provider smoke testing is
separate and requires local credentials and Ollama.
