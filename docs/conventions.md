# Conventions

Use Python 3.13+, typed function boundaries, Pydantic for untrusted input, and explicit
exceptions with safe user-facing messages. Prefer small cohesive modules and composition.
Domain models must not import CLI or network libraries. Provider interfaces should describe
capabilities; their implementations must not leak response details into orchestration.

Use Ruff for formatting/imports/linting, ty for type checking, and pytest for meaningful
behavioral tests. Mock network transports instead of making paid requests in tests.
Never treat a green mock test as evidence of real-world model accuracy.

Log named stages, counts, durations, and safe error codes. Never interpolate arbitrary
exception messages from network, configuration, or model parsing into logs or CLI errors.
Use module loggers; configure handlers only at the CLI boundary.

Commits should describe one coherent change, with `feat:`, `fix:`, `test:`, `docs:`, or
`chore:` prefixes. The initial scaffold may be larger. Keep later changes focused and
update documentation in the same commit as behavior. Avoid speculative plugin systems,
generic repositories, and framework plumbing. Do not spawn agents unless the user asks.
