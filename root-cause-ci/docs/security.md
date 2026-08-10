# Security

Phase 1 only establishes the project skeleton, but the later design must preserve these constraints:

- Never execute generated patches on the host.
- Run verification inside Docker isolation.
- Redact secrets from logs before any LLM access.
- Validate webhook signatures.
- Restrict patch scope.
- Require developer approval before merge.

No credentials are committed in this repository. Use `.env` locally and keep production secrets outside version control.
