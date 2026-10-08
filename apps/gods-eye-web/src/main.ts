import {
  Viewer,
  Cartesian3,
  Cartesian2,
  Cartographic,
  JulianDate,
  SampledPositionProperty,
  ClockRange,
  ExtrapolationType,
  BillboardGraphics,
  PropertyBag,
  Color,
  LabelStyle,
  ConstantProperty,
  PathGraphics,
  DistanceDisplayCondition,
  GeoJsonDataSource,
  OpenStreetMapImageryProvider,
  EllipsoidTerrainProvider,
  ScreenSpaceEventHandler,
  createGooglePhotorealistic3DTileset,
  ScreenSpaceEventType,
  type Entity,
} from "cesium";
import "cesium/Build/Cesium/Widgets/widgets.css";
import "./style.css";
import * as satellite from "satellite.js";

const API = import.meta.env.VITE_API_BASE || "";
const app = document.querySelector<HTMLDivElement>("#app")!;

function apiUrl(path: string): string {
  return `${API}${path}`;
}

app.innerHTML = `
<div class="app-shell">
  <header class="topbar">
    <div class="mobile-controls">
      <button id="mobile-left" title="Open investigation controls">☰</button>
      <button id="mobile-right" title="Open analyst inspector">▤</button>
    </div>
    <div class="brand">
      <div class="brand-mark">GE</div>
      <div><strong>GOD'S EYE</strong><span>WORLD INTELLIGENCE</span></div>
    </div>
    <div class="mission">
      <span class="eyebrow">MISSION</span>
      <span id="mission-name">GLOBAL SITUATIONAL AWARENESS</span>
    </div>
    <div class="system-status"><i id="status-dot"></i><span id="status">INITIALIZING</span></div>
  </header>

  <main class="workspace">
    <aside class="left-rail">
      <section class="panel-section">
        <div class="section-head"><span>INVESTIGATION</span><b>01</b></div>
        <label class="field-label" for="entity">ENTITY / OBJECT ID</label>
        <div class="search-row">
          <input id="entity" autocomplete="off" placeholder="e.g. entity-001"/>
          <button id="inspect" title="Inspect entity">↗</button>
        </div>
        <div class="quick-actions">
          <button id="global-view">GLOBAL</button>
          <button id="india-view">INDIA</button>
          <button id="reset-view">RESET</button>
        </div>
        <label class="field-label time-label" for="analysis-time">ANALYSIS TIME (UTC)</label>
        <input id="analysis-time" type="datetime-local"/>
      </section>

      <section class="panel-section">
        <div class="section-head"><span>DATA LAYERS</span><b>02</b></div>
        <label class="toggle"><input id="layer-entities" type="checkbox" checked/><span></span><em>WORLD STATE ENTITIES</em></label>
        <label class="toggle"><input id="layer-aircraft" type="checkbox" checked/><span></span><em>AIRCRAFT / OPENSKY • AUTO-ON</em></label>
        <label class="toggle"><input id="layer-satellites" type="checkbox"/><span></span><em>SATELLITES / CELESTRAK</em></label>
        <label class="toggle"><input id="layer-earthquakes" type="checkbox"/><span></span><em>EARTHQUAKES / USGS</em></label>
        <label class="toggle"><input id="layer-fires" type="checkbox"/><span></span><em>WILDFIRE / NASA FIRMS</em></label>
        <label class="toggle"><input id="layer-ships" type="checkbox"/><span></span><em>SHIPS / AISSTREAM</em></label>
        <label class="toggle"><input id="layer-weather" type="checkbox"/><span></span><em>WEATHER / OPEN-METEO</em></label>
        <label class="toggle"><input id="layer-labels" type="checkbox" checked/><span></span><em>MAP LABELS</em></label>
      </section>
      <section class="panel-section">
        <div class="section-head"><span>COMMAND PROFILES</span><b>03</b></div>
        <div class="module-grid">
          <button class="module-btn" data-module="geolens">GEOLENS</button>
          <button class="module-btn" data-module="world-monitor">WORLD MONITOR</button>
          <button class="module-btn" data-module="iron-sight">IRON SIGHT</button>
          <button class="module-btn" data-module="pythia">PYTHIA</button>
          <button class="module-btn" data-module="wanderer">WANDERER</button>
          <button class="module-btn" data-module="open-meteo">OPEN-METEO</button>
        </div>
        <div class="quick-actions"><button id="flir-toggle">FLIR</button><button id="google-3d">GOOGLE 3D</button></div>
      </section>

      <section class="panel-section">
        <div class="section-head"><span>SOURCE POSTURE</span><b>03</b></div>
        <div class="metric-grid">
          <div><small>FEATURES</small><strong id="feature-count">—</strong></div>
          <div><small>SOURCES</small><strong id="source-count">—</strong></div>
          <div><small>EVIDENCE</small><strong id="evidence-count">—</strong></div>
          <div><small>CONFIDENCE</small><strong id="confidence">—</strong></div>
        </div>
      </section>

      <section class="panel-section doctrine">
        <div class="section-head"><span>ANALYTIC DOCTRINE</span><b>04</b></div>
        <p>Public-source intelligence is treated as evidence, not truth. Claims remain attributable, time-bounded and confidence-scored.</p>
        <div class="legend"><span><i class="real"></i>OBSERVED</span><span><i class="derived"></i>DERIVED</span><span><i class="predicted"></i>PREDICTED</span></div>
      </section>
    </aside>

    <section class="map-stage">
      <div id="globe"></div>
      <div class="map-overlay top-left">
        <span class="mode-tag">3D / WGS84</span><span id="view-coords">GLOBAL VIEW</span>
      </div>
      <div class="map-overlay top-right">
        <button id="refresh" class="icon-btn" title="Refresh intelligence layer">↻</button>
      </div>
      <div id="map-empty" class="map-empty">
        <div class="empty-kicker">WORLD MODEL</div>
        <h1>Awaiting authoritative state</h1>
        <p>The globe is live. Intelligence features appear when the governed analyst runtime and its evidence-backed world state are ready.</p>
      </div>
      <div class="aircraft-legend"><span>✈ AIRCRAFT</span><span>◆ JET</span><span>◉ ROTOR</span></div><div class="osm-attribution">© <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap contributors</a></div><div class="scale"><span>WGS84</span><span>GEOINT VIEW</span></div>
    </section>

    <aside class="right-panel">
      <section class="inspector-head">
        <div><span class="eyebrow">ANALYST</span><h2 id="inspector-title">Situation overview</h2></div>
        <span id="record-state" class="state-badge">NO SELECTION</span>
      </section>

      <section id="inspector" class="inspector-body">
        <div id="weather-card" class="inspector-card hidden">
          <div class="card-title">LIVE WEATHER • OPEN-METEO</div>
          <div id="weather-content" class="overview-grid"><span class="muted">Enable weather to load current conditions.</span></div>
          <div id="weather-updated" class="muted"></div>
        </div>
        <div class="overview-grid">
          <div><small>WORLD STATE</small><strong id="world-state">—</strong></div>
          <div><small>OBSERVED</small><strong id="observed-at">—</strong></div>
          <div><small>VALID FROM</small><strong id="valid-from">—</strong></div>
          <div><small>CONFIDENCE</small><strong id="entity-confidence">—</strong></div>
        </div>
        <div class="inspector-card">
          <div class="card-title">ENTITY PROPERTIES</div>
          <pre id="properties">Select an entity or run an investigation.</pre>
        </div>
        <div class="inspector-card">
          <div class="card-title">EVIDENCE & PROVENANCE</div>
          <div id="evidence-list" class="evidence-list"><span class="muted">No evidence selected.</span></div>
        </div>
        <div class="inspector-card">
          <div class="card-title">TEMPORAL CHANGE</div>
          <div class="timeline-actions"><button id="timeline">LAST 7 DAYS</button><button id="timeline-30">30 DAYS</button></div>
          <div id="timeline-results" class="timeline-results"><span class="muted">No temporal query executed.</span></div>
        </div>
      </section>
    </aside>
  </main>

  <footer class="bottombar">
    <div><span class="live-pulse"></span><b id="footer-status">READ-ONLY ANALYST</b><span>•</span><span>PROVENANCE PRESERVED</span></div>
    <div id="last-refresh">NOT REFRESHED</div>
  </footer>
</div>`;

