import {
  Viewer, Cartesian2, Cartesian3, CallbackPositionProperty, GeoJsonDataSource, Color, ConstantProperty, ColorMaterialProperty,
  LabelStyle, Ion, createWorldTerrainAsync, createOsmBuildingsAsync, OpenStreetMapImageryProvider, WebMapTileServiceImageryProvider, EllipsoidTerrainProvider,
  ScreenSpaceEventHandler, ScreenSpaceEventType, VerticalOrigin
} from "cesium";
import "cesium/Build/Cesium/Widgets/widgets.css";
import "./style.css";

const API = import.meta.env.VITE_ANALYST_API_BASE || "/v1/analyst";
const app = document.querySelector<HTMLDivElement>("#app")!;
app.innerHTML = `
<div class="ops">
  <header class="topbar">
    <div class="brand"><div class="brand-mark">Q</div><div><b>QUANTSOIL</b><small>WORLD INTELLIGENCE PLATFORM</small></div></div>
    <div class="global-search"><span>⌕</span><input id="search" placeholder="Search locations, entities, events, coordinates, evidence…"/><button id="search-go" aria-label="Search">↵</button></div>
    <div class="top-center"><span class="pulse"></span><span id="connection">INITIALIZING SOURCES</span><span class="top-divider"></span><span id="clock">--:--:-- UTC</span></div>
    <div class="top-actions"><button id="refresh" title="Refresh source data">↻ <span>SYNC</span></button><button id="toggle-left" title="Toggle navigation" aria-label="Toggle navigation">☰</button><button id="home" title="Reset globe camera">⌂</button><button id="toggle-right" title="Toggle inspector">▤</button></div>
  </header>
  <div class="workspace">
    <aside class="left-panel">
      <div class="panel-head"><span>WORKSPACE NAVIGATION</span><span class="live-dot"></span></div>
      <div class="nav-group">
        <div class="nav-caption">INTELLIGENCE</div>
        <button class="nav-item selected" data-section="overview"><span>◈</span><b>Overview</b><small>Global situation</small></button>
        <button class="nav-item" data-section="globe"><span>◎</span><b>3D Globe</b><small>World view</small></button>
        <button class="nav-item" data-section="maps"><span>⌖</span><b>Maps & analysis</b><small>Layers and terrain</small></button>
        <button class="nav-item" data-section="investigations"><span>⌘</span><b>Investigations</b><small>AI-assisted workflow</small></button>
        <button class="nav-item" data-section="entities"><span>♧</span><b>Entities & events</b><small>Observation index</small></button>
        <button class="nav-item" data-section="evidence"><span>⬡</span><b>Evidence graph</b><small>Relationship analysis</small></button>
        <button class="nav-item" data-section="timeline"><span>⌁</span><b>Temporal analysis</b><small>Time and change</small></button>
        <button class="nav-item" data-section="reports"><span>▤</span><b>Reports</b><small>Auditable findings</small></button>
      </div>
      <div class="section-label">GEOINT LAYERS <span id="layer-count">06</span></div>
      <div class="layer-list">
        <label class="layer-row"><span class="layer-icon cyan">✈</span><span class="layer-copy"><b>Aircraft & flight data</b><small id="aircraft-status">Waiting for source</small></span><input type="checkbox" data-layer="aircraft" checked/><i></i></label>
        <label class="layer-row"><span class="layer-icon violet">◉</span><span class="layer-copy"><b>Satellite / orbital</b><small id="satellite-status">Provider not configured</small></span><input type="checkbox" data-layer="satellite" checked/><i></i></label>
        <label class="layer-row"><span class="layer-icon amber">⌁</span><span class="layer-copy"><b>Earth events</b><small id="events-status">Waiting for source</small></span><input type="checkbox" data-layer="event" checked/><i></i></label>
        <label class="layer-row"><span class="layer-icon green">◆</span><span class="layer-copy"><b>Maritime observations</b><small id="vessel-status">No AIS provider configured</small></span><input type="checkbox" data-layer="vessel" checked/><i></i></label>
        <label class="layer-row"><span class="layer-icon violet">▣</span><span class="layer-copy"><b>Authorized camera metadata</b><small id="camera-status">No source configured</small></span><input type="checkbox" data-layer="camera" checked/><i></i></label>
        <label class="layer-row"><span class="layer-icon green">⌖</span><span class="layer-copy"><b>Other spatial evidence</b><small id="other-status">Waiting for source</small></span><input type="checkbox" data-layer="other" checked/><i></i></label>
      </div>
      <div class="section-label">MAP CONTROLS</div>
      <div class="control-list"><button id="zoom-in"><span>＋</span> Zoom in</button><button id="zoom-out"><span>－</span> Zoom out</button><button id="camera-reset"><span>◎</span> Global view</button><button id="terrain-toggle"><span>△</span> 3D terrain</button></div>
      <div class="section-label">SOURCE HEALTH</div>
      <div id="source-health" class="health-card"><div><span class="health-dot idle"></span><b>Analyst API</b><span id="api-health" class="health-state">CHECKING</span></div><p>Source availability reflects actual API responses. Unconfigured feeds are never represented as live.</p><div class="health-foot"><span>LAST CHECK</span><span id="last-check">—</span></div></div>
      <div class="left-footer">EVIDENCE FIRST <span>•</span> PROVENANCE ALWAYS</div>
    </aside>
    <main class="main-stage">
      <section class="kpi-strip">
        <article class="kpi-card"><div class="kpi-icon cyan">⌖</div><div><small>SPATIAL FEATURES</small><b id="kpi-features">—</b><span id="kpi-features-note">Waiting for API</span></div><i>◌</i></article>
        <article class="kpi-card"><div class="kpi-icon green">⌁</div><div><small>EARTH EVENTS</small><b id="kpi-events">—</b><span>Public USGS source</span></div><i>⌁</i></article>
        <article class="kpi-card"><div class="kpi-icon violet">◉</div><div><small>ORBITAL OBJECTS</small><b id="kpi-orbital">—</b><span>Propagated positions</span></div><i>◌</i></article>
        <article class="kpi-card"><div class="kpi-icon amber">⌁</div><div><small>ACTIVE SOURCES</small><b id="kpi-sources">—</b><span id="kpi-sources-note">Availability pending</span></div><i>▤</i></article>
        <article class="kpi-card"><div class="kpi-icon cyan">⬡</div><div><small>DATA CONFIDENCE</small><b id="kpi-confidence">—</b><span>Not inferred from uptime</span></div><i>◇</i></article>
      </section>
      <section class="primary-row">
        <section class="map-card">
          <div class="card-heading"><div><span class="eyebrow">GLOBAL VIEW</span><h1>World Intelligence <em>•</em> Spatial Context</h1></div><div class="map-buttons"><button id="view-3d" class="active">3D GLOBE</button><button id="view-2d">2D MAP</button><button id="imagery-toggle">SATELLITE</button></div></div>
          <div class="map-canvas"><div id="globe"></div><div class="map-overlay-top"><span class="coord-chip"><span class="crosshair">⌖</span><span id="coordinates">LAT — / LON —</span></span><span class="map-mode-tag"><i></i> GEOSPATIAL ENGINE</span></div><div class="map-bottom-left"><span class="scale-line"></span><span id="altitude">GLOBAL VIEW</span><span class="map-sep">|</span><span id="feature-total">0 FEATURES</span></div><div class="map-bottom-right"><span class="legend-dot cyan-bg"></span> AIRCRAFT <span class="legend-dot amber-bg"></span> EVENTS <span class="legend-dot violet-bg"></span> ORBITAL <span class="legend-dot vessel-bg"></span> MARITIME</div><div id="map-message" class="map-message">Connecting to governed spatial API…</div></div>
          <div class="map-card-footer"><span><i class="status-square"></i> WGS84 COORDINATES</span><span>OBSERVATIONS · DERIVED DATA SEPARATED</span><span id="map-freshness">FRESHNESS UNKNOWN</span></div>
        </section>
        <div class="side-stack">
          <section class="dashboard-card events-card"><div class="card-heading compact"><div><span class="eyebrow">OBSERVATION STREAM</span><h2>Recent Events <span id="event-count" class="count-pill">0</span></h2></div><span class="live-tag"><i></i> SOURCE-DRIVEN</span></div><div id="recent-events" class="event-list"><div class="empty-card">Events will appear when a configured source returns observations.</div></div></section>
          <section class="dashboard-card insights-card"><div class="card-heading compact"><div><span class="eyebrow">ASSISTED ANALYSIS</span><h2>AI Investigation Insights</h2></div><span class="state-tag">VALIDATION REQUIRED</span></div><div id="ai-insights" class="insight-body"><div class="insight-symbol">✳</div><div><b>No validated insight available</b><p>Analysis appears only when the configured inference service returns a validated result with provenance.</p><span>INFERENCE STATUS: NOT VERIFIED</span></div></div></section>
          <section class="dashboard-card mini-graph-card"><div class="card-heading compact"><div><span class="eyebrow">EVIDENCE FUSION</span><h2>Relationship Graph</h2></div><button id="expand-graph" class="text-action">VIEW GRAPH ↗</button></div><div id="evidence-graph" class="mini-graph"><div class="graph-lines"></div><span class="graph-node center">EVIDENCE</span><span class="graph-node n1">DOC</span><span class="graph-node n2">ENTITY</span><span class="graph-node n3">EVENT</span><span class="graph-node n4">GEO</span><span class="graph-node n5">SRC</span><span class="graph-node n6">TIME</span><p>Nodes populate from selected evidence relationships.</p></div></section>
        </div>
      </section>
      <section class="secondary-row">
        <section class="dashboard-card timeline-card"><div class="card-heading compact"><div><span class="eyebrow">TEMPORAL RECONSTRUCTION</span><h2>Event Timeline</h2></div><button id="timeline" class="text-action">LOAD HISTORY ↗</button></div><div class="timeline-rail"><div id="timeline-results" class="timeline-results">Select an entity and load its recorded history. No past state is fabricated.</div></div><div class="timeline-foot"><span>TIME RANGE <b>LAST 7 DAYS</b></span><span>TIME BASIS <b>UTC</b></span></div></section>
        <section class="dashboard-card imagery-card"><div class="card-heading compact"><div><span class="eyebrow">REMOTE SENSING</span><h2>Imagery & Source Coverage</h2></div><button id="imagery-gallery" class="text-action">SOURCE STATUS ↗</button></div><div id="imagery-gallery-items" class="imagery-gallery"><div class="imagery-placeholder"><span>◈</span><b>NASA GIBS</b><small>Toggle satellite imagery on the globe</small></div><div class="imagery-placeholder"><span>▧</span><b>USGS EVENTS</b><small id="imagery-events-status">Waiting for source result</small></div><div class="imagery-placeholder"><span>◎</span><b>ORBITAL FEED</b><small id="imagery-orbital-status">Waiting for source result</small></div></div></section>
        <section class="dashboard-card provenance-card"><div class="card-heading compact"><div><span class="eyebrow">DATA LINEAGE</span><h2>Provenance Tracking</h2></div><span class="state-tag">TRACEABLE</span></div><div class="provenance-flow"><div class="prov-step"><span>01</span><b>Source</b><small>Provider record</small></div><i>→</i><div class="prov-step"><span>02</span><b>Normalize</b><small>Schema check</small></div><i>→</i><div class="prov-step"><span>03</span><b>Validate</b><small>Trust boundary</small></div><i>→</i><div class="prov-step"><span>04</span><b>Inspect</b><small>Analyst review</small></div></div><div class="provenance-note">Trace metadata is shown per observation when provided. This diagram describes the workflow, not a claim that every record passed every stage.</div></section>
      </section>
      <section class="bottom-panels">
        <section class="dashboard-card system-card"><div class="card-heading compact"><div><span class="eyebrow">RUNTIME OPERATIONS</span><h2>System Monitoring</h2></div><span id="system-status" class="state-tag">UNKNOWN</span></div><div class="system-metrics"><div><span class="system-ring cyan-ring">API</span><b id="system-api">UNKNOWN</b><small>Analyst endpoint</small></div><div><span class="system-ring green-ring">GEO</span><b id="system-geo">UNKNOWN</b><small>Spatial source</small></div><div><span class="system-ring violet-ring">AI</span><b>UNVERIFIED</b><small>Inference service</small></div><div><span class="system-ring amber-ring">DB</span><b>UNVERIFIED</b><small>Persistence health</small></div></div></section>
        <section class="dashboard-card selected-evidence-card"><div class="card-heading compact"><div><span class="eyebrow">INSPECTION WORKSPACE</span><h2>Selected Evidence</h2></div><button id="clear-selection" class="text-action">CLEAR</button></div><div id="inspector-empty" class="empty-inspector"><div class="target-icon">⌖</div><b>No entity selected</b><p>Select a marker on the globe or use global search to inspect available properties and provenance.</p></div><div id="entity-details" hidden></div><label class="field-label">Entity identifier<input id="entity-id" placeholder="Select an entity or enter ID"/></label><div class="timeline-actions"><button id="load-entity-timeline">LOAD HISTORY</button><button id="clear-timeline">CLEAR</button></div></section>
      </section>
    </main>
  </div>
  <div class="bottom-status"><span><i class="status-square"></i> QUANTSOIL ANALYST WORKSPACE</span><span id="data-state">DATA STATE: NOT YET VERIFIED</span><span>WGS84 · UTC</span></div>
</div>`;

