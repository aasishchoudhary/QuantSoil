# Evaluation Policy

Production maturity is determined by executable evidence, not labels.

Evaluate correctness, reproducibility, provenance completeness, temporal correctness, spatial correctness, security, reliability, performance, observability, and recovery.

Evidence hierarchy:
1. Reproducible production execution
2. Automated integration/replay evaluation
3. Automated unit/contract tests
4. Independently inspectable implementation
5. Documentation and claims

Ingestion/fusion evaluation must cover duplicates, idempotency, malformed input, stale data, outages, schema drift, contradictions, provenance loss, clock errors, and spatial-reference errors.

AI evaluation must cover evidence grounding, provenance correctness, tool-use correctness, uncertainty calibration, contradiction handling, unsupported-claim refusal, replayability where feasible, and regression cases.


## Prediction release gate

A prediction model cannot be promoted from evaluation results alone. For each declared horizon, the release gate requires a minimum sample count plus explicit maximum Brier score, maximum log loss, and maximum expected calibration error. The gate returns deterministic pass/fail reasons and must be evaluated against realized outcomes, never synthetic targets.
