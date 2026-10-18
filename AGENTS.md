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

Ask for explicit approval before creating a commit so the user can test the changes first.
A direct request to commit authorizes that commit only, not future commits. Keep commits
small and focused, and keep docs current with behavior.
Run `task check` before committing completed behavior. Tests must work without credentials,
internet, or a running model. Do not add frameworks or abstractions without a concrete use.

Write README text, docstrings, and other human-facing documentation around lasting
behavior, usage, and relevant limitations. Use plain language that stands on its own;
do not mirror the wording of a user request or emphasize incidental details of a change.
