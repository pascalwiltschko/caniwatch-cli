# Architecture

Dependency direction: CLI → application → domain. Providers implement application
protocols and use domain types. The composition root in the CLI constructs providers.

`domain.models` defines Movie, Source, Research, Evidence, Finding, Assessment, and Report.
`application.ports` declares metadata, research, and assessor capabilities.
`application.service` resolves research and validates model findings before reporting.
`providers.tmdb`, `providers.tavily`, and `providers.ollama` own their wire formats.
`cli.render` owns Rich presentation and the public JSON view.

The research protocol accepts only Movie. Concerns exist only in local assessment inputs.
Fixed query templates, limits, and selection order are independent of concerns. Source
text is untrusted data, never instructions or tool requests. The model has no tools.

Use separate HTTP clients: external research uses fixed HTTPS endpoints, local inference
uses a validated literal loopback address, no redirects, and no environment proxies.
Remote model endpoints are rejected. No HTTP debug/body logging is enabled.

Extension points: replace a provider implementing the same protocol, change the model via
configuration, or adjust the packaged prompt. Do not expose concerns to a future research
agent. Caching, if added, needs provider-term review and must key only on public inputs.
