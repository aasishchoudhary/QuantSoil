import {
  Viewer,
  Cartesian3,
  Color,
  ConstantProperty,
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

app.innerHTML = `
<div class="app-shell">
  <header class="topbar">
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
        <label class="toggle"><input id="layer-aircraft" type="checkbox"/><span></span><em>AIRCRAFT / OPENSKY</em></label>
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
      <div class="scale"><span>WGS84</span><span>GEOINT VIEW</span></div>
    </section>

    <aside class="right-panel">
      <section class="inspector-head">
        <div><span class="eyebrow">ANALYST</span><h2 id="inspector-title">Situation overview</h2></div>
        <span id="record-state" class="state-badge">NO SELECTION</span>
      </section>

      <section id="inspector" class="inspector-body">
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

async function refreshAircraft(): Promise<void> {
  await addLiveGeoJson("aircraft", "/v1/live/aircraft?bbox=" + encodeURIComponent(cameraBbox()), "callsign");
}

async function refreshEarthquakes(): Promise<void> {
  await addLiveGeoJson("earthquakes", "/v1/live/earthquakes?feed=all_day", "title");
}

async function refreshFires(): Promise<void> {
  await addLiveGeoJson("fires", "/v1/live/fires?bbox=" + encodeURIComponent(cameraBbox()) + "&days=1");
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

async function refreshSatellites(): Promise<void> {
  const payload = await requestJson("/v1/live/satellites?group=active&limit=1000");
  removeLiveLayer("satellites");
  const now = new Date();
  const features: any[] = [];
  for (const row of payload.objects || []) {
    try {
      const name = String(row.OBJECT_NAME || row.object_name || "SATELLITE");
      const satrec: any = row.TLE_LINE1 && row.TLE_LINE2
        ? satellite.twoline2satrec(row.TLE_LINE1, row.TLE_LINE2)
        : satellite.json2satrec(row);
      const state = satellite.propagate(satrec, now);
      if (!state?.position) continue;
      const geo = satellite.eciToGeodetic(state.position, satellite.gstime(now));
      const lon = satellite.degreesLong(geo.longitude);
      const lat = satellite.degreesLat(geo.latitude);
      const heightKm = geo.height;
      if (!Number.isFinite(lon) || !Number.isFinite(lat) || !Number.isFinite(heightKm)) continue;
      features.push({
        type: "Feature",
        geometry: { type: "Point", coordinates: [lon, lat, heightKm * 1000] },
        properties: { entity_type: "satellite", source: "celestrak", name, norad: row.NORAD_CAT_ID || row.OBJECT_ID || null },
      });
    } catch { }
  }
  const ds = await GeoJsonDataSource.load({ type: "FeatureCollection", features }, { clampToGround: false });
  ds.name = "satellites";
  ds.entities.values.forEach((entity: Entity) => {
    if (entity.point) {
      entity.point.color = new ConstantProperty(Color.fromCssColorString("#c084fc"));
      entity.point.pixelSize = new ConstantProperty(4);
    }
  });
  liveSources.set("satellites", ds);
  await viewer.dataSources.add(ds);
}

async function refreshLiveLayers(): Promise<void> {
  const aircraftOn = ($("#layer-aircraft") as HTMLInputElement).checked;
  const satellitesOn = ($("#layer-satellites") as HTMLInputElement).checked;
  const earthquakesOn = ($("#layer-earthquakes") as HTMLInputElement).checked;
  const firesOn = ($("#layer-fires") as HTMLInputElement).checked;
  const shipsOn = ($("#layer-ships") as HTMLInputElement).checked;
  try {
    if (aircraftOn) await refreshAircraft(); else removeLiveLayer("aircraft");
    if (satellitesOn) await refreshSatellites(); else removeLiveLayer("satellites");
    if (earthquakesOn) await refreshEarthquakes(); else removeLiveLayer("earthquakes");
    if (firesOn) await refreshFires(); else removeLiveLayer("fires");
    if (shipsOn) await refreshShips(); else removeLiveLayer("ships");
    if (aircraftOn || satellitesOn || earthquakesOn || firesOn || shipsOn) setStatus("LIVE WORLD FEEDS", "ready");
  } catch (error) {
    setStatus("LIVE FEED DEGRADED", "warn");
    console.warn(error);
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
  const response = await fetch(`${API}${path}`, {
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
    const data = await requestJson(`${API}/spatial?bbox=${encodeURIComponent(bbox)}&at=${encodeURIComponent(analysisAt)}&limit=1000`);
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
    const data = await requestJson(`/snapshot?entity_ids=${encodeURIComponent(entityId)}&at=${encodeURIComponent(new Date().toISOString())}`);
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
    const data = await requestJson(`/timeline/${encodeURIComponent(entityId)}?start=${encodeURIComponent(start.toISOString())}&end=${encodeURIComponent(end.toISOString())}`);
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

$("#inspect").addEventListener("click", () => void inspectEntity());
entityInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter") void inspectEntity();
});
$("#timeline").addEventListener("click", () => void loadTimeline(7));
$("#timeline-30").addEventListener("click", () => void loadTimeline(30));
$("#refresh").addEventListener("click", () => void refreshMap());
analysisTimeInput.addEventListener("change", () => void refreshMap());
$("#layer-entities").addEventListener("change", setLayerVisibility);
$("#layer-labels").addEventListener("change", setLayerVisibility);
$("#layer-aircraft").addEventListener("change", () => void refreshLiveLayers());
$("#layer-satellites").addEventListener("change", () => void refreshLiveLayers());
$("#layer-earthquakes").addEventListener("change", () => void refreshLiveLayers());
$("#layer-fires").addEventListener("change", () => void refreshLiveLayers());
$("#layer-ships").addEventListener("change", () => void refreshLiveLayers());
$("#layer-weather").addEventListener("change", async () => {
  if (!(($("#layer-weather") as HTMLInputElement).checked)) return;
  const data = await requestJson("/v1/live/weather?lat=23.3441&lon=85.3096");
  $("#inspector-title").textContent = "Open-Meteo weather";
  $("#properties").textContent = JSON.stringify(data.data?.current || data.data || {}, null, 2);
  setStatus("OPEN-METEO READY", "ready");
});
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
  window.clearTimeout(cameraTimer);
  cameraTimer = window.setTimeout(() => void refreshMap(), 650);
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
