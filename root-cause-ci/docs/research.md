# Research Notes

The research goal is to compare evidence-driven CI/CD failure diagnosis against a log-only LLM baseline.

## Phase 1 scope

Phase 1 does not perform diagnosis or attribution. It only creates the runnable scaffold needed to host later experiments.

## Research direction

The eventual system will evaluate whether combining:
- CI logs
- Git history
- stack traces
- AST structure
- dependency graphs
- historical failure patterns
- confidence scoring
- constrained patch generation
- sandbox verification

improves trustworthiness relative to a raw CI log prompt.

## Data and evaluation

The demo repository and evaluation harness will be added in later phases. No metrics are reported yet because no experiments have been run.