const $ = <T extends Element>(selector: string) => document.querySelector<T>(selector)!;
const statusEl = $("#status");
const statusDot = $("#status-dot");
const emptyEl = $("#map-empty");
const resultsEl = $("#timeline-results");
const entityInput = $("#entity") as HTMLInputElement;
const analysisTimeInput = $("#analysis-time") as HTMLInputElement;
const featureCount = $("#feature-count") as HTMLElement;
const sourceCount = $("#source-count") as HTMLElement;
const evidenceCount = $("#evidence-count") as HTMLElement;
const confidenceEl = $("#confidence") as HTMLElement;
const dataSources = new Map<string, any>();
const liveSources = new Map<string, any>();
const aircraftEntities = new Map<string, Entity>();
const aircraftSamples = new Map<string, JulianDate[]>();
const aircraftPredictionTimes = new Map<string, JulianDate>();
const aircraftLastSeen = new Map<string, number>();
const satelliteEntities = new Map<string, Entity>();
let liveClockInitialized = false;
const AIRCRAFT_TRAIL_SECONDS = 300;
const AIRCRAFT_LEAD_SECONDS = 30;
const AIRCRAFT_STALE_SECONDS = 75;
const AIRCRAFT_LABEL_ZOOM_METERS = 1800000;
const SATELLITE_ORBIT_SECONDS = 2 * 60 * 60;
const SATELLITE_SAMPLE_SECONDS = 240;
const AIRCRAFT_ICON = "data:image/svg+xml;charset=UTF-8," + encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64"><path d="M32 3 L39 27 L57 35 L57 41 L39 37 L36 60 L28 60 L25 37 L7 41 L7 35 L25 27 Z" fill="#e8f7ff" stroke="#07131d" stroke-width="3" stroke-linejoin="round"/></svg>`);
const JET_ICON = "data:image/svg+xml;charset=UTF-8," + encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64"><path d="M32 2 L37 22 L58 32 L58 38 L38 35 L35 61 L29 61 L26 35 L6 38 L6 32 L27 22 Z" fill="#ffd166" stroke="#07131d" stroke-width="3" stroke-linejoin="round"/><path d="M26 27 L12 17 L10 22 L25 34 Z M38 27 L52 17 L54 22 L39 34 Z" fill="#ffd166" stroke="#07131d" stroke-width="2"/></svg>`);
const ROTOR_ICON = "data:image/svg+xml;charset=UTF-8," + encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64"><circle cx="32" cy="34" r="12" fill="#75d6ff" stroke="#07131d" stroke-width="3"/><path d="M8 18 Q32 10 56 18 M8 50 Q32 58 56 50 M32 5 L32 59" fill="none" stroke="#75d6ff" stroke-width="4"/></svg>`);
const SATELLITE_ICON = "data:image/svg+xml;charset=UTF-8," + encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 48 48"><path d="M24 4 L44 24 L24 44 L4 24 Z" fill="#c084fc" stroke="#120b1c" stroke-width="3"/><circle cx="24" cy="24" r="5" fill="#fff"/></svg>`);
const AIRCRAFT_REFRESH_MS = 10000;
const SATELLITE_REFRESH_MS = 300000;
let requestSeq = 0;
let lastFeatures: any[] = [];
let runtimeReady = false;

function escapeHtml(value: unknown): string {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;",
  }[char] || char));
}

function setStatus(label: string, mode: "ready" | "warn" | "error" | "loading"): void {
  statusEl.textContent = label;
  statusDot.className = mode;
}

function setMetric(el: HTMLElement, value: string | number): void {
  el.textContent = String(value);
}

function formatTime(value: unknown): string {
  if (!value) return "—";
  const date = new Date(String(value));
  return Number.isNaN(date.valueOf()) ? String(value) : date.toISOString().replace(".000Z", "Z");
}

function confidenceLabel(value: unknown): string {
  if (typeof value !== "number") return "—";
  return `${Math.round(value * 100)}%`;
}

const viewer = new Viewer("globe", {
  animation: false,
  timeline: false,
  baseLayerPicker: false,
  geocoder: false,
  homeButton: false,
  navigationHelpButton: false,
  sceneModePicker: false,
  fullscreenButton: false,
  terrainProvider: new EllipsoidTerrainProvider(),
  selectionIndicator: false,
  infoBox: false,
});
viewer.imageryLayers.removeAll();
viewer.imageryLayers.addImageryProvider(new OpenStreetMapImageryProvider({
  url: "https://tile.openstreetmap.org/",
}));
viewer.camera.setView({ destination: Cartesian3.fromDegrees(78, 23, 9000000) });

