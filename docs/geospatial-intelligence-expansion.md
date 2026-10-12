# QuantSoil Geospatial Intelligence Expansion

Status: architecture and implementation contract; not a claim that every provider or UI layer is already implemented.

## Objective

Evolve QuantSoil's existing evidence-first OSINT/GEOINT foundation into an interactive, multi-source geospatial operations workspace inspired by the uploaded reference Reel, without mistaking a polished visualization for verified intelligence.

## Non-negotiable trust rules

1. Every observation records provider, source object ID where available, observed-at, retrieved-at, ingestion time, license/terms reference, schema version and content hash.
2. Preserve source payloads as immutable evidence subject to retention and provider terms; normalized records reference evidence IDs.
3. Distinguish observed, derived, estimated/interpolated, simulated and predicted values in API contracts and UI labels.
4. Never describe a feed as live without source timestamp and freshness state. Display stale, delayed, unavailable and simulated distinctly.
5. Provider outages degrade only their own layer. Use bounded retries, backoff with jitter, timeouts, rate limits, cache TTLs, circuit breakers and health metrics.
6. Public data is not necessarily unrestricted: honor API terms, attribution, rate limits, privacy requirements and applicable law.
7. Do not implement unauthorized camera access, private-device tracking, credential bypass, person identification, stalking or covert collection. Index public camera feeds only where access is authorized and use is lawful.
8. Do not infer military status, hostility or threat solely from a label or heuristic. Show classification method and confidence.

## Target architecture

Provider adapters -> source validation -> normalized observation -> provenance/evidence store -> temporal world state -> API/query service -> interactive map and analyst tools.

### Adapter contract

Each adapter declares stable provider ID, documentation URL, license/terms, attribution, entity types, coverage, authentication requirements, polling/streaming mode, minimum interval, request budget, timeout/cache policy, schema version, parser, validation rules, source timestamp semantics, known limitations and health state.

Normalized envelope: observation_id, provider_id, entity_type, source_entity_id, geometry, properties, observed_at, retrieved_at, valid_time, source_url, license_id, content_hash, quality_flags, provenance_refs and schema_version. Geometry has explicit CRS; API boundaries use WGS84 longitude/latitude and reject invalid coordinates.

## Data-layer roadmap

### Priority A: verifiable public sources
- Aircraft: adsb.lol or appropriately licensed ADS-B Exchange API. Preserve source time, coverage limits and attribution.
- Satellites: CelesTrak GP data in modern OMM/JSON formats and SGP4 propagation. Store element epoch; propagated positions are derived estimates, not live telemetry.
- Earthquakes: USGS GeoJSON feeds; preserve event ID, origin time, magnitude, depth, update time and source URL.
- Weather: Open-Meteo or authorized national meteorological sources. Separate forecasts from observations and preserve model/issue times.
- Satellite imagery: NASA GIBS or other licensed imagery, with acquisition time, product ID, resolution, projection and processing level. Never assume imagery is real-time.
- Base geography: OpenStreetMap and suitable public boundary datasets with attribution and caching policy.
- India-specific context: prefer official/authorized sources and document coverage/update limitations.

### Priority B: enable only after terms and behavior are verified
- Maritime AIS from a licensed/authorized provider, with coverage and reception time.
- NASA FIRMS fire/hotspot detections, preserving satellite observation time and confidence.
- Weather radar, flood, volcano, water and disaster feeds with documented refresh semantics.
- Official or explicitly authorized public transport/camera feeds; never scrape access-controlled feeds.
- Traffic feeds; distinguish observed traffic from static OSM roads and synthetic animated particles.
- News/geopolitical events with citations, publication time, location uncertainty and corroboration. Avoid unsupported threat verdicts.
- Internet outage and space-weather feeds from published providers.

