# Production Acceptance

This document records what is executable in the repository and what requires target infrastructure.

## Repository gates

The CI pipeline must pass:
- JSON schema validation
- Python compilation
- full migration application against PostGIS
- Kubernetes YAML parsing
- scripts/production_acceptance.py
- unit and integration tests included by CI
- Cesium analyst UI build

production_acceptance.py additionally verifies required architecture/security/recovery artifacts, migration-chain continuity, Restricted Pod Security controls, default-deny network policy, disruption-budget and cluster-acceptance artifacts, shell syntax, and a basic embedded-secret scan.

## Target-infrastructure gates

These cannot honestly be marked PASS from source control alone:

1. Identity boundary
   - terminate TLS at the production gateway
   - enforce OAuth/OIDC authentication and least-privilege authorization
   - deny direct backend exposure
   - retain gateway and service audit correlation

2. Kubernetes
   - apply manifests to the target cluster
   - verify Pod Security Admission enforcement
   - verify NetworkPolicy behavior from actual namespaces/selectors
   - verify rolling update, readiness/liveness behavior, and PodDisruptionBudgets\n   - run `scripts/production_cluster_acceptance.sh` and retain its output as deployment evidence

3. Database
   - run the complete migration chain on the production-compatible PostGIS version
   - verify connection pooling and failure recovery
   - execute an isolated backup/restore test
   - if PITR is required, verify WAL archiving and a point-in-time recovery target

4. Evidence storage
   - private bucket with public access blocked and TLS-only access enforced
   - versioning/Object Lock policy where required
   - workload identity/IRSA or equivalent short-lived credentials
   - verify payload hash retrieval after restore

5. Spatial performance
   - run representative vector-tile queries against production-sized data
   - capture p50/p95/p99 latency and error rate
   - verify spatial indexes are used
   - test bounded tile coordinates and response-size limits

6. Prediction evaluation
   - link forecasts to realized outcomes after their declared horizons
   - evaluate Brier/log loss by horizon
   - monitor calibration and deterministic drift signals
   - define and enforce model-promotion thresholds

7. 24/7 operations
   - exercise connector outage and recovery
   - reclaim an expired lease
   - verify duplicate scheduling is idempotent
   - verify alerts for readiness failures, repeated connector errors, stale/rejected data, failed jobs, and evidence persistence failures

## Acceptance rule

The system is production-ready candidate only when repository CI is green and every applicable target-infrastructure gate above has an attached execution result.

Do not convert documentation into a deployment claim.