function updateAircraftPresentation(): void {
  const labelsEnabled = ($("#layer-labels") as HTMLInputElement).checked;
  const height = viewer.camera.positionCartographic?.height ?? Number.POSITIVE_INFINITY;
  const closeEnoughForLabels = height <= AIRCRAFT_LABEL_ZOOM_METERS;
  aircraftEntities.forEach((entity) => {
    if (entity.label) {
      const tracked = viewer.trackedEntity === entity;
      entity.label.show = new ConstantProperty(labelsEnabled && (tracked || closeEnoughForLabels));
    }
  });
}

function updateSatellitePresentation(): void {
  const labelsEnabled = ($("#layer-labels") as HTMLInputElement).checked;
  satelliteEntities.forEach((entity) => {
    if (entity.label) entity.label.show = new ConstantProperty(labelsEnabled);
  });
}

function setLayerVisibility(): void {
  const entities = dataSources.get("analyst");
  if (entities) {
    entities.show = ($("#layer-entities") as HTMLInputElement).checked;
  }
  const labels = ($("#layer-labels") as HTMLInputElement).checked;
  if (entities) {
    entities.entities.values.forEach((entity: Entity) => {
      if (entity.label) entity.label.show = new ConstantProperty(labels);
    });
  }
  updateAircraftPresentation();
  updateSatellitePresentation();
}
function removeAircraftEntities(): void {
  for (const entity of aircraftEntities.values()) viewer.entities.remove(entity);
  aircraftEntities.clear();
  aircraftSamples.clear();
  aircraftPredictionTimes.clear();
  aircraftLastSeen.clear();
}

function removeSatelliteEntities(): void {
  for (const entity of satelliteEntities.values()) viewer.entities.remove(entity);
  satelliteEntities.clear();
}

function aircraftIcon(category: number | null): string {
  if (category === 8) return ROTOR_ICON;
  if (category !== null && category >= 4 && category <= 7) return JET_ICON;
  return AIRCRAFT_ICON;
}

function predictPosition(lon: number, lat: number, altitude: number, speedMps: number | null, headingDeg: number | null, seconds: number): Cartesian3 {
  if (!speedMps || headingDeg == null || speedMps <= 0) return Cartesian3.fromDegrees(lon, lat, altitude);
  const distance = speedMps * seconds;
  const heading = headingDeg * Math.PI / 180;
  const radius = 6371000;
  const dLat = (distance * Math.cos(heading)) / radius;
  const dLon = (distance * Math.sin(heading)) / (radius * Math.max(Math.cos(lat * Math.PI / 180), 0.05));
  return Cartesian3.fromDegrees(lon + dLon * 180 / Math.PI, lat + dLat * 180 / Math.PI, altitude);
}

function aircraftLabel(props: any, icao: string): string {
  const callsign = String(props.callsign || "").trim() || icao;
  const altitude = Number(props.altitude_m);
  const speed = Number(props.velocity_mps);
  const altitudeFt = Number.isFinite(altitude) ? Math.round(altitude * 3.28084 / 100) * 100 : null;
  const speedKt = Number.isFinite(speed) ? Math.round(speed * 1.94384) : null;
  return [
    callsign,
    altitudeFt == null ? "ALT —" : `ALT ${altitudeFt.toLocaleString()} FT`,
    speedKt == null ? "SPD —" : `SPD ${speedKt} KT`,
  ].join("\\n");
}

function updateAircraftSamples(
  entity: Entity,
  icao: string,
  sampleTime: JulianDate,
  position: Cartesian3,
  futureTime: JulianDate,
  futurePosition: Cartesian3,
): void {
  const property = entity.position as SampledPositionProperty;
  property.forwardExtrapolationType = ExtrapolationType.EXTRAPOLATE;
  property.forwardExtrapolationDuration = AIRCRAFT_STALE_SECONDS;
  const times = aircraftSamples.get(icao) || [];
  const lastTime = times[times.length - 1];
  const sampleOrder = lastTime ? JulianDate.compare(sampleTime, lastTime) : 1;

  // Provider caches can repeat timestamps. Ignore out-of-order observations,
  // and replace equal-time samples instead of inserting duplicate timestamps
  // into Cesium's sampled property (which can break interpolation and trails).
  if (sampleOrder < 0) return;

  const previousPrediction = aircraftPredictionTimes.get(icao);
  if (previousPrediction) property.removeSample(previousPrediction);

  if (sampleOrder === 0) {
    property.removeSample(sampleTime);
    property.addSample(sampleTime, position);
  } else {
    property.addSample(sampleTime, position);
    times.push(sampleTime);
  }

  property.addSample(futureTime, futurePosition);
  aircraftPredictionTimes.set(icao, futureTime);

  while (times.length > 18) {
    property.removeSample(times.shift()!);
  }
  aircraftSamples.set(icao, times);
}

