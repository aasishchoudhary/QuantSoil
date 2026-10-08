# God's Eye Analyst UI

CesiumJS 1.146 globe client for the evidence-first analyst API.

## Configuration

Set `VITE_ANALYST_API_BASE` to the runtime analyst base, for example
`/v1/analyst`. No provider API keys are required.

The UI never promotes client-side interpretation into authoritative state. It
only renders governed API results and their evidence references.

The OpenStreetMap tile service is used as a basemap and must retain its
attribution in deployed UX. CesiumJS is used for the 3D globe.
