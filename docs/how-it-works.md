# How caniwatch works

## Public research

Before public requests, a synthetic local generation probe checks schema enforcement.
The probe has no movie identity, sources, or private concerns. Unsupported constraints
stop the run before public research credits are spent. The default explicit GGUF model
tag avoids platform-dependent backend selection through the shorter model alias.

TMDB search resolves the title/year. Detailed movie metadata includes runtime, genres,
director credits, and an overview. This metadata is not treated as proof that a concern
is absent. Before ambiguous matches are listed, the app loads details for the first ten
candidates so the list can show director names. The selected details are reused for the
report.

`--director` loads details for candidates on the returned search page and filters by a
case-insensitive part of a credited director's name. Whitespace is normalized, and names
from any co-director can match. Missing director credits do not match a supplied name.
No additional search pages are fetched. The filter can be combined with `--year`; if
several matches remain, the user selects from up to ten films. JSON/noninteractive runs
require a single match. Selection and filtering happen before paid content research,
and these metadata requests are included in the TMDB usage count.

Tavily receives two fixed queries: title/year plus `parents guide content advisory` and
`content warnings detailed review`. Each basic search asks for at most four results,
raw text, no generated answer, no images, and explicit usage reporting. Automatic search
parameters are disabled. Results are deduplicated by URL, with at most four sources and
12,000 characters per source. Selection favors raw page text over excerpts, with stable
provider order as the tie breaker. Some pages will be unavailable or unrelated; a limited
research budget necessarily leaves coverage gaps. URLs are restricted to HTTP(S).

The app excludes DoesTheDogDie from discovery due to its access/use restrictions. It
does not bypass paywalls, challenges, login gates, or scrape websites directly. Provider
access does not grant republication rights; display only short supporting excerpts.
No persistent research cache is implemented. Review provider terms before adding one.

## Private assessment

Enter concerns as a comma-separated list at the prompt or through repeatable `--avoid`
arguments.
Only the local Ollama client receives them. The research function cannot receive them.
The local endpoint must be a literal loopback IP and must not redirect or use proxy
environment variables. Metadata/search services still see movie identity and your IP;
this is private preference matching, not anonymous or fully offline browsing.

The packaged system prompt treats source text as untrusted and requests a Pydantic-derived
JSON schema. Temperature is low; responses are bounded. Thinking is disabled to reserve
generation for the structured report. There is no retry using unconstrained output.
Findings must preserve every requested concern exactly once. The application verifies
source IDs and verbatim excerpts after whitespace normalization. Unsupported claims are downgraded to unknown. Conflicting
findings require evidence asserting both presence and absence. This establishes provenance,
not semantic truth: the model may still misunderstand a quote, source, film edition, or
subject. No confidence percentages or universal safety verdict are generated.

If all research fails, the app returns unknown findings without requesting a content assessment. A
partially failed research run retains usable evidence with an explicit limitation. Model
or metadata failures produce a safe actionable error rather than a fabricated report.

## Presentation and diagnostics

Rich places neutral film facts beside “Your Assessment”, a compact recommendation built
from validated findings. Reported presence leads to advice to skip, conflicting or unknown
findings to hold off, and explicitly reported absence of every concern to a reasonable
pick. The summary names the concerns driving the recommendation, using a count when
their combined names exceed 80 characters. Other unresolved findings are acknowledged
when content is reported present. JSON uses the same recommendation in `summary`.
Recommendations do not promise a universally safe viewing. The assessment border is
red if any concern is reported present or conflicting, yellow if evidence remains unknown,
and green when all concerns are reported absent. The film panel shows age classifications
from TMDB's release-date data, appended to the existing movie details request. Available
classifications for Germany, the US, and the UK appear on one line separated by dots;
the line wraps naturally in narrow panels. Duplicate certifications are removed, while
distinct certifications for different releases are preserved, separated by slashes.
Missing classifications are omitted. JSON includes country codes and classifications.
These classifications do not change concern findings or the summary color. Demo
classifications are fictional and labeled accordingly.

The table lists concerns, findings, compact comments, and source references, followed by
clickable/printed source URLs. With `--details`, a Details column includes each finding's
scene explanation and supporting excerpts. In narrow terminals, these appear with each
finding in the list.
Narrow terminals stack panels and use a list for findings. Limitations, an AI disclaimer,
and TMDB attribution appear in a subdued bullet list under “Disclaimers”; research usage
is hidden by default. `--api-usage` adds a separate “API Usage” list last, showing TMDB
requests counted locally and Tavily credits reported by the search responses. Missing
usage data is omitted. JSON includes these values only with this option. The terminal
demo always includes the list with a fictional demo label and sample usage; no API calls
occur.

The model writes comments and explanations in a calm, conversational voice, addressing
the reader directly without claiming personal viewing experience. It supplies a separate
comment of at most 160 characters about evidence coverage,
instructed to omit scene descriptions and plot details. Validation replaces comments for
unsupported findings with an uncertainty notice. Default output omits synopsis, scene
explanations, and excerpts. `--details` explicitly reveals them. Finding labels, comments,
and source titles can still reveal content; minimal output reduces but cannot guarantee
no spoilers. JSON includes comments and follows the same disclosure policy, without raw
source text.

Application stages emit counts, elapsed times, and a run ID. Optional local log files
rotate. Exceptions from providers are translated to controlled messages; arbitrary
payloads and exception bodies are never printed. Reports are not automatically saved.
The fictional offline demo uses the same orchestration and renderer with fixture providers;
it proves installability and report behavior, not the performance of Gemma or web search.

## Open innovation and costs

The open-weight model runs locally and is replaceable; prompt and source validation
behavior are inspectable. Personal concerns need not go to a hosted inference provider.
Research remains online and uses external APIs. Free allowances can support a prototype
but are not a promise of indefinite free service. Tavily's basic search currently consumes
one credit; the normal budget is two search calls per film, with no automatic retries or
deeper extraction calls. `--api-usage` shows the sum of provider-reported credits for the
current run. Missing or invalid credit data is omitted rather than estimated. The option
uses the existing search responses and makes no additional requests.

TMDB requires attribution and a commercial license for commercial use; this prototype is
non-commercial. Tavily has its own service terms. The project code's MIT license does not
relicense third-party metadata/content or the model. Sources:

- [TMDB API and attribution](https://developer.themoviedb.org/docs/faq)
- [Tavily search](https://docs.tavily.com/documentation/api-reference/endpoint/search)
- [Tavily pricing](https://www.tavily.com/pricing)
- [Gemma 4 E4B](https://ollama.com/library/gemma4:e4b-it-q4_K_M)