async function refreshAircraft(): Promise<void> {
  const data = await requestJson("/v1/live/aircraft?bbox=" + encodeURIComponent(cameraBbox()) + "&provider=opensky");
  const observed = new Date(data.observed_at || Date.now());
  const sampleTime = JulianDate.fromDate(observed);
  const seen = new Set<string>();

  if (!liveClockInitialized) {
    viewer.clock.currentTime = JulianDate.fromDate(new Date());
    viewer.clock.multiplier = 1;
    viewer.clock.clockRange = ClockRange.UNBOUNDED;
    viewer.clock.shouldAnimate = true;
    liveClockInitialized = true;
  }

  for (const feature of data.features || []) {
    const props = feature.properties || {};
    const icao = String(props.icao24 || "");
    const coords = feature.geometry?.coordinates || [];
    if (!icao || coords.length < 2) continue;

    const lon = Number(coords[0]);
    const lat = Number(coords[1]);
    const altitude = Number(coords[2] || 0);
    if (![lon, lat, altitude].every(Number.isFinite)) continue;

    seen.add(icao);
    aircraftLastSeen.set(icao, Date.now());
    const position = Cartesian3.fromDegrees(lon, lat, altitude);
    const category = props.category == null ? null : Number(props.category);
    const heading = props.heading_deg == null ? null : Number(props.heading_deg);
    const speed = props.velocity_mps == null ? null : Number(props.velocity_mps);
    const futureTime = JulianDate.addSeconds(sampleTime, AIRCRAFT_REFRESH_MS / 1000, new JulianDate());
    const futurePosition = predictPosition(lon, lat, altitude, speed, heading, AIRCRAFT_REFRESH_MS / 1000);
    const existing = aircraftEntities.get(icao);

    if (existing) {
      updateAircraftSamples(existing, icao, sampleTime, position, futureTime, futurePosition);
      if (existing.billboard) {
        existing.billboard.image = new ConstantProperty(aircraftIcon(category));
        existing.billboard.rotation = new ConstantProperty((heading || 0) * Math.PI / 180);
      }
      if (existing.label) existing.label.text = new ConstantProperty(aircraftLabel(props, icao));
      existing.name = props.callsign?.trim() || icao;
      if (existing.properties) {
        existing.properties.callsign = new ConstantProperty(props.callsign || "");
        existing.properties.altitude_m = new ConstantProperty(altitude);
        existing.properties.velocity_mps = new ConstantProperty(speed);
        existing.properties.heading_deg = new ConstantProperty(heading);
      }
      continue;
    }

    const positionProperty = new SampledPositionProperty();
    positionProperty.forwardExtrapolationType = ExtrapolationType.EXTRAPOLATE;
    positionProperty.forwardExtrapolationDuration = AIRCRAFT_STALE_SECONDS;
    positionProperty.addSample(sampleTime, position);
    positionProperty.addSample(futureTime, futurePosition);
    aircraftSamples.set(icao, [sampleTime]);
    aircraftPredictionTimes.set(icao, futureTime);
    aircraftLastSeen.set(icao, Date.now());

    const entity = viewer.entities.add({
      id: `aircraft-${icao}`,
      name: props.callsign?.trim() || icao,
      position: positionProperty,
      billboard: new BillboardGraphics({
        image: aircraftIcon(category),
        width: 34,
        height: 34,
        rotation: (heading || 0) * Math.PI / 180,
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
        alignedAxis: Cartesian3.ZERO,
        pixelOffset: new Cartesian2(0, 0),
      }),
      label: {
        text: aircraftLabel(props, icao),
        font: "11px monospace",
        style: LabelStyle.FILL_AND_OUTLINE,
        show: false,
        disableDepthTestDistance: Number.POSITIVE_INFINITY,
        distanceDisplayCondition: new DistanceDisplayCondition(0, AIRCRAFT_LABEL_ZOOM_METERS),
        showBackground: true,
        backgroundColor: Color.fromCssColorString("rgba(4,12,18,0.78)"),
        fillColor: Color.WHITE,
        outlineWidth: 2,
        pixelOffset: new Cartesian2(16, -8),
      },
      path: new PathGraphics({
        show: true,
        trailTime: AIRCRAFT_TRAIL_SECONDS,
        leadTime: AIRCRAFT_LEAD_SECONDS,
        width: 3,
        resolution: 5,
        material: Color.fromCssColorString("rgba(255,209,102,0.8)"),
      }),
      properties: new PropertyBag({
        entity_type: "aircraft",
        icao24: icao,
        callsign: props.callsign || "",
        category: category,
        source: props.source || "opensky",
        altitude_m: altitude,
        velocity_mps: speed,
        heading_deg: heading,
      }),
    });
    aircraftEntities.set(icao, entity);
  }

  const nowMs = Date.now();
  for (const [icao, entity] of aircraftEntities) {
    const ageSeconds = (nowMs - (aircraftLastSeen.get(icao) || 0)) / 1000;
    if (!seen.has(icao) && ageSeconds > AIRCRAFT_STALE_SECONDS) {
      entity.show = false;
    } else {
      entity.show = true;
    }
    if (ageSeconds > AIRCRAFT_STALE_SECONDS * 2) {
      viewer.entities.remove(entity);
      aircraftEntities.delete(icao);
      aircraftSamples.delete(icao);
      aircraftPredictionTimes.delete(icao);
      aircraftLastSeen.delete(icao);
    }
  }

  updateAircraftPresentation();
  viewer.clock.shouldAnimate = true;
  setMetric(featureCount, data.count || 0);
  setStatus(`AIRCRAFT LIVE • ${data.count || 0}`, "ready");
}

async function refreshSatellites(): Promise<void> {
  const payload = await requestJson("/v1/live/satellites?group=active&limit=1000");
  removeSatelliteEntities();

  const now = new Date();
  const start = new Date(now.getTime() - 30 * 60 * 1000);
  const stop = new Date(now.getTime() + SATELLITE_ORBIT_SECONDS * 1000);
  const labelsOn = ($("#layer-labels") as HTMLInputElement).checked;
  const seen = new Set<string>();

  viewer.clock.startTime = JulianDate.fromDate(start);
  viewer.clock.stopTime = JulianDate.fromDate(stop);
  if (!liveClockInitialized) {
    viewer.clock.currentTime = JulianDate.fromDate(now);
    viewer.clock.multiplier = 1;
    viewer.clock.shouldAnimate = true;
    liveClockInitialized = true;
  } else {
    viewer.clock.clockRange = ClockRange.UNBOUNDED;
    viewer.clock.shouldAnimate = true;
  }

  for (const row of payload.objects || []) {
    try {
      const name = String(row.OBJECT_NAME || row.object_name || "SATELLITE");
      const norad = String(row.NORAD_CAT_ID || row.OBJECT_ID || name);
      const satrec: any = row.TLE_LINE1 && row.TLE_LINE2
        ? satellite.twoline2satrec(row.TLE_LINE1, row.TLE_LINE2)
        : satellite.json2satrec(row);
      const positionProperty = new SampledPositionProperty();
      let samples = 0;

      for (let offset = -1800; offset <= SATELLITE_ORBIT_SECONDS; offset += SATELLITE_SAMPLE_SECONDS) {
        const sampleDate = new Date(now.getTime() + offset * 1000);
        const state = satellite.propagate(satrec, sampleDate);
        if (!state?.position) continue;
        const geo = satellite.eciToGeodetic(state.position, satellite.gstime(sampleDate));
        const lon = satellite.degreesLong(geo.longitude);
        const lat = satellite.degreesLat(geo.latitude);
        const heightKm = geo.height;
        if (![lon, lat, heightKm].every(Number.isFinite)) continue;
        positionProperty.addSample(
          JulianDate.fromDate(sampleDate),
          Cartesian3.fromDegrees(lon, lat, heightKm * 1000)
        );
        samples += 1;
      }

      if (samples < 2) continue;
      seen.add(norad);
      const entity = viewer.entities.add({
        id: `satellite-${norad}`,
        name,
        position: positionProperty,
        billboard: new BillboardGraphics({
          image: SATELLITE_ICON,
          width: 18,
          height: 18,
          scale: 0.9,
        }),
        label: {
          text: name,
          font: "10px monospace",
          show: labelsOn,
          showBackground: true,
          backgroundColor: Color.fromCssColorString("rgba(12,6,20,0.78)"),
          fillColor: Color.fromCssColorString("#e9d5ff"),
          pixelOffset: new Cartesian2(10, -6),
        },
        path: new PathGraphics({
          show: true,
          trailTime: 45 * 60,
          leadTime: SATELLITE_ORBIT_SECONDS,
          width: 1,
          resolution: SATELLITE_SAMPLE_SECONDS,
          material: Color.fromCssColorString("rgba(192,132,252,0.55)"),
        }),
        properties: new PropertyBag({
          entity_type: "satellite",
          source: "celestrak",
          name,
          norad,
          orbit_window_seconds: SATELLITE_ORBIT_SECONDS,
          sample_interval_seconds: SATELLITE_SAMPLE_SECONDS,
        }),
      });
      satelliteEntities.set(norad, entity);
    } catch {
      continue;
    }
  }

  setStatus(`SATELLITES LIVE • ${satelliteEntities.size}`, "ready");
}