const viewer = new Viewer("globe", {
  animation:false, timeline:false, baseLayerPicker:false, geocoder:false, homeButton:false,
  navigationHelpButton:false, sceneModePicker:false, fullscreenButton:false,
  infoBox:false, selectionIndicator:false, terrainProvider:new EllipsoidTerrainProvider(),
  scene3DOnly:true, requestRenderMode:true, maximumRenderTimeChange:1,
});
viewer.imageryLayers.removeAll();
const osmProvider=new OpenStreetMapImageryProvider({url:"https://tile.openstreetmap.org/"});
const osmLayer=viewer.imageryLayers.addImageryProvider(osmProvider);
const flatTerrain=new EllipsoidTerrainProvider();
let worldTerrain:any=null;
let buildingsPrimitive:any=null;
let terrainEnabled=false;
let satelliteLayer:any=null;
let satelliteEnabled=false;
viewer.camera.setView({destination:Cartesian3.fromDegrees(78,23,12500000)});
viewer.scene.globe.show=true;
viewer.scene.backgroundColor=Color.fromCssColorString("#05090f");

const $=<T extends HTMLElement>(selector:string)=>document.querySelector<T>(selector)!;
const status=$<HTMLSpanElement>("#connection"), results=$<HTMLDivElement>("#timeline-results");
const message=$<HTMLDivElement>("#map-message");
const apiHealth=$<HTMLSpanElement>("#api-health");
let sourceFeatures:any[]=[];
let selected:any=null;
let refreshSeq=0;
let refreshTimer:number|undefined;
let activeLayers=new Set(["aircraft","satellite","event","vessel","camera","other"]);
let analystSource:GeoJsonDataSource|undefined;
type CachedFeed={expires:number;features:any[];error?:string;key?:string};
let aircraftFeed:CachedFeed={expires:0,features:[]};
let earthquakeFeed:CachedFeed={expires:0,features:[]};
let orbitalFeed:CachedFeed={expires:0,features:[]};
let vesselFeed:CachedFeed={expires:0,features:[]};
let cameraFeed:CachedFeed={expires:0,features:[]};
const aircraftHistory=new Map<string,Array<{lon:number;lat:number;time:number}>>();
const aircraftOverlays=new Map<string,{marker:any;trail:any;motion:any}>();
const handler=new ScreenSpaceEventHandler(viewer.scene.canvas);

