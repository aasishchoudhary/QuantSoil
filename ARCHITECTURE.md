# Architecture

Evidence-first world intelligence: sources → governed connectors → bounded retry/health → ingestion/quality → evidence ledger → entity resolution → ontology → temporal world state → contradiction/fusion → audit/replay → analyst tools → visualization/prediction.

The first live public connector is the USGS earthquake GeoJSON feed. It is intentionally no-key, fixture-testable, provenance-preserving, and isolated behind the connector contract.

## Invariants
- Raw evidence is immutable and content-addressed.
- Observations and predictions are separate types.
- Derived assertions retain provenance.
- Contradictions are preserved, never silently overwritten.
- Entity matches carry uncertainty and evidence.
- Historical state is reproducible at a requested time.
- Provider licenses are first-class metadata.
- AI cannot write unverified facts directly into authoritative state.
- Sensitive operations are audited.
- Replay/evaluation gates production releases.

## Stack
TypeScript/React/CesiumJS; Python/FastAPI; PostgreSQL/PostGIS; S3-compatible storage; OpenSearch; Redis; Kafka-compatible bus; GDAL/Rasterio/GeoPandas/DuckDB.