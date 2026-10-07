# Geospatial / Map Service

The map service is the authoritative read/write boundary for geospatial intelligence primitives used by the analyst map and 3D globe.

## Responsibilities

- Store and query points, lines, polygons, and bounding boxes in PostGIS.
- Preserve observation/evidence references for every authoritative feature.
- Return GeoJSON-compatible feature collections for map clients.
- Support temporal filtering without rewriting historical observations.
- Keep map rendering concerns separate from intelligence state.

## Non-goals

- No private-device tracking.
- No facial recognition or named-person surveillance.
- No bypass of access controls.
- No assumption that a rendered feature is current truth.

## API contract

GET /v1/map/features?bbox=minLon,minLat,maxLon,maxLat&at=<ISO-8601>&limit=500

The endpoint returns GeoJSON FeatureCollection objects. Production deployments must apply authentication, authorization, tenant/source policy, rate limits, and audit logging at the gateway/service boundary.