function removeLiveLayer(name: string): void {
  const ds = liveSources.get(name);
  if (ds) viewer.dataSources.remove(ds, true);
  liveSources.delete(name);
}

async function addLiveGeoJson(name: string, url: string, labelField?: string): Promise<void> {
  const data = await requestJson(url);
  removeLiveLayer(name);
  const ds = await GeoJsonDataSource.load(data, { clampToGround: false });
  ds.name = name;
  ds.entities.values.forEach((entity: Entity) => {
    if (entity.point) {
      entity.point.color = new ConstantProperty(Color.fromCssColorString("#ffbf69"));
      entity.point.pixelSize = new ConstantProperty(7);
      entity.point.outlineColor = new ConstantProperty(Color.fromCssColorString("#0b141b"));
      entity.point.outlineWidth = new ConstantProperty(2);
    }
    if (entity.label) entity.label.show = new ConstantProperty(false);
    if (labelField && entity.properties) {
      const value = entity.properties[labelField]?.getValue?.();
      if (value) entity.name = String(value);
    }
  });
  liveSources.set(name, ds);
  await viewer.dataSources.add(ds);
}

async function refreshEarthquakes(): Promise<void> {
  await addLiveGeoJson("earthquakes", "/v1/live/earthquakes?feed=all_day", "title");
}

async function refreshFires(): Promise<void> {
  await addLiveGeoJson("fires", "/v1/live/fires?bbox=" + encodeURIComponent(cameraBbox()) + "&days=1");
}

async function refreshWeather(): Promise<void> {
  const card = $("#weather-card");
  const content = $("#weather-content");
  const updated = $("#weather-updated");
  card.classList.remove("hidden");
  content.textContent = "Loading current conditions…";
  const canvas = viewer.scene.canvas;
  const target = viewer.camera.pickEllipsoid(
    new Cartesian2(canvas.clientWidth / 2, canvas.clientHeight / 2),
    viewer.scene.globe.ellipsoid,
  );
  const location = target
    ? Cartographic.fromCartesian(target, viewer.scene.globe.ellipsoid)
    : viewer.camera.positionCartographic;
  if (!location) throw new Error("Unable to determine the current map location");
  const lat = location.latitude * 180 / Math.PI;
  const lon = location.longitude * 180 / Math.PI;
  try {
    const payload = await requestJson(`/v1/live/weather?lat=${encodeURIComponent(lat.toFixed(4))}&lon=${encodeURIComponent(lon.toFixed(4))}`);
    const current = payload.data?.current;
    if (!current) throw new Error("Weather provider returned no current conditions");
    const units = payload.data.current_units || {};
    const fields: Array<[string, string]> = [
      ["TEMPERATURE", `${current.temperature_2m ?? "—"} ${units.temperature_2m ?? "°C"}`],
      ["FEELS LIKE", `${current.apparent_temperature ?? "—"} ${units.apparent_temperature ?? "°C"}`],
      ["WIND", `${current.wind_speed_10m ?? "—"} ${units.wind_speed_10m ?? "km/h"}`],
      ["HUMIDITY", `${current.relative_humidity_2m ?? "—"}${units.relative_humidity_2m ?? "%"}`],
      ["PRECIPITATION", `${current.precipitation ?? "—"} ${units.precipitation ?? "mm"}`],
    ];
    content.innerHTML = fields.map(([label, value]) =>
      `<div><small>${escapeHtml(label)}</small><strong>${escapeHtml(value)}</strong></div>`
    ).join("");
    updated.textContent = `Map centre ${lat.toFixed(2)}, ${lon.toFixed(2)} • Retrieved ${formatTime(payload.retrieved_at)} • Source: Open-Meteo`;
  } catch (error) {
    content.textContent = "Weather unavailable for this view.";
    updated.textContent = error instanceof Error ? error.message : String(error);
    throw error;
  }
}

async function refreshShips(): Promise<void> {
  const payload = await requestJson("/v1/live/ships");
  const features = (payload.ships || []).map((ship: any) => ({
    type: "Feature",
    geometry: { type: "Point", coordinates: [ship.longitude, ship.latitude] },
    properties: ship,
  }));
  removeLiveLayer("ships");
  const ds = await GeoJsonDataSource.load({ type: "FeatureCollection", features }, { clampToGround: false });
  ds.name = "ships";
  ds.entities.values.forEach((entity: Entity) => {
    if (entity.point) {
      entity.point.color = new ConstantProperty(Color.fromCssColorString("#55b7ff"));
      entity.point.pixelSize = new ConstantProperty(6);
    }
  });
  liveSources.set("ships", ds);
  await viewer.dataSources.add(ds);
}

