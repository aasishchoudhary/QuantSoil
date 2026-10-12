# QuantSoil Public Geospatial Source Registry

This is an initial governance catalogue. Listing a provider does not mean its adapter is implemented, enabled, continuously available or production-approved. Verify current terms and endpoint limits before enabling connectors.

## Current implementation status (2026-10-12)

- **USGS past-hour earthquakes:** adapter implemented in `services/analyst/public_sources.py`; exposed through `GET /sources/earthquakes` on the analyst API. It is a public feed, not a guarantee of instantaneous detection.
- **adsb.lol regional aircraft:** adapter implemented in `services/analyst/public_sources.py`; exposed through `GET /sources/aircraft?bbox=minLon,minLat,maxLon,maxLat`. It queries the viewport center with a bounded radius and is subject to volunteer receiver coverage, provider availability and provider limits.
- **CelesTrak station-group orbital objects:** adapter implemented in `services/analyst/orbital_sources.py`; exposed through `GET /sources/orbital`. TLEs are propagated with SGP4 and converted from TEME to WGS84; resulting positions are derived/predicted, not direct observations.
- **Optional maritime AIS:** `GET /sources/maritime` consumes an operator-configured HTTPS GeoJSON point feed using `QUANTSOIL_AIS_GEOJSON_URL`; optional bearer token, provider ID and license ID use `QUANTSOIL_AIS_BEARER_TOKEN`, `QUANTSOIL_AIS_PROVIDER_ID`, and `QUANTSOIL_AIS_LICENSE_ID`. No provider is enabled by default.
- **Authorized camera metadata:** `GET /sources/cameras` consumes an operator-configured HTTPS GeoJSON point feed using `QUANTSOIL_AUTHORIZED_CAMERA_GEOJSON_URL`; optional bearer token, provider ID and license ID use corresponding `QUANTSOIL_AUTHORIZED_CAMERA_*` variables. Metadata only; the endpoint does not proxy, unlock or scrape video streams.
- **NASA GIBS imagery:** optional browser imagery toggle uses VIIRS corrected-reflectance imagery with a two-day date offset. It is satellite imagery, not street-level aerial photography or live video.
- **Cesium World Terrain / OSM Buildings:** optional frontend control is available when `VITE_CESIUM_ION_TOKEN` is supplied at build time. Use a public, domain-restricted token with only required asset access; do not commit tokens to source control. This capability is not enabled in builds without the variable.
- **Global map metadata search:** implemented through `GET /search?q=...` in the analyst API, backed by the PostGIS trigram index on map feature metadata. The in-memory repository supports local/test searches. This searches indexed map projections; it is not a web-wide search engine.
- **Not implemented by this change:** maritime AIS, CCTV/video feeds, traffic feeds, or a persistent backend history store for aircraft positions.

A route being present does not guarantee network reachability from a particular deployment. Provider failures return explicit errors and the UI should continue to identify unavailable sources rather than inventing data.

| Layer | Candidate source | Data type | Freshness semantics | Safeguards |
|---|---|---|---|---|
| Aircraft | adsb.lol | ADS-B reports | Source observation time; receiver coverage varies | Respect limits; expose stale/coverage state |
| Aircraft | ADS-B Exchange API | Flight state/history where authorized | Provider timestamp | Terms, key secrecy, attribution and quota |
| Satellites | CelesTrak GP/OMM | Orbital elements | Element epoch; propagated position is derived | Use modern OMM/JSON for six-digit catalog IDs; label propagation |
| Earthquakes | USGS GeoJSON | Seismic reports | Origin and update times | Preserve event ID, revision and source URL |
| Weather | Open-Meteo | Forecasts/available observations | Model/forecast time differs from retrieval time | Attribute and obey applicable terms/limits |
| Satellite imagery | NASA GIBS | Imagery layers | Product/acquisition time, not assumed live | Preserve product metadata, projection and attribution |
| Fire/hotspots | NASA FIRMS | Satellite detections | Satellite observation time | Key where required, terms, confidence and acquisition time |
| Base map | OpenStreetMap | Roads/geographic features | Dataset/tile-specific; not live traffic | Attribution, tile policy, no bulk scraping |
| Maritime | Authorized AIS provider | Vessel AIS reports | Report/reception time; coverage varies | License, quota and no universal-coverage claims |
| Cameras | Official/authorized feeds | Public camera metadata/video | Provider-specific | No access-control bypass; privacy and terms |
| Traffic | Official traffic feeds | Observed conditions | Provider update time | Separate observations from static roads/simulation |
| Weather hazards | Official weather/disaster feeds | Alerts/radar/warnings | Issue time, valid period, update time | Preserve validity; avoid stale alerts |
| Space weather | NOAA SWPC | Solar/geomagnetic products | Product-specific | Show product time; separate forecast from observation |
| Geocoding | Nominatim or authorized provider | Place lookup | Request-time result, not tracking | Respect usage policy, identify client, cache appropriately |

## Provider request caching

The analyst API caches successful USGS responses for 60 seconds, CelesTrak orbital propagation results for 60 seconds, and ADS-B viewport responses for 15 seconds per rounded bounding box. Failures are not cached as successful empty data. The in-process cache is bounded and is local to each API process; multi-replica deployments should use a shared cache or provider-specific rate limiting if aggregate request volume requires it.

## Normalized freshness states

- fresh: within provider-specific documented threshold.
- delayed: data exceeds preferred threshold.
- stale: data exceeds hard maximum age.
- unknown: source timestamp missing or uninterpretable.
- unavailable: request failed or provider unreachable.
- simulated: generated fixture/demo data, never presented as live observation.

Thresholds must be provider/layer-specific and tested; do not use a universal duration across aircraft, forecasts, satellite elements, imagery and earthquakes.

## Minimum observation fields

observation_id, provider_id, entity_type, source_entity_id, geometry, observed_at, retrieved_at, source_url, license_id, content_hash, quality_flags, provenance_refs and schema_version.

For derived positions also record derivation_method, input_observation_ids, algorithm_version, calculated_at and uncertainty where quantifiable.

## Source review checklist

- [ ] Official documentation and current terms reviewed
- [ ] Access method/authentication recorded
- [ ] Rate limit, cache and retry policy documented
- [ ] Source timestamp semantics confirmed
- [ ] Attribution/redistribution conditions recorded
- [ ] Fixture captured without secrets or prohibited personal data
- [ ] Parser, contract and failure tests pass
- [ ] Health metrics and stale state visible
- [ ] Retention/deletion policy reviewed
- [ ] Security and lawful-use review completed