async function cachedFeed(path:string,ttl:number,cache:CachedFeed):Promise<any[]>{
  if(Date.now()<cache.expires&&cache.key===path){if(cache.error)throw new Error(cache.error);return cache.features;}
  try{
    const response=await fetch(API+path,{headers:{Accept:"application/geo+json, application/json"}});
    if(!response.ok)throw new Error("HTTP "+response.status);
    const payload=await response.json();
    cache.features=Array.isArray(payload.features)?payload.features:[];
    cache.error=undefined;
    cache.key=path;
    cache.expires=Date.now()+ttl;
    return cache.features;
  }catch(error){
    // Short negative cache prevents camera movement from hammering an unavailable provider.
    cache.error=String(error);
    cache.key=path;
    cache.expires=Date.now()+60000;
    throw error;
  }
}
function recordAircraftAndTrails(features:any[]){
  const now=Date.now();
  const seen=new Set<string>();
  for(const feature of features){
    if(category(feature)!=="aircraft")continue;
    const coords=feature.geometry?.coordinates;
    if(!Array.isArray(coords)||!Number.isFinite(Number(coords[0]))||!Number.isFinite(Number(coords[1])))continue;
    const id=String(feature.id??feature.properties?.source_entity_id??feature.properties?.entity_id??"");
    if(!id)continue;
    seen.add(id);
    const trail=aircraftHistory.get(id)||[];
    const last=trail[trail.length-1];
    // Record only meaningful position changes; retain a bounded, timestamped path.
    if(!last||Math.abs(last.lon-Number(coords[0]))>0.00001||Math.abs(last.lat-Number(coords[1]))>0.00001){
      trail.push({lon:Number(coords[0]),lat:Number(coords[1]),time:now});
      while(trail.length>24)trail.shift();
      aircraftHistory.set(id,trail);
    }
    const props=feature.properties||{};
    const heading=Number(props.track_deg);
    const image='data:image/svg+xml;charset=utf-8,'+encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 40 40"><path d="M20 2 L25 15 L36 22 L36 26 L24 23 L23 34 L29 37 L29 39 L20 36 L11 39 L11 37 L17 34 L16 23 L4 26 L4 22 L15 15 Z" fill="#44d9f5" stroke="#061019" stroke-width="1.4"/></svg>');
    let overlay=aircraftOverlays.get(id);
    if(!overlay){
      const lon=Number(coords[0]),lat=Number(coords[1]);
      const motion={startLon:lon,startLat:lat,targetLon:lon,targetLat:lat,startedAt:performance.now(),moving:false};
      const position=new CallbackPositionProperty(()=>{
        const progress=motion.moving?Math.min(1,(performance.now()-motion.startedAt)/12000):1;
        if(progress>=1)motion.moving=false;
        return Cartesian3.fromDegrees(motion.startLon+(motion.targetLon-motion.startLon)*progress,motion.startLat+(motion.targetLat-motion.startLat)*progress);
      },false);
      const marker=viewer.entities.add({id:"motion:"+id,position,properties:{...props,entity_id:id},billboard:{image,scale:.85,rotation:0,alignedAxis:Cartesian3.UNIT_Z,verticalOrigin:VerticalOrigin.BOTTOM},label:{text:String(props.callsign||props.name||id),font:"10px sans-serif",fillColor:Color.fromCssColorString("#c9f8ff"),outlineColor:Color.fromCssColorString("#061019"),outlineWidth:3,style:LabelStyle.FILL_AND_OUTLINE,pixelOffset:new Cartesian2(0,-18)}});
      const trailEntity=viewer.entities.add({id:"trail:"+id,polyline:{positions:trail.map(p=>Cartesian3.fromDegrees(p.lon,p.lat)),width:2,material:new ColorMaterialProperty(Color.fromCssColorString("#44d9f5").withAlpha(.55))}});
      overlay={marker,trail:trailEntity,motion};aircraftOverlays.set(id,overlay);
    }else{
      const lon=Number(coords[0]),lat=Number(coords[1]),motion=overlay.motion;
      if(Math.abs(lon-motion.targetLon)>0.00001||Math.abs(lat-motion.targetLat)>0.00001){
        const progress=motion.moving?Math.min(1,(performance.now()-motion.startedAt)/12000):1;
        motion.startLon=motion.startLon+(motion.targetLon-motion.startLon)*progress;
        motion.startLat=motion.startLat+(motion.targetLat-motion.startLat)*progress;
        motion.targetLon=lon;motion.targetLat=lat;motion.startedAt=performance.now();motion.moving=true;
        viewer.scene.requestRender();
      }
      overlay.marker.properties={...props,entity_id:id};
      overlay.marker.billboard.rotation=Number.isFinite(heading)?-heading*Math.PI/180:0;
      overlay.marker.label.text=String(props.callsign||props.name||id);
      overlay.trail.polyline.positions=trail.map(p=>Cartesian3.fromDegrees(p.lon,p.lat));
    }
    overlay.marker.show=activeLayers.has("aircraft");
    overlay.trail.show=activeLayers.has("aircraft")&&trail.length>1;
  }
  // Keep prior tracks visible through temporary provider gaps; do not fabricate motion.
  for(const [id,overlay] of aircraftOverlays){
    overlay.marker.show=activeLayers.has("aircraft");
    const trail=aircraftHistory.get(id)||[];
    overlay.trail.show=activeLayers.has("aircraft")&&trail.length>1;
  }
}