### Priority C: analyst capabilities
- Global and area-of-interest search, coordinate/place lookup with attribution.
- Layer tree with visibility, filters, refresh state, count, legend and source details.
- Entity inspector with raw/normalized fields, timestamps, source link, quality flags and evidence chain.
- Tracks built only from time-ordered observations; show gaps, never fabricate continuity.
- Satellite ground tracks from versioned elements, explicitly labelled propagated calculations.
- Timeline playback from persisted observations with speed controls, time window and replay indicator.
- Bounding-box/polygon selection, measurement, bookmarks, annotations and provenance-preserving exports.
- Clustering and level-of-detail; preserve hit-testing on touch devices.
- Accessible controls, keyboard alternatives, mobile-responsive panels and explicit loading/error/empty states.

## UI behavior contract

Every visible control must have a real action and test: layer toggle changes visibility; marker selection opens an inspector; follow/lock has visible unlock; timeline changes displayed observation time; refresh invokes the corresponding query and reports failure; search returns results or explicit empty/error state; camera reset restores a known view; filters actually filter data; controls remain touch-usable.

Moving markers may use source timestamps and bounded interpolation for visual smoothness. Render a trail only when multiple timestamped positions exist. Never create fake trails from one point. Differentiate extrapolated motion from received observations.

## API and persistence guidance

- Keep provider network calls server-side when keys, terms, CORS or quotas require it.
- Use PostgreSQL/PostGIS for canonical spatial-temporal state with indexed geometry/time and bounded queries.
- Cache by provider TTL and use conditional requests where supported.
- Expose per-adapter health, last success/error, latency, response age, parse failures, rate-limit events and record counts.
- Bound query limits and payload sizes; enforce authorization for private notes/workspaces.
- Exports include source, timestamps, license, transformation/version and uncertainty.
- Backfills and replays are idempotent and auditable.

## Verification gates

1. Unit tests for parsers, missing/malformed fields, invalid coordinates, stale timestamps, duplicates and provider errors.
2. Contract tests using checked-in synthetic fixtures; CI must not depend on live APIs.
3. Integration tests for PostGIS queries, provenance references, temporal ordering and idempotency.
4. Frontend tests for layer toggles, marker selection, inspector, filters, timeline, refresh, search, keyboard and touch.
5. End-to-end fixture test proving clickability and multi-point trails.
6. Security tests for SSRF, outbound allowlists where relevant, rate limiting, secret handling, authorization, injection and oversized payloads.
7. Accessibility checks for focus, labels, contrast and keyboard operation.
8. Performance tests at 1k, 10k and 25k entities on target devices including Android.
9. Operational acceptance: deployment, readiness, migrations, backup/restore drill, monitoring, runbooks and rollback.
10. UI claims labelled verified, derived, predicted, simulated or unverified.

## Delivery sequence

1. Audit and reuse existing connectors, evidence contracts, world-state projection, Cesium viewer and tests; avoid duplicate abstractions.
2. Fix interaction/movement defects first and add regression tests.
3. Standardize provider registry and adapter contract.
4. Harden aircraft/satellite trails and timestamp semantics.
5. Complete USGS, weather and imagery layers behind the same contracts.
6. Add replay, inspector, search, filters, health and provenance UI.
7. Add maritime/fire/camera/traffic only after source terms are verified.
8. Run CI and target-device smoke tests; do not claim production-ready until all gates pass.

## Reference documentation

- ADS-B Exchange API: https://www.adsbexchange.com/api/aircraft/v2/docs
- CelesTrak GP formats: https://celestrak.org/NORAD/documentation/gp-data-formats.php
- USGS APIs: https://www.usgs.gov/faqs/does-usgs-have-apis
- NASA GIBS: https://www.earthdata.nasa.gov/data/tools/gibs
- OpenStreetMap attribution: https://www.openstreetmap.org/copyright
- Open-Meteo API: https://open-meteo.com/en/docs
- CesiumJS: https://cesium.com/learn/cesiumjs/ref-doc/
- PostGIS: https://postgis.net/documentation/

## Definition of done

This is an architecture/acceptance contract, not evidence that the roadmap is implemented. A feature is complete only when code, tests, provenance, error handling, documentation and CI evidence are present and reviewed.
