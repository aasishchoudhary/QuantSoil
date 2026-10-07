# Map Backend

The map is a projection of the intelligence system, not the intelligence system itself.

## Data path

source -> connector -> observation -> evidence -> entity/event/world state -> map_features -> GeoJSON -> God's Eye / Analyst UI

### Guarantees

1. Every persisted map feature carries source identity and provenance.
2. WGS84 (EPSG:4326) is the external map interchange CRS.
3. PostGIS performs authoritative spatial filtering.
4. Temporal validity is explicit.
5. Confidence is bounded to [0,1].
6. Raw evidence hashes and parser versions remain attached to the projection.
7. Rendering never mutates evidence.

## Initial API

GET /health

GET /v1/map/features?bbox=minLon,minLat,maxLon,maxLat&at=<ISO-8601>&limit=500

The response is a GeoJSON FeatureCollection plus generation metadata. Each feature exposes source, source_record_id, observation_id, observed_at, confidence, raw_payload_hash, parser_version, and license_class so a rendered object remains traceable to its evidence boundary.

## Production path

The Python API establishes the contract and a dependency-free repository implementation for tests. Its in-memory geometry filter is a conservative bbox candidate check; PostGIS remains the authoritative spatial execution path. The repository now includes a DB-API-compatible PostGIS adapter backed by map_features_in_bbox. Remaining production hardening includes authenticated gateway integration, RBAC, audit events, pagination/tiles, and source/license policy enforcement.

## Map clients

The backend is renderer-agnostic. CesiumJS can consume the same spatial contracts used by a 2D map client, while future vector-tile/3D-tile services can be added without changing the evidence model.
