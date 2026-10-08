# God's Eye World Intelligence

Production-grade lawful OSINT/GEOINT platform: evidence first, provenance always, reproducible intelligence.

## Current foundation

The repository now contains executable foundations for:

- immutable evidence contracts and PostgreSQL persistence;
- deterministic Observation → Evidence conversion;
- explicit observed / derived / predicted Event semantics;
- repository-neutral provenance tracing;
- evidence-aware geospatial map contracts and PostGIS execution;
- provider-neutral inference control;
- bounded autonomous engineering through GitHub Actions + AWS OIDC/Bedrock.

## Trust model

```
source
  -> observation
  -> content hash + provenance validation
  -> immutable evidence
  -> event / world-state projection
  -> provenance trace
  -> validated inference
  -> intelligence
```

AI output is untrusted until it passes deterministic contract validation. Observations, derived assertions, and predictions are not interchangeable.

## Engineering model

Every production slice is expected to include implementation, executable tests, contract/schema validation, provenance preservation, security boundaries, failure behavior, and replayability where applicable.

The autonomous engineering control plane runs on a five-minute GitHub Actions schedule plus manual and main-branch triggers. It creates isolated branches and pull requests; architectural changes remain review-gated.

## Lawful-use boundary

Use only public, licensed, user-authorized, or synthetic/test data. The project does not implement unauthorized access, credential harvesting, access-control bypass, covert collection, named-person surveillance, stalking, facial identification, or private-device tracking.
