# Working on caniwatch

Read the relevant documents before changing behavior:

- [Features](docs/features.md): CLI behavior and acceptance criteria.
- [Architecture](docs/architecture.md): boundaries and extension points.
- [Conventions](docs/conventions.md): code, tests, logs, and commits.
- [Development](docs/development.md): setup and verification.
- [How it works](docs/how-it-works.md): detailed data flow and limitations.

The privacy invariant is mandatory: external research cannot receive concerns or private
assessment output. Research requests must be identical for the same movie regardless of
concerns. Inference is loopback-only. Never log credentials, concerns, prompts, page text,
or model responses. Do not enable remote telemetry.

Make small, focused commits as the project progresses. Keep docs current with behavior.
Run `task check` before committing completed behavior. Tests must work without credentials,
internet, or a running model. Do not add frameworks or abstractions without a concrete use.
