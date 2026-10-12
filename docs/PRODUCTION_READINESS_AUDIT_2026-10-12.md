# QuantSoil production-readiness gap audit — 2026-10-12

## Scope and evidence boundary

This is a repository inspection, not a claim that the deployed service or a physical Android device has been verified. The main branch inspected for this report was `97b88be58b02e9fbb216efc589426b08cbfd7978`; current proposed hardening is in PR #50 and must not be treated as released until merged and deployed.

## Current verified evidence

- The CI run for PR #50 commit `4460bf92ce303f17e30797d5e24732718ae92f48` passed the repository integrity and frontend build jobs.
- PR #50 enabled Cesium scene-mode morphing and documented a constrained Bedrock profile-selection fallback.
- Follow-up changes in this branch add a bounded response-body check to public JSON feeds, split antimeridian-crossing aircraft viewport queries, deduplicate merged aircraft by feature ID, and preserve explicit ADS-B `on_ground` flags. CI for the latest follow-up commit must pass before these changes are considered validated.
- Public aircraft data comes from ADS-B receiver networks; it is regional and incomplete by design. Orbital positions are propagated from a station-group TLE feed, not direct real-time satellite observations.

## Blocking gaps before a defensible 100% acceptance claim

### P0 — deployment and security

1. **Bedrock workflow is not operationally proven.** The previous autonomous workflow failed at inference-profile selection because the deployed role lacked `bedrock:ListInferenceProfiles`. PR #50 improves diagnostics and permits an explicitly configured allowlisted profile ID, but it does not alter AWS IAM or prove inference invocation. Apply the least-privilege Terraform policy with an authorized AWS identity, or configure `GODS_EYE_BEDROCK_PROFILE_ID` only after validating profile availability and invocation permission; then rerun the workflow.
2. **Production authentication must be enforced.** Analyst API middleware defaults `ANALYST_AUTH_MODE` to `optional`. Production must set it to `required` and provide a managed secret for `ANALYST_BEARER_TOKEN`, or enforce equivalent strong authentication at a trusted gateway. Verify unauthorized requests fail closed and health-check exposure is intentional.
3. **No live deployment verification is evidenced here.** Validate TLS, DNS, reverse-proxy route mapping (including the frontend's `/v1/analyst` API base), secret delivery, OIDC trust, least-privilege IAM, Kubernetes network policy and restricted pod security against the actual target environment.
4. **Recovery is unproven.** Execute a database backup/PITR restore drill, evidence/object-storage recovery drill, and service restart/outage recovery test. Record timings and integrity checks.

### P1 — fidelity and end-to-end functionality

5. **Aircraft trails require a trustworthy history pipeline.** A live position snapshot is not a historical track. Persist timestamped observations with source IDs, event time, retrieval time, freshness, provenance, and retention policy; render trails only from actual historical points and visually distinguish stale/derived data. Test that refreshes do not make aircraft disappear and that camera changes do not cause excessive source requests.
6. **Maritime AIS and authorized camera feeds are not configured as working live providers.** Add only licensed/public/explicitly authorized integrations, with provider terms, rate limits, attribution, coverage disclaimers, and source-health checks. Do not display placeholders as live observations.
7. **Entity-to-evidence workflow needs deployed end-to-end acceptance.** Verify search → entity inspector → evidence/provenance → timeline → spatial snapshot, including empty states, source outages, stale observations, invalid data, and permission-denied responses.
8. **Cesium optional capabilities depend on deployment configuration.** Terrain/buildings requiring a Cesium ion token must be configured and validated or clearly disabled with an actionable UI message. Verify satellite imagery availability/time handling, attribution, network errors, and fallback basemaps.
9. **Mobile and 2D/3D runtime acceptance is outstanding.** Test on a real Android browser/device: touch targets, scroll/gesture conflicts, layer drawer, search, selected entity, timeline, mode changes, resize/orientation, low-memory behavior, aircraft motion/trails, and console/network errors. A successful frontend build is not proof of usable interactions.

### P2 — operations and scale

10. **Source health and resilience.** Add observable success/failure/latency/freshness metrics, bounded retries with jitter where safe, provider-specific rate limits, timeouts, cache policy, and explicit stale/degraded states. Never convert upstream errors into a false empty-data success.
11. **Performance and capacity.** Establish target viewports/entity counts, API latency budgets, frontend frame-rate expectations, load tests, and recovery tests. Bound request fan-out and data sizes; verify cancellation of obsolete viewport requests.
12. **Data governance.** Document source licensing, retention/deletion, audit access, data-quality gates, provenance lineage, and policy for sensitive location data. Keep inferred/propagated positions visibly distinct from observed facts.
13. **Release and operations.** Define release promotion, rollback, migration compatibility, SBOM/dependency scanning, vulnerability triage, alert ownership, and an operator runbook. Confirm that the Termux checkout is separately updated; GitHub changes do not update a phone's local working tree.

## Required acceptance gates for a 100% claim

- [ ] Latest PR checks pass on the latest commit, including all tests and frontend build.
- [ ] Changes reviewed and merged into `main`; release artifact deployed to the intended environment.
- [ ] AWS OIDC and Bedrock profile selection/invocation succeed under least privilege.
- [ ] Production auth is verified fail-closed; TLS, proxy routing, network policy, and secrets are verified in deployment.
- [ ] Live public sources pass freshness, malformed-response, oversized-body, outage, and antimeridian tests.
- [ ] Aircraft trails are generated from persisted timestamped observations and never fabricated from a single point.
- [ ] Search, layers, entity inspector, evidence, timeline, and 2D/3D controls pass browser end-to-end tests and real-device Android acceptance.
- [ ] Authorized maritime/camera integrations are either operational and attributed or explicitly marked unavailable (never falsely live).
- [ ] Backup/PITR restore, outage recovery, load/performance, observability, and rollback drills pass with recorded evidence.
- [ ] Deployment and Termux/local instructions are current and reproducible.

## Status

**Not 100% production-ready yet.** CI establishes that the checked code compiles and the automated repository checks pass; it does not establish live provider coverage, deployed IAM, production security, real-device usability, historical track persistence, or disaster recovery. Close the gates above and attach execution evidence before claiming complete production readiness.
