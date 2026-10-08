# Major Update — God's Eye View

QuantSoil's browser surface is being expanded from an evidence-backed analyst globe into a **God's Eye View spatial-intelligence command center**.

## Capability packs

| Pack | QuantSoil role | Integration policy |
|---|---|---|
| GeoLens | spatial catalog, datasets, OGC/STAC concepts | adapter/compatibility, not copied source |
| World Monitor | global event/news context and layer orchestration | adapter/compatibility |
| Iron Sight | conflict-monitoring workspace | adapter/compatibility |
| Pythia | forecast/scenario workspace | local prediction interface |
| Wanderer | trails/routes and temporal movement context | route/trail interface |
| Open-Meteo | weather, marine and air-quality context | direct public API adapter |
| God's Eye View | primary 3D command-center UI | CesiumJS + governed live-feed gateway |

## Live layers in this update

- Aircraft: OpenSky bounding-box state vectors.
- Aircraft near a point: ADSB.lol.
- Satellites: CelesTrak current GP/OMM JSON, propagated in-browser with Satellite.js/SGP4.
- Earthquakes: USGS GeoJSON feeds.
- Weather: Open-Meteo current + short forecast.
- Optional Google Photorealistic 3D Tiles: enabled only when a provider-restricted VITE_GOOGLE_MAPS_API_KEY is configured.
- Optional AISStream ships, NASA FIRMS fires, and OpenAI Realtime voice are explicitly capability-gated; the application must never fabricate those layers when credentials are absent.

## Evidence and licensing boundary

Live third-party feeds remain **volatile external observations**. They are not silently promoted to authoritative world state. Persistent evidence must continue through the existing ingestion, provenance, audit, and projection boundaries.

We do not copy AGPL application source from World Monitor or Wanderer into QuantSoil. World Monitor and Wanderer are AGPL projects; GeoLens is Apache-2.0 with separate trademark rules; Pythia and IronSight are MIT. QuantSoil therefore integrates capabilities through public interfaces, adapters, and independent implementations while preserving attribution and source terms.

God's Eye View upstream is MIT, but its third-party data and visual assets have separate terms. QuantSoil must keep source attribution and data-provider restrictions explicit.

## Safety posture

This command center remains evidence-first and lawful. It does not add named-person search, face recognition, private-device tracking, credential collection, or covert collection. Modeled/inferred data must be labeled as such.

## Implementation status

The repository now contains real provider adapters for OpenSky, ADSB.lol, USGS, CelesTrak, Open-Meteo, NASA FIRMS (credential-gated), and AISStream (server-side credential-gated websocket ingestion). The browser exposes aircraft, satellites, earthquakes, wildfire and ship layers without treating unavailable credentials as live data.

The following are intentionally provider-gated rather than falsely represented as universal keyless services: live global traffic, a global public-camera catalog, world radio station metadata, Google Photorealistic 3D Tiles, NASA FIRMS, AISStream, and OpenAI Realtime. There is no single authoritative global API for the first three; production integration requires selecting and licensing a concrete provider/catalog.

The six named command profiles are implemented as QuantSoil-native governed workspaces/interfaces; they do not copy upstream AGPL application source.

## Acceptance gates

1. Backend live gateway starts with no API keys.
2. /v1/live/status reports keyless layers accurately.
3. OpenSky/ADSB.lol/USGS/Open-Meteo/CelesTrak failures degrade individual layers rather than taking down the analyst API.
4. Satellite propagation handles malformed/decayed objects without crashing the frame.
5. Google 3D remains optional and never requires a secret committed to Git.
6. Existing analyst and projection tests remain green.
7. Web build succeeds with the new live-layer controls.
8. Optional AISStream/FIRMS routes fail explicitly with 503 when credentials are absent; they never fabricate data.
9. The UI has no stale event-handler reference to a removed/nonexistent control.