function category(feature:any):string {
  const p=feature?.properties||{};
  const raw=String(p.entity_type||p.type||p.category||p.kind||p.layer||"other").toLowerCase();
  if(/aircraft|flight|plane|ads.?b/.test(raw))return "aircraft";
  if(/satellite|orbital|spacecraft|orbit/.test(raw))return "satellite";
  if(/earthquake|event|fire|weather|disaster|volcano/.test(raw))return "event";
  if(/vessel|ship|maritime|\bais\b/.test(raw))return "vessel";
  if(/camera|cctv|video_source/.test(raw))return "camera";
  return "other";
}
function propValue(value:any):string {
  if(value===null||value===undefined||value==="")return "—";
  if(typeof value==="object")return JSON.stringify(value);
  return String(value);
}
function safeText(value:any):string {
  return String(value??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]!));
}
function safeHttpUrl(value:any):string|null {
  try {
    const url=new URL(String(value??""));
    return url.protocol==="https:"||url.protocol==="http:"?url.href:null;
  } catch { return null; }
}
function featureProps(feature:any):Record<string,any>{return feature?.properties||{};}
function updateCoordinates(position:any){
  const cartesian=viewer.camera.pickEllipsoid(position,viewer.scene.globe.ellipsoid);
  if(!cartesian){$<HTMLElement>("#coordinates").textContent="LAT — / LON —";return;}
  const cartographic=viewer.scene.globe.ellipsoid.cartesianToCartographic(cartesian);
  const lat=cartographic.latitude*180/Math.PI,lon=cartographic.longitude*180/Math.PI;
  $<HTMLElement>("#coordinates").textContent="LAT "+lat.toFixed(4)+"° / LON "+lon.toFixed(4)+"°";
}
function applyLayerVisibility(){
  for(const entity of viewer.entities.values){
    const id=String(entity.id??"");
    if(id.startsWith("motion:")){entity.show=activeLayers.has("aircraft");continue;}
    if(id.startsWith("trail:")){
      const history=aircraftHistory.get(id.slice(6))||[];
      entity.show=activeLayers.has("aircraft")&&history.length>1;continue;
    }
    const p=(entity.properties as any)?.toJSON?.()||{};
    entity.show=activeLayers.has(category({properties:p}));
  }
  if(analystSource) for(const entity of analystSource.entities.values){
    const p=(entity.properties as any)?.toJSON?.()||{};
    entity.show=activeLayers.has(category({properties:p}));
  }
}
function showEntity(feature:any){
  selected=feature;
  const p=featureProps(feature);
  const sourceUrl=safeHttpUrl(p.source_url);
  const authorizedStreamUrl=safeHttpUrl(p.authorized_stream_url);
  const id=feature.id??p.id??p.entity_id??p.source_entity_id??"Unknown ID";
  const kind=category(feature);
  const evidenceLinks=[
    sourceUrl?'<a href="'+safeText(sourceUrl)+'" target="_blank" rel="noopener noreferrer">OPEN SOURCE ↗</a>':"",
    kind==="camera"&&authorizedStreamUrl?.startsWith("https://")?'<a href="'+safeText(authorizedStreamUrl)+'" target="_blank" rel="noopener noreferrer">OPEN AUTHORIZED CAMERA ↗</a>':""
  ].join("");
  const name=p.name||p.callsign||p.title||id;
  $<HTMLDivElement>("#inspector-empty").hidden=true;
  const details=$<HTMLDivElement>("#entity-details");details.hidden=false;
  const entries=Object.entries(p).filter(([k])=>!["geometry","bbox"].includes(k)).slice(0,24);
  details.innerHTML=`<div class="entity-type"><span class="layer-icon ${kind==="aircraft"?"cyan":kind==="event"?"amber":kind==="satellite"||kind==="camera"?"violet":"green"}">${kind==="aircraft"?"✈":kind==="event"?"⌁":kind==="satellite"?"◉":kind==="vessel"?"◆":kind==="camera"?"▣":"⌖"}</span><span>${safeText(kind.toUpperCase())}</span><span class="freshness">${safeText(p.freshness||"FRESHNESS UNKNOWN")}</span></div><h2 class="entity-title">${safeText(name)}</h2><div class="entity-id">${safeText(id)}</div><div class="section-label">OBSERVATION PROPERTIES</div><div class="property-grid">${entries.map(([k,v])=>`<div class="property"><small>${safeText(k.replace(/_/g," ").toUpperCase())}</small><b>${safeText(propValue(v))}</b></div>`).join("")}</div><div class="evidence-box"><div class="evidence-title">PROVENANCE</div><div>Source: ${safeText(p.provider_id||p.source||"Not supplied")}</div><div>Observed: ${safeText(p.observed_at||p.timestamp||"Unknown")}</div><div>Evidence ref: ${safeText(p.evidence_id||p.evidence_ref||"Not supplied")}</div>${evidenceLinks}</div>`;
  $<HTMLInputElement>("#entity-id").value=String(id);
  $<HTMLSpanElement>("#data-state").textContent="DATA STATE: ENTITY SELECTED";
}
handler.setInputAction((movement:any)=>{
  updateCoordinates(movement.position);
  const picked=viewer.scene.pick(movement.position);
  if(!picked){return;}
  const entity=picked.id;
  if(!entity)return;
  const rawId=String(entity.id??"");
  const id=rawId.startsWith("motion:")?rawId.slice(7):rawId;
  const feature=sourceFeatures.find(f=>String(f.id??f.properties?.id??f.properties?.entity_id)===id||String(f.properties?.source_entity_id??"")===id.replace(/^adsb:/,""));
  if(feature){showEntity(feature);return;}
  const props=(entity.properties as any)?.toJSON?.()||{};
  if(Object.keys(props).length)showEntity({id,properties:props});
},ScreenSpaceEventType.LEFT_CLICK);