async function refreshLiveLayers(): Promise<void> {
  const aircraftOn = ($("#layer-aircraft") as HTMLInputElement).checked;
  const satellitesOn = ($("#layer-satellites") as HTMLInputElement).checked;
  const earthquakesOn = ($("#layer-earthquakes") as HTMLInputElement).checked;
  const firesOn = ($("#layer-fires") as HTMLInputElement).checked;
  const shipsOn = ($("#layer-ships") as HTMLInputElement).checked;
  const weatherOn = ($("#layer-weather") as HTMLInputElement).checked;

  // One provider outage must not prevent unrelated live layers from refreshing.
  const jobs: Array<{ name: string; run: () => Promise<void> }> = [];
  if (aircraftOn) jobs.push({ name: "AIRCRAFT", run: refreshAircraft });
  else removeAircraftEntities();
  if (satellitesOn) jobs.push({ name: "SATELLITES", run: refreshSatellites });
  else removeSatelliteEntities();
  if (earthquakesOn) jobs.push({ name: "EARTHQUAKES", run: refreshEarthquakes });
  else removeLiveLayer("earthquakes");
  if (firesOn) jobs.push({ name: "FIRES", run: refreshFires });
  else removeLiveLayer("fires");
  if (shipsOn) jobs.push({ name: "SHIPS", run: refreshShips });
  else removeLiveLayer("ships");
  if (weatherOn) jobs.push({ name: "WEATHER", run: refreshWeather });
  else $("#weather-card").classList.add("hidden");

  const results = await Promise.all(jobs.map(async (job) => {
    try {
      await job.run();
      return { name: job.name, ok: true };
    } catch (error) {
      console.warn(`Live layer ${job.name} failed`, error);
      return { name: job.name, ok: false };
    }
  }));
  const failed = results.filter((result) => !result.ok).map((result) => result.name);
  if (failed.length) {
    setStatus(`LIVE DEGRADED • ${failed.join(", ")}`, "warn");
  } else if (jobs.length) {
    setStatus("LIVE WORLD FEEDS", "ready");
  }
}

function cameraBbox(): string {
  const rect = viewer.camera.computeViewRectangle(viewer.scene.globe.ellipsoid);
  if (!rect) return "";
  const deg = (x: number) => x * 180 / Math.PI;
  const west = deg(rect.west);
  const east = deg(rect.east);
  const south = deg(rect.south);
  const north = deg(rect.north);
  return [Math.max(-180, west), Math.max(-90, south), Math.min(180, east), Math.min(90, north)].join(",");
}

async function requestJson(path: string): Promise<any> {
  const response = await fetch(apiUrl(path), {
    headers: { Accept: "application/json" },
    cache: "no-store",
  });
  const raw = await response.text();
  let payload: any = {};
  try { payload = raw ? JSON.parse(raw) : {}; } catch { payload = { detail: raw.slice(0, 200) }; }
  if (!response.ok) throw new Error(payload.detail || `HTTP ${response.status}`);
  return payload;
}

async function checkHealth(): Promise<boolean> {
  try {
    const health = await requestJson("/health");
    runtimeReady = health.status === "ok" && health.ready !== false;
    if (runtimeReady) {
      setStatus("ANALYST READY", "ready");
      emptyEl.classList.add("hidden");
      return true;
    }
    setStatus("ANALYST DEGRADED", "warn");
    emptyEl.classList.remove("hidden");
    emptyEl.querySelector("h1")!.textContent = "Runtime dependency not ready";
    emptyEl.querySelector("p")!.textContent = "The process is reachable, but authoritative analyst dependencies are unavailable. No synthetic intelligence is displayed.";
    return false;
  } catch (error) {
    runtimeReady = false;
    setStatus("ANALYST UNREACHABLE", "error");
    emptyEl.classList.remove("hidden");
    emptyEl.querySelector("h1")!.textContent = "Analyst API unreachable";
    emptyEl.querySelector("p")!.textContent = escapeHtml(error instanceof Error ? error.message : error);
    return false;
  }
}

function styleFeatures(data: any): void {
  const sourceNames = new Set<string>();
  const evidenceIds = new Set<string>();
  let confidenceSum = 0;
  let confidenceN = 0;
  for (const feature of data.features || []) {
    const props = feature.properties || {};
    if (props.source) sourceNames.add(String(props.source));
    if (props.observation_id) evidenceIds.add(String(props.observation_id));
    if (typeof props.confidence === "number") {
      confidenceSum += props.confidence;
      confidenceN += 1;
    }
  }
  setMetric(featureCount, data.count ?? data.features?.length ?? 0);
  setMetric(sourceCount, sourceNames.size || "—");
  setMetric(evidenceCount, evidenceIds.size || "—");
  setMetric(confidenceEl, confidenceN ? confidenceLabel(confidenceSum / confidenceN) : "—");
}

async function refreshMap(): Promise<void> {
  const id = ++requestSeq;
  if (!runtimeReady && !(await checkHealth())) return;
  const bbox = cameraBbox();
  if (!bbox) return;
  try {
    const analysisAt = analysisTimeInput.value ? new Date(`${analysisTimeInput.value}:00Z`).toISOString() : new Date().toISOString();
    const data = await requestJson(`/v1/analyst/spatial?bbox=${encodeURIComponent(bbox)}&at=${encodeURIComponent(analysisAt)}&limit=1000`);
    if (id !== requestSeq) return;
    lastFeatures = data.features || [];
    const old = dataSources.get("analyst");
    if (old) viewer.dataSources.remove(old, true);
    const ds = await GeoJsonDataSource.load(data, { clampToGround: false });
    ds.name = "analyst";
    ds.entities.values.forEach((entity: Entity) => {
      if (entity.point) {
        entity.point.color = new ConstantProperty(Color.fromCssColorString("#48d6b0"));
        entity.point.pixelSize = new ConstantProperty(7);
        entity.point.outlineColor = new ConstantProperty(Color.fromCssColorString("#0b141b"));
        entity.point.outlineWidth = new ConstantProperty(2);
      }
      if (entity.label) entity.label.show = new ConstantProperty(true);
    });
    dataSources.set("analyst", ds);
    await viewer.dataSources.add(ds);
    styleFeatures(data);
    emptyEl.classList.toggle("hidden", (data.count ?? 0) > 0);
    if (!data.count) {
      emptyEl.querySelector("h1")!.textContent = "No features in current view";
      emptyEl.querySelector("p")!.textContent = "The world-state query returned no authoritative features for this viewport and time.";
    }
    setStatus(`${data.count ?? 0} FEATURES • READY`, "ready");
    $("#last-refresh").textContent = `REFRESHED ${new Date().toISOString().replace(".000Z", "Z")}`;
  } catch (error) {
    setStatus("ANALYST QUERY FAILED", "error");
    emptyEl.classList.remove("hidden");
    emptyEl.classList.add("error-state");
    emptyEl.querySelector("h1")!.textContent = "Intelligence query failed";
    emptyEl.querySelector("p")!.textContent = escapeHtml(error instanceof Error ? error.message : error);
  }
}

