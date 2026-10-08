# Analyst Layer

The analyst layer is a read-only intelligence surface over authoritative evidence-backed projections.

## Query paths
- GET /v1/analyst/snapshot?entity_ids=...&at=...
- GET /v1/analyst/timeline/{entity_id}?start=...&end=...
- GET /v1/analyst/spatial?bbox=...&at=...&limit=...

The runtime mounts these routes over PostgreSQL world state and PostGIS map projections.

## Invariants
1. Analyst queries never mutate authoritative observations or world state.
2. Historical queries require timezone-aware timestamps.
3. Spatial queries use WGS84 coordinates and bounded result limits.
4. Returned states preserve evidence references.
5. Derived rules may create only derived events and must preserve evidence references.
6. Predictions remain a separate state and cannot be promoted into authoritative state by the analyst layer.
7. Runtime audit telemetry records endpoint, status, and correlation ID without logging bearer tokens or raw query payloads.
8. Production authentication is expected at a trusted API gateway; direct service exposure must be prevented by deployment networking.

## UI
apps/gods-eye-web provides a CesiumJS globe and timeline panel. It consumes only the analyst API. It does not contain provider credentials and does not write intelligence state.

## Security
The API supports an optional deployment-controlled bearer-token boundary for isolated deployments. For production, prefer an external OAuth/OIDC gateway with least-privilege authorization and prevent direct backend access, consistent with OWASP API authorization guidance.
