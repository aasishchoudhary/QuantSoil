# QuantSoil Public Geospatial Source Registry

This is an initial governance catalogue. Listing a provider does not mean its adapter is implemented, enabled, continuously available or production-approved. Verify current terms and endpoint limits before enabling connectors.

## Current implementation status (2026-10-12)

- **USGS past-hour earthquakes:** adapter implemented in `services/analyst/public_sources.py`; exposed through `GET /sources/earthquakes` on the analyst API. It is a public feed, not a guarantee of instantaneous detection.
- **adsb.lol regional aircraft:** adapter implemented in `services/analyst/public_sources.py`; exposed through `GET /sources/aircraft?bbox=minLon,minLat,maxLon,maxLat`. It queries the viewport center with a bounded radius and is subject to volunteer receiver coverage, provider availability and provider limits.
- **NASA GIBS imagery:** optional browser imagery toggle uses VIIRS corrected-reflectance imagery with a two-day date offset. It is satellite imagery, not street-level aerial photography or live video.
- **CelesTrak visual satellites:** a source adapter fetches public GP/TLE elements and propagates subpoint estimates using SGP4. These are derived positions, not direct sensor observations; the current transform is approximate and must not be used for precision navigation.
- **Aircraft track rendering:** the browser keeps a bounded in-memory path of distinct provider positions and animates a short transition between two genuine observations. It is not a predictive flight path or durable historical archive.
- **Frontend track rendering:** the browser retains a bounded in-memory path for returned aircraft positions and animates a short transition between two distinct provider observations. This is presentation interpolation, not a prediction of future aircraft movement; the path is lost on reload and is not authoritative historical storage.
- **Still not implemented:** maritime AIS, CCTV, traffic feeds, photorealistic real-time 3D terrain/buildings, a global entity search service, and a persistent backend history store for aircraft positions.

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

## Runtime validation status\n\nCI verifies source parsing, API code compilation, frontend compilation and unit-test behaviour. It does not prove that external providers are reachable from a deployment, that credentials and rate limits are configured, or that the browser has been end-to-end tested on a phone. Verify provider connectivity and visual behaviour in the deployed environment before treating this workspace as operational.\n\n## Normalized freshness states

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
