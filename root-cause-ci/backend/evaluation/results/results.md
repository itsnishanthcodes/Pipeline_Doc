# Offline evaluation of the deterministic pipeline

13 controlled, synthetic failure scenarios (see `evaluation/scenarios.py`). The LLM is not involved. These results describe the deterministic stages on controlled fixtures, not accuracy on real-world repositories.

| Metric | Result |
|---|---|
| Classification accuracy | 12/13 (92%) |
| Commit attribution Top-1 (evidence-first) | 9/9 (100%) |
| Commit attribution Top-3 (evidence-first) | 9/9 (100%) |
| Commit attribution Top-1 (baseline: latest commit) | 3/9 (33%) |
| Flaky failures detected | 2/2 (100%) |
| Flaky false positives | 0/11 (0%) |
| Fix target file correct | 9/9 (100%) |

## Per-category classification

| Category | Precision | Recall | Support |
|---|---|---|---|
| CODE_REGRESSION | 88% | 100% | 7 |
| CONFIGURATION_FAILURE | 100% | 100% | 1 |
| DEPENDENCY_FAILURE | 100% | 100% | 2 |
| INFRASTRUCTURE_FAILURE | 100% | 50% | 2 |
| UNKNOWN | 100% | 100% | 1 |

## Per-scenario results

| Scenario | Category (expected / predicted) | Culprit rank | Flaky (expected / verdict) | Target |
|---|---|---|---|---|
| configuration: missing environment variable | CONFIGURATION_FAILURE / CONFIGURATION_FAILURE | 1 | no / LIKELY_STABLE | correct |
| infrastructure: docker daemon unavailable | INFRASTRUCTURE_FAILURE / INFRASTRUCTURE_FAILURE | n/a | no / LIKELY_STABLE | n/a |
| dependency: unresolvable version pin | DEPENDENCY_FAILURE / DEPENDENCY_FAILURE | 1 | no / LIKELY_STABLE | correct |
| dependency: new import of an uninstalled module | DEPENDENCY_FAILURE / DEPENDENCY_FAILURE | 1 | no / LIKELY_STABLE | correct |
| code regression: single commit | CODE_REGRESSION / CODE_REGRESSION | 1 | no / LIKELY_STABLE | correct |
| code regression: culprit is not the latest commit | CODE_REGRESSION / CODE_REGRESSION | 1 | no / LIKELY_STABLE | correct |
| code regression: exception raised in changed source line | CODE_REGRESSION / CODE_REGRESSION | 1 | no / LIKELY_STABLE | correct |
| code regression: older commit changed the failing function | CODE_REGRESSION / CODE_REGRESSION | 1 | no / LIKELY_STABLE | correct |
| code regression: two commits touch the same file | CODE_REGRESSION / CODE_REGRESSION | 1 | no / LIKELY_STABLE | correct |
| flaky: intermittent timeout, same commit passed on rerun | INFRASTRUCTURE_FAILURE / CODE_REGRESSION | n/a | yes / LIKELY_FLAKY | n/a |
| flaky: order-dependent test | CODE_REGRESSION / CODE_REGRESSION | n/a | yes / LIKELY_FLAKY | n/a |
| not flaky: first failure after a long green history | CODE_REGRESSION / CODE_REGRESSION | 1 | no / LIKELY_STABLE | correct |
| unknown: native crash | UNKNOWN / UNKNOWN | n/a | no / LIKELY_STABLE | n/a |
