# Engineering Constitution

Build and operate a production-grade, lawful OSINT/GEOINT World Intelligence platform.

**Trust execution, not claims.**

## Rules

- Evidence is immutable and provenance-backed.
- Observations, derived assertions, predictions, and scenarios remain distinct.
- Important derived claims are traceable to inputs, transformations, versions, and time.
- Contradictions are preserved and explicitly reconciled.
- Entity resolution is probabilistic unless independently proven.
- Historical state remains reproducible.
- Licensing and redistribution constraints are first-class metadata.
- AI output is untrusted until validated.
- Security, auditability, observability, and failure behavior are implementation requirements.
- No production merge based only on a demo.

## Lawful-use boundary

Use only public, licensed, user-authorized, or synthetic/test data. Do not implement unauthorized access, credential harvesting, access-control bypass, covert collection, named-person surveillance, facial identification, stalking, or private-device tracking.

## Agent operating model

Agents implement bounded tasks. The default integration branch is the protected integration boundary. Every task must state its objective, affected subsystem, dependencies, acceptance criteria, security/data constraints, tests, observability requirements, and provenance implications.

Core contract changes require architecture review.

## Definition of done

Production changes require implementation, tests, contract/schema validation, provenance preservation, security review, observability, documentation, recovery strategy, and replayable evaluation where applicable.

Never commit secrets, credentials, private data, or proprietary source data to fixtures.

Never claim production readiness without executable evidence.