function bbox():string{
  const rect=viewer.camera.computeViewRectangle(viewer.scene.globe.ellipsoid);
  if(!rect)return "";
  const d=(x:number)=>x*180/Math.PI;
  return [d(rect.west),d(rect.south),d(rect.east),d(rect.north)].join(",");
}
function featureCollection(data:any):any[]{
  if(Array.isArray(data?.features))return data.features;
  if(Array.isArray(data?.items))return data.items;
  return [];
}
function paintSource(data:any){
  sourceFeatures=featureCollection(data);
  // Normalize supported API envelopes into a renderable GeoJSON FeatureCollection.
  // Previously, {items:[Feature,...]} updated counters but rendered no map entities.
  const renderPayload=data?.type==="FeatureCollection"&&Array.isArray(data.features)
    ? data
    : {type:"FeatureCollection",features:sourceFeatures.filter((f:any)=>f&&f.type==="Feature"&&f.geometry)};
  if(analystSource){viewer.dataSources.remove(analystSource,true);analystSource=undefined;}
  if(renderPayload.features.length){
    GeoJsonDataSource.load(renderPayload,{clampToGround:false}).then(ds=>{
      analystSource=ds;ds.name="quantsoil-analyst";
      ds.entities.values.forEach(e=>{
        const feature=sourceFeatures.find(f=>String(f.id??f.properties?.id??f.properties?.entity_id)===String(e.id));
        const kind=category(feature||{properties:(e.properties as any)?.toJSON?.()||{}});
        const color=kind==="aircraft"?Color.fromCssColorString("#44d9f5"):kind==="event"?Color.fromCssColorString("#ffb64d"):kind==="satellite"?Color.fromCssColorString("#b49aff"):kind==="vessel"?Color.fromCssColorString("#59e0b1"):kind==="camera"?Color.fromCssColorString("#ef83ff"):Color.fromCssColorString("#a9bac9");
        if(e.point){e.point.color=new ConstantProperty(color);e.point.pixelSize=new ConstantProperty(7);e.point.outlineColor=new ConstantProperty(Color.fromCssColorString("#061019"));e.point.outlineWidth=new ConstantProperty(1);if(kind==="aircraft")e.show=false;}
        if(e.polyline){e.polyline.material=new ColorMaterialProperty(color.withAlpha(.8));e.polyline.width=new ConstantProperty(2);}
      });
      viewer.dataSources.add(ds);applyLayerVisibility();
    }).catch(()=>{message.textContent="Map payload could not be rendered.";});
  }
  $<HTMLElement>("#kpi-features").textContent=String(sourceFeatures.length);
  $<HTMLElement>("#kpi-features-note").textContent=sourceFeatures.length ? "Returned by configured feeds" : "No observations returned";
  const counts={aircraft:0,satellite:0,event:0,vessel:0,camera:0,other:0};
  sourceFeatures.forEach(f=>counts[category(f) as keyof typeof counts]++);
  $<HTMLElement>("#kpi-events").textContent=String(counts.event);
  $<HTMLElement>("#kpi-orbital").textContent=String(counts.satellite);
  const respondingFeeds=[aircraftFeed,earthquakeFeed,orbitalFeed,vesselFeed,cameraFeed].filter(f=>!f.error && Date.now() < f.expires).length;
  $<HTMLElement>("#kpi-sources").textContent=respondingFeeds+"/5";
  $<HTMLElement>("#kpi-sources-note").textContent="Recent feed responses; not uptime";
  $<HTMLElement>("#kpi-confidence").textContent="N/A";
  $<HTMLElement>("#imagery-events-status").textContent=earthquakeFeed.features.length+" observations returned";
  $<HTMLElement>("#imagery-orbital-status").textContent=orbitalFeed.features.length+" propagated positions returned";
  $<HTMLElement>("#map-freshness").textContent=sourceFeatures.some(f=>f.properties?.observed_at||f.properties?.timestamp) ? "TIMESTAMPS AVAILABLE" : "FRESHNESS UNKNOWN";
  const events=sourceFeatures.filter(f=>category(f)==="event").slice(0,5);
  $<HTMLElement>("#event-count").textContent=String(counts.event);
  $<HTMLElement>("#recent-events").innerHTML=events.length?events.map((f:any)=>{const p=f.properties||{};const title=p.title||p.name||p.event_type||"Earth event";const where=p.place||p.region||p.location||"Location not supplied";const when=p.observed_at||p.timestamp||p.updated_at||"Time not supplied";const magnitude=p.magnitude??p.severity??p.priority;return '<div class="event-row"><span class="event-icon">⌁</span><div class="event-main"><b>'+safeText(title)+'</b><small>'+safeText(where)+' · '+safeText(when)+'</small></div><span class="event-meta">'+safeText(magnitude===undefined?"SOURCE DATA":("LEVEL "+magnitude))+'<em>OBSERVED</em></span></div>';}).join(""):'<div class="empty-card">No event observations returned by the configured feeds. Nothing is being fabricated as a live event.</div>';
  $<HTMLSpanElement>("#feature-total").textContent=sourceFeatures.length+" FEATURES";
  const counts={aircraft:0,satellite:0,event:0,vessel:0,camera:0,other:0};
  sourceFeatures.forEach(f=>counts[category(f) as keyof typeof counts]++);
  $<HTMLElement>("#aircraft-status").textContent=counts.aircraft+" features returned";
  $<HTMLElement>("#satellite-status").textContent=counts.satellite+" features returned";
  $<HTMLElement>("#events-status").textContent=counts.event+" features returned";
  $<HTMLElement>("#vessel-status").textContent=counts.vessel?counts.vessel+" evidence features":"No AIS provider configured";
  $<HTMLElement>("#camera-status").textContent=counts.camera?counts.camera+" authorized metadata features":"No authorized source configured";
  $<HTMLElement>("#other-status").textContent=counts.other+" features returned";
  $<HTMLElement>("#map-message").textContent=sourceFeatures.length?"Spatial observations loaded; timestamps and provider determine freshness.":"No features in this viewport.";
  $<HTMLElement>("#map-message").classList.toggle("hidden",sourceFeatures.length>0);
}
async function refreshMap(){
  const seq=++refreshSeq;const box=bbox();if(!box)return;
  status.textContent="REQUESTING SPATIAL DATA";apiHealth.textContent="CHECKING";
  const failures:string[]=[];
  let analystFeatures:any[]=[];
  try{
    const response=await fetch(`${API}/spatial?bbox=${encodeURIComponent(box)}&limit=500`,{headers:{Accept:"application/geo+json, application/json"}});
    if(!response.ok)throw new Error(`HTTP ${response.status}`);
    const data=await response.json();analystFeatures=featureCollection(data);
  }catch(error){failures.push("Analyst API: "+String(error));}
  const [aircraftResult,eventResult,orbitalResult,vesselResult,cameraResult]=await Promise.allSettled([
    cachedFeed("/sources/aircraft?bbox="+encodeURIComponent(box),30000,aircraftFeed),
    cachedFeed("/sources/earthquakes",300000,earthquakeFeed),
    cachedFeed("/sources/orbital",300000,orbitalFeed),
    cachedFeed("/sources/maritime",60000,vesselFeed),
    cachedFeed("/sources/cameras",60000,cameraFeed)
  ]);
  if(aircraftResult.status==="fulfilled")aircraftFeed.features=aircraftResult.value;else failures.push("Aircraft: "+String(aircraftResult.reason));
  if(eventResult.status==="fulfilled")earthquakeFeed.features=eventResult.value;else failures.push("Earthquakes: "+String(eventResult.reason));
  if(orbitalResult.status==="fulfilled")orbitalFeed.features=orbitalResult.value;else failures.push("Orbital: "+String(orbitalResult.reason));
  if(vesselResult.status==="fulfilled")vesselFeed.features=vesselResult.value;else if(!String(vesselResult.reason).includes("503"))failures.push("Maritime: "+String(vesselResult.reason));
  if(cameraResult.status==="fulfilled")cameraFeed.features=cameraResult.value;else if(!String(cameraResult.reason).includes("503"))failures.push("Authorized camera metadata: "+String(cameraResult.reason));
  if(seq!==refreshSeq)return;
  const combined=[...analystFeatures,...aircraftFeed.features,...earthquakeFeed.features,...orbitalFeed.features,...vesselFeed.features,...cameraFeed.features];
  // Deduplicate by stable provider feature ID, preferring the freshest returned copy.
  const byId=new Map<string,any>();
  for(const feature of combined){const id=String(feature?.id??JSON.stringify(feature?.geometry));if(!byId.has(id))byId.set(id,feature);}
  const features=[...byId.values()];
  recordAircraftAndTrails(features);
  paintSource({type:"FeatureCollection",features});
  $<HTMLElement>("#vessel-status").textContent=vesselResult.status==="fulfilled"
    ? vesselFeed.features.length+" AIS observations"
    : String(vesselResult.reason).includes("503")?"No AIS provider configured":"Provider unavailable";
  $<HTMLElement>("#camera-status").textContent=cameraResult.status==="fulfilled"
    ? cameraFeed.features.length+" authorized metadata records"
    : String(cameraResult.reason).includes("503")?"No authorized source configured":"Provider unavailable";
  const partial=failures.length>0;
  status.textContent=partial?(features.length?"PARTIAL SOURCES":"SOURCES UNAVAILABLE"):"PUBLIC SOURCES CONNECTED";
  apiHealth.textContent=partial?"PARTIAL":"ONLINE";
  $<HTMLElement>("#source-health").querySelector(".health-dot")?.classList.toggle("idle",partial);
  $<HTMLElement>("#last-check").textContent=new Date().toISOString().slice(11,19)+"Z";
  $<HTMLElement>("#data-state").textContent=partial
    ?"DATA STATE: PARTIAL SOURCES · "+failures.length+" SOURCE(S) UNAVAILABLE"
    :"DATA STATE: PROVIDERS RESPONDING · OBSERVATION FRESHNESS SHOWN PER ENTITY";
  if(features.length===0){
    message.textContent=failures.length?"No observations loaded. "+failures.join(" · "):"No observations returned for this viewport.";
    message.classList.remove("hidden");
  }else message.classList.add("hidden");
}
function scheduleRefresh(){window.clearTimeout(refreshTimer);refreshTimer=window.setTimeout(()=>void refreshMap(),450);}
document.querySelectorAll<HTMLInputElement>("[data-layer]").forEach(input=>input.addEventListener("change",()=>{
  const kind=input.dataset.layer!;if(input.checked)activeLayers.add(kind);else activeLayers.delete(kind);applyLayerVisibility();if(kind==="aircraft")for(const overlay of aircraftOverlays.values()){overlay.marker.show=input.checked;overlay.trail.show=input.checked&&(aircraftHistory.get(String(overlay.marker.id).replace("motion:",""))||[]).length>1;}
}));
$<HTMLButtonElement>("#refresh").addEventListener("click",()=>void refreshMap());
$<HTMLButtonElement>("#home").addEventListener("click",()=>viewer.camera.flyTo({destination:Cartesian3.fromDegrees(78,23,12500000),duration:.8}));
$<HTMLButtonElement>("#camera-reset").addEventListener("click",()=>viewer.camera.flyTo({destination:Cartesian3.fromDegrees(78,23,12500000),duration:.8}));
$<HTMLButtonElement>("#terrain-toggle").addEventListener("click",async()=>{
  const button=$<HTMLButtonElement>("#terrain-toggle");
  const token=String(import.meta.env.VITE_CESIUM_ION_TOKEN||"").trim();
  if(!token){
    message.textContent="3D terrain/buildings need VITE_CESIUM_ION_TOKEN configured at build time. Use a domain-restricted public token with only the required Cesium assets.";
    message.classList.remove("hidden");return;
  }
  if(terrainEnabled){
    viewer.terrainProvider=flatTerrain;
    if(buildingsPrimitive)buildingsPrimitive.show=false;
    terrainEnabled=false;button.classList.remove("active");button.textContent="3D TERRAIN";
    return;
  }
  if(worldTerrain&&buildingsPrimitive){
    viewer.terrainProvider=worldTerrain;buildingsPrimitive.show=true;terrainEnabled=true;
    button.classList.add("active");button.textContent="3D TERRAIN ON";return;
  }
  button.disabled=true;button.textContent="LOADING TERRAIN…";
  try{
    Ion.defaultAccessToken=token;
    const [terrain,buildings]=await Promise.all([createWorldTerrainAsync(),createOsmBuildingsAsync()]);
    worldTerrain=terrain;buildingsPrimitive=buildings;
    viewer.terrainProvider=worldTerrain;
    buildingsPrimitive.show=true;viewer.scene.primitives.add(buildingsPrimitive);
    viewer.scene.globe.depthTestAgainstTerrain=true;
    terrainEnabled=true;button.classList.add("active");button.textContent="3D TERRAIN ON";
    message.classList.add("hidden");
  }catch(error){
    message.textContent="Cesium terrain/buildings could not be loaded. Check token restrictions and asset access: "+String(error);
    message.classList.remove("hidden");
  }finally{button.disabled=false;if(!terrainEnabled)button.textContent="3D TERRAIN";}
});
$<HTMLButtonElement>("#zoom-in").addEventListener("click",()=>viewer.camera.zoomIn(viewer.camera.positionCartographic.height*.35));
$<HTMLButtonElement>("#zoom-out").addEventListener("click",()=>viewer.camera.zoomOut(viewer.camera.positionCartographic.height*.35));
$<HTMLButtonElement>("#view-3d").addEventListener("click",()=>{viewer.scene.morphTo3D(.6);$<HTMLElement>("#view-3d").classList.add("active");$<HTMLElement>("#view-2d").classList.remove("active");});
$<HTMLButtonElement>("#view-2d").addEventListener("click",()=>{viewer.scene.morphTo2D(.6);$<HTMLElement>("#view-2d").classList.add("active");$<HTMLElement>("#view-3d").classList.remove("active");});
$<HTMLButtonElement>("#imagery-toggle").addEventListener("click",async()=>{
  const button=$<HTMLButtonElement>("#imagery-toggle");
  if(satelliteEnabled){
    if(satelliteLayer)viewer.imageryLayers.remove(satelliteLayer,true);
    satelliteLayer=null;satelliteEnabled=false;
    button.classList.remove("active");
    button.textContent="SATELLITE";
    return;
  }
  button.disabled=true;button.textContent="LOADING…";
  try{
    const productDate=new Date(Date.now()-2*86400000).toISOString().slice(0,10);
    const provider=new WebMapTileServiceImageryProvider({
      url:"https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/VIIRS_SNPP_CorrectedReflectance_TrueColor/default/"+productDate+"/GoogleMapsCompatible_Level9/{TileMatrix}/{TileRow}/{TileCol}.jpg",
      layer:"VIIRS_SNPP_CorrectedReflectance_TrueColor",style:"default",format:"image/jpeg",
      tileMatrixSetID:"GoogleMapsCompatible_Level9",maximumLevel:9
    });
    satelliteLayer=viewer.imageryLayers.addImageryProvider(provider);
    satelliteEnabled=true;
    button.classList.add("active");button.textContent="SATELLITE ON";
  }catch(error){
    message.textContent="Satellite imagery could not be configured: "+String(error);
    message.classList.remove("hidden");
  }finally{button.disabled=false;}
});
$<HTMLButtonElement>("#clear-selection").addEventListener("click",()=>{selected=null;$<HTMLDivElement>("#entity-details").hidden=true;$<HTMLDivElement>("#inspector-empty").hidden=false;$<HTMLSpanElement>("#data-state").textContent="DATA STATE: NO ENTITY SELECTED";});
$<HTMLButtonElement>("#toggle-left").addEventListener("click",()=>{
  $<HTMLElement>(".left-panel").classList.toggle("collapsed");
  $<HTMLElement>(".workspace").classList.toggle("left-collapsed");
  window.setTimeout(()=>viewer.resize(),180);
});
$<HTMLButtonElement>("#close-inspector").addEventListener("click",()=>$<HTMLElement>("#inspector").classList.toggle("collapsed"));
$<HTMLButtonElement>("#toggle-right").addEventListener("click",()=>$<HTMLElement>("#inspector").classList.toggle("collapsed"));
async function runSearch(){
  const q=$<HTMLInputElement>("#search").value.trim().toLowerCase();
  if(!q)return;
  let found=sourceFeatures.find(f=>JSON.stringify([f.id,f.properties]).toLowerCase().includes(q));
  if(!found){
    message.textContent="Searching indexed map evidence…";message.classList.remove("hidden");
    try{
      const response=await fetch(`${API}/search?q=${encodeURIComponent(q)}&limit=25`,{headers:{Accept:"application/geo+json, application/json"}});
      if(!response.ok)throw new Error(response.status===404?"Global search endpoint is not deployed yet.":`HTTP ${response.status}`);
      const data=await response.json();
      found=featureCollection(data)[0];
      if(!found){message.textContent="No indexed match found. Try a source, identifier, feature type or property.";return;}
    }catch(error){
      message.textContent="Global search unavailable: "+String(error);return;
    }
  }
  showEntity(found);
  const coords=found.geometry?.coordinates;
  const point=Array.isArray(coords)&&typeof coords[0]==="number"&&typeof coords[1]==="number"
    ? coords
    : Array.isArray(coords?.[0])&&typeof coords[0][0]==="number" ? coords[0] : null;
  if(point){
    message.classList.add("hidden");
    viewer.camera.flyTo({destination:Cartesian3.fromDegrees(Number(point[0]),Number(point[1]),Math.max(120000,viewer.camera.positionCartographic.height*.25)),duration:1});
  }
}
$<HTMLButtonElement>("#search-go").addEventListener("click",runSearch);
$<HTMLInputElement>("#search").addEventListener("keydown",e=>{if(e.key==="Enter")runSearch();});
$<HTMLButtonElement>("#timeline").addEventListener("click",async()=>{
  const id=$<HTMLInputElement>("#entity-id").value.trim();if(!id){results.textContent="Select an entity or enter an identifier.";return;}
  results.textContent="Loading timeline…";
  const start=new Date(Date.now()-7*86400000).toISOString(),end=new Date().toISOString();
  try{
    const r=await fetch(`${API}/timeline/${encodeURIComponent(id)}?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`);
    const data=await r.json();if(!r.ok)throw new Error(data.detail||`HTTP ${r.status}`);
    results.innerHTML=Array.isArray(data.changes)&&data.changes.length?data.changes.map((c:any)=>`<article><b>${safeText(c.from_state_id||"initial")} → ${safeText(c.to_state_id)}</b><small>${safeText(c.valid_from||"")}</small><div>${safeText((c.changed_properties||[]).join(", ")||"No property change")}</div><code>${safeText((c.evidence_refs||[]).join(", "))}</code></article>`).join(""):"No history returned for this time window.";
  }catch(e){results.textContent="Timeline unavailable: "+String(e);}
});
$<HTMLButtonElement>("#clear-timeline").addEventListener("click",()=>{results.textContent="Historical data appears here when available from the analyst API.";});
// Update geographic readout from the actual globe point under the pointer.
handler.setInputAction((movement:any)=>updateCoordinates(movement.endPosition),ScreenSpaceEventType.MOUSE_MOVE);
viewer.scene.postRender.addEventListener(()=>{
  const p=viewer.camera.positionCartographic;
  $<HTMLElement>("#altitude").textContent=p?Math.round(p.height/1000).toLocaleString()+" KM ALTITUDE":"GLOBAL VIEW";
});
window.setInterval(()=>{$<HTMLElement>("#clock").textContent=new Date().toISOString().slice(11,19)+" UTC";},1000);
viewer.camera.moveEnd.addEventListener(scheduleRefresh);
// Refresh at a bounded cadence even when the camera is stationary. This queries
// the configured API; it does not turn static data into a verified live feed.
window.setInterval(()=>void refreshMap(),30000);
// requestRenderMode saves idle work; request frames at 10 Hz only while aircraft
// interpolation is active so observed position changes animate smoothly.
window.setInterval(()=>{
  if([...aircraftOverlays.values()].some(overlay=>overlay.motion.moving))viewer.scene.requestRender();
},100);
void refreshMap();
