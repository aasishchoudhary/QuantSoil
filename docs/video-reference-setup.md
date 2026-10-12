# Video-reference workspace setup

This guide explains how to enable the optional capabilities shown in the reference dashboard without inventing data or treating unavailable feeds as live.

## Included without provider credentials

- Cesium globe with OpenStreetMap base imagery.
- Public USGS past-hour earthquake observations.
- Regional ADS-B aircraft observations through adsb.lol, subject to receiver coverage.
- CelesTrak station-group TLE propagation using SGP4. These are derived orbital positions, not direct observations.
- NASA GIBS VIIRS corrected-reflectance imagery, available through the SATELLITE toggle.
- Aircraft symbols, heading rotation, short interpolation between changed positions, bounded in-memory trails, object inspection, timeline/search controls and source provenance.
- Optional licensed AIS and authorized camera-metadata connectors. They remain disabled until an operator configures a feed.

## Detailed terrain and buildings

Set `VITE_CESIUM_ION_TOKEN` at frontend build time to a public, domain-restricted Cesium ion token with only the assets required by the application. The token is bundled into browser code, so it is not a secret; restrict its allowed domains and asset permissions. Do not place a private server token in a `VITE_*` variable.

Without a token, the app uses ellipsoid terrain and does not claim photorealistic 3D buildings. Satellite imagery is not street-level aerial imagery or live video.

## Licensed AIS feed

Configure these backend environment variables:

- `QUANTSOIL_AIS_GEOJSON_URL`: HTTPS endpoint returning a GeoJSON FeatureCollection of Point features.
- `QUANTSOIL_AIS_BEARER_TOKEN`: optional token, kept server-side.
- `QUANTSOIL_AIS_PROVIDER_ID`: provider identifier used in provenance.
- `QUANTSOIL_AIS_LICENSE_ID`: license/authorization reference.

The adapter accepts point positions only, caps response size and feature count, validates WGS84 coordinates, and preserves source timestamps when parseable. Obtain the provider's permission, review attribution/redistribution terms, and set realistic rate limits before enabling it.

## Authorized camera metadata

Configure:

- `QUANTSOIL_AUTHORIZED_CAMERA_GEOJSON_URL`: HTTPS GeoJSON FeatureCollection of camera metadata Point features.
- `QUANTSOIL_AUTHORIZED_CAMERA_BEARER_TOKEN`: optional server-side token.
- `QUANTSOIL_AUTHORIZED_CAMERA_PROVIDER_ID` and `QUANTSOIL_AUTHORIZED_CAMERA_LICENSE_ID`: provenance and authorization metadata.

The camera connector handles metadata, not video transport. If a record includes `authorized_stream_url`, the inspector offers a separate external HTTPS link. QuantSoil does not discover private cameras, bypass access controls, or proxy video streams.

## API and deployment checks

1. Set the API's `DATABASE_URL` and required runtime dependencies.
2. In production, set `ANALYST_AUTH_MODE=required` and configure a strong `ANALYST_BEARER_TOKEN`; keep secrets in the deployment secret manager, not source control.
3. Route `/v1/analyst` to the analyst API and set `VITE_ANALYST_API_BASE=/v1/analyst` for the frontend build.
4. Configure provider environment variables only on the backend; do not expose bearer tokens through frontend `VITE_*` variables.
5. Verify each source endpoint from the deployed environment and check its provenance, freshness, licensing and failure state.
6. Run CI and test touch interactions on a real mobile browser.

The provider TTL cache is in-process. Multi-replica deployments should use a shared cache or coordinated rate limiting if aggregate request volume requires it.

## Known limitations

- ADS-B coverage is regional and depends on receiver availability; it is not guaranteed globally.
- Satellite positions are propagated from orbital elements and approximate Earth-fixed coordinates; they are not precision navigation solutions.
- Aircraft trails are bounded in-memory browser history and disappear on reload. They are not a persistent authoritative archive.
- A successful build does not prove external feed availability or deployment readiness.
- Maritime AIS and camera metadata remain unconfigured until a licensed/authorized endpoint is supplied.