function showState(state: any): void {
  $("#inspector-title").textContent = state.entity_id || "Selected entity";
  $("#record-state").textContent = state.entity_type || "ENTITY";
  $("#world-state").textContent = state.state_id || "—";
  $("#observed-at").textContent = formatTime(state.observed_at);
  $("#valid-from").textContent = formatTime(state.valid_from);
  $("#entity-confidence").textContent = confidenceLabel(state.confidence);
  $("#properties").textContent = JSON.stringify(state.properties || {}, null, 2);
  const refs = Array.isArray(state.evidence_refs) ? state.evidence_refs : [];
  $("#evidence-list").innerHTML = refs.length
    ? refs.map((ref: string) => `<div class="evidence-item"><span class="evidence-dot"></span><code>${escapeHtml(ref)}</code></div>`).join("")
    : '<span class="muted">No evidence references attached to this state.</span>';
}

async function inspectEntity(entityId = entityInput.value.trim()): Promise<void> {
  if (!entityId) {
    resultsEl.innerHTML = '<span class="muted">Enter an entity ID to inspect authoritative state.</span>';
    return;
  }
  try {
    const data = await requestJson(`/v1/analyst/snapshot?entity_ids=${encodeURIComponent(entityId)}&at=${encodeURIComponent(new Date().toISOString())}`);
    if (!data.states?.length) {
      $("#record-state").textContent = "NOT FOUND";
      $("#inspector-title").textContent = entityId;
      resultsEl.innerHTML = '<span class="muted">No authoritative state exists for this entity at the requested time.</span>';
      return;
    }
    showState(data.states[0]);
    const summary = data.evidence || {};
    setMetric(sourceCount, summary.sources?.length || "—");
    setMetric(evidenceCount, summary.refs?.length || "—");
    setMetric(confidenceEl, confidenceLabel(data.states[0].confidence));
  } catch (error) {
    resultsEl.innerHTML = `<span class="error-text">${escapeHtml(error instanceof Error ? error.message : error)}</span>`;
  }
}

async function loadTimeline(days: number): Promise<void> {
  const entityId = entityInput.value.trim();
  if (!entityId) {
    resultsEl.innerHTML = '<span class="muted">Enter an entity ID first.</span>';
    return;
  }
  const end = new Date();
  const start = new Date(end.getTime() - days * 86400000);
  try {
    const data = await requestJson(`/v1/analyst/timeline/${encodeURIComponent(entityId)}?start=${encodeURIComponent(start.toISOString())}&end=${encodeURIComponent(end.toISOString())}`);
    const changes = data.changes || [];
    resultsEl.innerHTML = changes.length
      ? changes.map((change: any) => `
        <article class="timeline-item">
          <div class="timeline-date">${escapeHtml(formatTime(change.valid_from))}</div>
          <strong>${escapeHtml(change.from_state_id || "initial")} → ${escapeHtml(change.to_state_id)}</strong>
          <span>${escapeHtml((change.changed_properties || []).join(" • ") || "state transition")}</span>
          <code>${escapeHtml((change.evidence_refs || []).join(", ") || "no evidence refs")}</code>
        </article>`).join("")
      : '<span class="muted">No state transitions in the requested window.</span>';
  } catch (error) {
    resultsEl.innerHTML = `<span class="error-text">${escapeHtml(error instanceof Error ? error.message : error)}</span>`;
  }
}

function selectEntityFromGlobe(entity: Entity | undefined): void {
  if (!entity) return;
  const entityType = entity.properties?.entity_type?.getValue?.();
  if (entityType === "aircraft") {
    const props: any = {};
    for (const key of ["icao24", "callsign", "category", "source", "altitude_m", "velocity_mps", "heading_deg"]) {
      props[key] = entity.properties?.[key]?.getValue?.();
    }
    const tracked = viewer.trackedEntity === entity;
    if (tracked) {
      viewer.trackedEntity = undefined;
      $("#record-state").textContent = "AIRCRAFT";
      setStatus("TRACK RELEASED", "ready");
    } else {
      viewer.trackedEntity = entity;
      $("#record-state").textContent = "AIRCRAFT • TRACKING";
      setStatus(`TRACKING ${String(props.callsign || props.icao24 || "AIRCRAFT")}`, "ready");
    }
    $("#inspector-title").textContent = String(props.callsign || props.icao24 || "Aircraft");
    $("#world-state").textContent = "LIVE TELEMETRY";
    $("#observed-at").textContent = formatTime(new Date().toISOString());
    $("#valid-from").textContent = "LIVE / 10S POLL";
    $("#entity-confidence").textContent = "SOURCE: OPENSKY";
    $("#properties").textContent = JSON.stringify(props, null, 2);
    $("#evidence-list").innerHTML = '<span class="muted">Live telemetry • public OpenSky state vector • not authoritative for identity.</span>';
    return;
  }
  if (entityType === "satellite") {
    const props: any = {};
    for (const key of ["name", "norad", "source", "orbit_window_seconds", "sample_interval_seconds"]) {
      props[key] = entity.properties?.[key]?.getValue?.();
    }
    viewer.trackedEntity = entity;
    $("#record-state").textContent = "SATELLITE • TRACKING";
    $("#inspector-title").textContent = String(props.name || "Satellite");
    $("#world-state").textContent = "LIVE ORBIT";
    $("#observed-at").textContent = formatTime(new Date().toISOString());
    $("#valid-from").textContent = "TLE / SGP4";
    $("#entity-confidence").textContent = "DERIVED ORBIT";
    $("#properties").textContent = JSON.stringify(props, null, 2);
    $("#evidence-list").innerHTML = '<span class="muted">Orbit propagated client-side from CelesTrak orbital elements.</span>';
    return;
  }
  const props = entity.properties as any;
  const id = props?.entity_id?.getValue?.() || props?.entityId?.getValue?.() || entity.id;
  if (!id) return;
  entityInput.value = String(id);
  inspectEntity(String(id));
}

const handler = new ScreenSpaceEventHandler(viewer.scene.canvas);
handler.setInputAction((movement: any) => {
  const picked = viewer.scene.pick(movement.position);
  const entity = picked?.id as Entity | undefined;
  selectEntityFromGlobe(entity);
}, ScreenSpaceEventType.LEFT_CLICK);

function closeOperatorRails(): void {
  document.body.classList.remove("mobile-left-open", "mobile-right-open");
}

$("#mobile-left").addEventListener("click", () => {
  document.body.classList.toggle("mobile-left-open");
  document.body.classList.remove("mobile-right-open");
});
$("#mobile-right").addEventListener("click", () => {
  document.body.classList.toggle("mobile-right-open");
  document.body.classList.remove("mobile-left-open");
});

const touchCompact = navigator.maxTouchPoints > 0 && window.innerWidth < 1200;
if (touchCompact) document.body.classList.add("compact-operator");

$("#inspect").addEventListener("click", () => void inspectEntity());
entityInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") void inspectEntity();
});
$("#timeline").addEventListener("click", () => void loadTimeline(7));
$("#timeline-30").addEventListener("click", () => void loadTimeline(30));
$("#refresh").addEventListener("click", () => void refreshMap());
analysisTimeInput.addEventListener("change", () => void refreshMap());
$("#layer-entities").addEventListener("change", setLayerVisibility);
$("#layer-labels").addEventListener("change", () => {
  setLayerVisibility();
  updateAircraftPresentation();
  updateSatellitePresentation();
});
$("#layer-aircraft").addEventListener("change", () => void refreshLiveLayers());
$("#layer-satellites").addEventListener("change", () => void refreshLiveLayers());
$("#layer-earthquakes").addEventListener("change", () => void refreshLiveLayers());
$("#layer-fires").addEventListener("change", () => void refreshLiveLayers());
$("#layer-ships").addEventListener("change", () => void refreshLiveLayers());
$("#layer-weather").addEventListener("change", () => void refreshLiveLayers());
window.setInterval(() => {
  if (!runtimeReady) return;
  if (($("#layer-aircraft") as HTMLInputElement).checked) void refreshAircraft();
  if (($("#layer-satellites") as HTMLInputElement).checked && !viewer.clock.shouldAnimate) {
    viewer.clock.shouldAnimate = true;
  }
}, AIRCRAFT_REFRESH_MS);
window.setInterval(() => {
  if (runtimeReady && ($("#layer-satellites") as HTMLInputElement).checked) void refreshSatellites();
}, SATELLITE_REFRESH_MS);
// Weather toggle is handled by refreshLiveLayers(), which queries the current map centre.
$("#flir-toggle").addEventListener("click", () => document.querySelector(".map-stage")?.classList.toggle("flir-mode"));
$("#google-3d").addEventListener("click", async () => {
  const key = (import.meta.env.VITE_GOOGLE_MAPS_API_KEY || "").trim();
  if (!key) { setStatus("GOOGLE 3D KEY NOT CONFIGURED", "warn"); return; }
  try {
    (viewer as any).scene.globe.show = false;
    const tileset = await createGooglePhotorealistic3DTileset({ key, onlyUsingWithGoogleGeocoder: true });
    viewer.scene.primitives.add(tileset);
    setStatus("GOOGLE PHOTOREALISTIC 3D", "ready");
  } catch (error) {
    setStatus("GOOGLE 3D FAILED", "error");
    console.warn(error);
  }
});
document.querySelectorAll<HTMLButtonElement>("[data-module]").forEach((button) => {
  button.addEventListener("click", () => {
    const labels: Record<string, string> = {
      geolens: "GEOLENS • SPATIAL CATALOG",
      "world-monitor": "WORLD MONITOR • GLOBAL CONTEXT",
      "iron-sight": "IRON SIGHT • CONFLICT MONITOR",
      pythia: "PYTHIA • FORECAST WORKSPACE",
      wanderer: "WANDERER • TRAIL WORKSPACE",
      "open-meteo": "OPEN-METEO • WEATHER CONTEXT",
    };
    $("#mission-name").textContent = labels[button.dataset.module || ""] || "GLOBAL SITUATIONAL AWARENESS";
  });
});

$("#global-view").addEventListener("click", () => {
  viewer.camera.flyTo({ destination: Cartesian3.fromDegrees(78, 23, 9000000), duration: 0.8 });
});
$("#india-view").addEventListener("click", () => {
  viewer.camera.flyTo({ destination: Cartesian3.fromDegrees(78.96, 20.59, 2600000), duration: 0.8 });
});
$("#reset-view").addEventListener("click", () => viewer.camera.setView({ destination: Cartesian3.fromDegrees(78, 23, 9000000) }));

let cameraTimer: number | undefined;
viewer.camera.changed.addEventListener(() => {
  updateAircraftPresentation();
  window.clearTimeout(cameraTimer);
  cameraTimer = window.setTimeout(() => {
    // Keep every viewport-bound feed in sync after pan/zoom. Without this,
    // aircraft remain queried against the previous bounding box and appear
    // to disappear when the operator moves the globe.
    void refreshMap();
    if (runtimeReady) void refreshLiveLayers();
  }, 650);
});

window.addEventListener("keydown", (event) => {
  if (event.key === "/" && document.activeElement !== entityInput) {
    event.preventDefault();
    entityInput.focus();
  }
});

analysisTimeInput.value = new Date().toISOString().slice(0, 16);
void checkHealth().then((ready) => {
  if (ready) {
    void refreshMap();
    void refreshLiveLayers();
  }
});

// Recover automatically if the API starts late or becomes temporarily unavailable.
let healthRecoveryInFlight = false;
window.setInterval(async () => {
  if (runtimeReady || healthRecoveryInFlight) return;
  healthRecoveryInFlight = true;
  try {
    const ready = await checkHealth();
    if (ready) {
      void refreshMap();
      void refreshLiveLayers();
    }
  } finally {
    healthRecoveryInFlight = false;
  }
}, 15000);
