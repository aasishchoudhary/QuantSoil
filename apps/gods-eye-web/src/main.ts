import {
  Viewer, Cartesian3, GeoJsonDataSource, Color, ConstantProperty,
  OpenStreetMapImageryProvider, EllipsoidTerrainProvider, ScreenSpaceEventHandler,
  ScreenSpaceEventType, Cartographic
} from "cesium";
import "cesium/Build/Cesium/Widgets/widgets.css";
import "./style.css";

const API = import.meta.env.VITE_ANALYST_API_BASE || "/v1/analyst";
const app = document.querySelector<HTMLDivElement>("#app")!;
app.innerHTML = `
<div class="ops">
  <header class="topbar">
    <div class="brand"><div class="brand-mark">Q</div><div><b>QUANTSOIL</b><small>WORLD INTELLIGENCE SYSTEM</small></div></div>
    <div class="top-center"><span class="pulse"></span><span id="connection">INITIALIZING SOURCES</span><span class="top-divider"></span><span id="clock">--:--:-- UTC</span></div>
    <div class="top-actions"><button id="refresh" title="Refresh source data">↻ <span>REFRESH</span></button><button id="home" title="Reset globe camera">⌂</button><button id="toggle-right" title="Toggle inspector">▤</button></div>
  </header>
  <div class="workspace">
    <aside class="left-panel">
      <div class="panel-head"><span>GLOBAL MONITOR</span><span class="live-dot"></span></div>
      <div class="search-wrap"><span>⌕</span><input id="search" placeholder="Search entity / identifier"/><button id="search-go">↵</button></div>
      <div class="section-label">INTELLIGENCE LAYERS <span id="layer-count">04</span></div>
      <div class="layer-list">
        <label class="layer-row"><span class="layer-icon cyan">✈</span><span class="layer-copy"><b>Aircraft & flight data</b><small id="aircraft-status">Waiting for source</small></span><input type="checkbox" data-layer="aircraft" checked/><i></i></label>
        <label class="layer-row"><span class="layer-icon violet">◉</span><span class="layer-copy"><b>Satellite / orbital objects</b><small id="satellite-status">Provider not configured</small></span><input type="checkbox" data-layer="satellite" checked/><i></i></label>
        <label class="layer-row"><span class="layer-icon amber">⌁</span><span class="layer-copy"><b>Earth events</b><small id="events-status">Waiting for source</small></span><input type="checkbox" data-layer="event" checked/><i></i></label>
        <label class="layer-row"><span class="layer-icon green">⌖</span><span class="layer-copy"><b>Other spatial evidence</b><small id="other-status">Waiting for source</small></span><input type="checkbox" data-layer="other" checked/><i></i></label>
      </div>
      <div class="section-label">MAP CONTROLS</div>
      <div class="control-list"><button id="zoom-in"><span>＋</span> Zoom in</button><button id="zoom-out"><span>－</span> Zoom out</button><button id="camera-reset"><span>◎</span> Reset global view</button><button id="clear-selection"><span>×</span> Clear selection</button></div>
      <div class="section-label">SOURCE HEALTH</div>
      <div id="source-health" class="health-card"><div><span class="health-dot idle"></span><b>Analyst API</b><span id="api-health" class="health-state">CHECKING</span></div><p>Layer data is queried from the configured QuantSoil analyst API. No feed is assumed live without source timestamps.</p><div class="health-foot"><span>LAST CHECK</span><span id="last-check">—</span></div></div>
      <div class="left-footer">EVIDENCE FIRST <span>•</span> PROVENANCE ALWAYS</div>
    </aside>
    <section class="map-wrap"><div id="globe"></div>
      <div class="map-top"><div class="coord-chip"><span class="crosshair">⌖</span><span id="coordinates">LAT — / LON —</span></div><div class="map-buttons"><button id="view-3d" class="active">3D GLOBE</button><button id="view-2d">2D MAP</button></div></div>
      <div class="map-bottom-left"><span class="scale-line"></span><span id="altitude">GLOBAL VIEW</span><span class="map-sep">|</span><span id="feature-total">0 FEATURES</span></div>
      <div class="map-bottom-right"><span class="legend-dot cyan-bg"></span> AIRCRAFT <span class="legend-dot amber-bg"></span> EVENTS <span class="legend-dot violet-bg"></span> ORBITAL <span class="legend-dot grey-bg"></span> OTHER</div>
      <div id="map-message" class="map-message">Connecting to governed spatial API…</div>
    </section>
    <aside id="inspector" class="right-panel">
      <div class="panel-head"><span>ENTITY INTELLIGENCE</span><button id="close-inspector" aria-label="Close inspector">×</button></div>
      <div id="inspector-empty" class="empty-inspector"><div class="target-icon">⌖</div><b>No entity selected</b><p>Select a marker on the globe to inspect available properties and evidence.</p></div>
      <div id="entity-details" hidden></div>
      <div class="section-label">TIMELINE / HISTORY</div>
      <label class="field-label">Entity identifier<input id="entity-id" placeholder="Select an entity or enter ID"/></label>
      <div class="timeline-actions"><button id="timeline">LOAD TIMELINE</button><button id="clear-timeline">CLEAR</button></div>
      <div id="timeline-results" class="timeline-results">Historical data appears here when available from the analyst API.</div>
      <div class="right-footer">SOURCE DATA MAY BE DELAYED OR INCOMPLETE</div>
    </aside>
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
viewer.imageryLayers.addImageryProvider(new OpenStreetMapImageryProvider({url:"https://tile.openstreetmap.org/"}));
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
let activeLayers=new Set(["aircraft","satellite","event","other"]);
let analystSource:GeoJsonDataSource|undefined;
const handler=new ScreenSpaceEventHandler(viewer.scene.canvas);

function category(feature:any):string {
  const p=feature?.properties||{};
  const raw=String(p.entity_type||p.type||p.category||p.kind||p.layer||"other").toLowerCase();
  if(/aircraft|flight|plane|ads.?b/.test(raw))return "aircraft";
  if(/satellite|orbital|spacecraft|orbit/.test(raw))return "satellite";
  if(/earthquake|event|fire|weather|disaster|volcano/.test(raw))return "event";
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
function featureProps(feature:any):Record<string,any>{return feature?.properties||{};}
function applyLayerVisibility(){
  for(const entity of viewer.entities.values){
    const p=(entity.properties as any)?.toJSON?.()||{};
    const kind=category({properties:p});
    entity.show=activeLayers.has(kind);
  }
  if(analystSource) for(const entity of analystSource.entities.values){
    const p=(entity.properties as any)?.toJSON?.()||{};
    entity.show=activeLayers.has(category({properties:p}));
  }
}
function showEntity(feature:any){
  selected=feature;
  const p=featureProps(feature);
  const id=feature.id??p.id??p.entity_id??p.source_entity_id??"Unknown ID";
  const kind=category(feature);
  const name=p.name||p.callsign||p.title||id;
  $<HTMLDivElement>("#inspector-empty").hidden=true;
  const details=$<HTMLDivElement>("#entity-details");details.hidden=false;
  const entries=Object.entries(p).filter(([k])=>!["geometry","bbox"].includes(k)).slice(0,24);
  details.innerHTML=`<div class="entity-type"><span class="layer-icon ${kind==="aircraft"?"cyan":kind==="event"?"amber":kind==="satellite"?"violet":"green"}">${kind==="aircraft"?"✈":kind==="event"?"⌁":kind==="satellite"?"◉":"⌖"}</span><span>${safeText(kind.toUpperCase())}</span><span class="freshness">${safeText(p.freshness||"FRESHNESS UNKNOWN")}</span></div><h2 class="entity-title">${safeText(name)}</h2><div class="entity-id">${safeText(id)}</div><div class="section-label">OBSERVATION PROPERTIES</div><div class="property-grid">${entries.map(([k,v])=>`<div class="property"><small>${safeText(k.replace(/_/g," ").toUpperCase())}</small><b>${safeText(propValue(v))}</b></div>`).join("")}</div><div class="evidence-box"><div class="evidence-title">PROVENANCE</div><div>Source: ${safeText(p.provider_id||p.source||"Not supplied")}</div><div>Observed: ${safeText(p.observed_at||p.timestamp||"Unknown")}</div><div>Evidence ref: ${safeText(p.evidence_id||p.evidence_ref||"Not supplied")}</div>${p.source_url?'<a href="'+safeText(p.source_url)+'" target="_blank" rel="noopener noreferrer">OPEN SOURCE ↗</a>':""}</div>`;
  $<HTMLInputElement>("#entity-id").value=String(id);
  $<HTMLSpanElement>("#data-state").textContent="DATA STATE: ENTITY SELECTED";
}
handler.setInputAction((movement:any)=>{
  const picked=viewer.scene.pick(movement.position);
  if(!picked){return;}
  const entity=picked.id;
  if(!entity)return;
  const id=entity.id;
  const feature=sourceFeatures.find(f=>String(f.id??f.properties?.id??f.properties?.entity_id)===String(id));
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
  if(analystSource){viewer.dataSources.remove(analystSource,true);analystSource=undefined;}
  if(data?.type==="FeatureCollection"&&Array.isArray(data.features)){
    GeoJsonDataSource.load(data,{clampToGround:false}).then(ds=>{
      analystSource=ds;ds.name="quantsoil-analyst";
      ds.entities.values.forEach(e=>{
        const feature=sourceFeatures.find(f=>String(f.id??f.properties?.id??f.properties?.entity_id)===String(e.id));
        const kind=category(feature||{properties:(e.properties as any)?.toJSON?.()||{}});
        const color=kind==="aircraft"?Color.fromCssColorString("#44d9f5"):kind==="event"?Color.fromCssColorString("#ffb64d"):kind==="satellite"?Color.fromCssColorString("#b49aff"):Color.fromCssColorString("#a9bac9");
        if(e.point){e.point.color=new ConstantProperty(color);e.point.pixelSize=new ConstantProperty(7);e.point.outlineColor=new ConstantProperty(Color.fromCssColorString("#061019"));e.point.outlineWidth=new ConstantProperty(1);}
        if(e.polyline){e.polyline.material=new ConstantProperty(color.withAlpha(.8));e.polyline.width=new ConstantProperty(2);}
      });
      viewer.dataSources.add(ds);applyLayerVisibility();
    }).catch(()=>{message.textContent="Map payload could not be rendered.";});
  }
  $<HTMLSpanElement>("#feature-total").textContent=sourceFeatures.length+" FEATURES";
  const counts={aircraft:0,satellite:0,event:0,other:0};
  sourceFeatures.forEach(f=>counts[category(f) as keyof typeof counts]++);
  $<HTMLElement>("#aircraft-status").textContent=counts.aircraft+" features returned";
  $<HTMLElement>("#satellite-status").textContent=counts.satellite+" features returned";
  $<HTMLElement>("#events-status").textContent=counts.event+" features returned";
  $<HTMLElement>("#other-status").textContent=counts.other+" features returned";
  $<HTMLElement>("#map-message").textContent=sourceFeatures.length?"Spatial observations loaded; timestamps and provider determine freshness.":"No features in this viewport.";
  $<HTMLElement>("#map-message").classList.toggle("hidden",sourceFeatures.length>0);
}
async function refreshMap(){
  const seq=++refreshSeq;const box=bbox();if(!box)return;
  status.textContent="REQUESTING SPATIAL DATA";apiHealth.textContent="CHECKING";
  try{
    const response=await fetch(`${API}/spatial?bbox=${encodeURIComponent(box)}&limit=500`,{headers:{Accept:"application/geo+json, application/json"}});
    if(!response.ok)throw new Error(`HTTP ${response.status}`);
    const data=await response.json();if(seq!==refreshSeq)return;
    paintSource(data);status.textContent="API RESPONDING";apiHealth.textContent="ONLINE";
    $<HTMLElement>("#source-health").querySelector(".health-dot")?.classList.remove("idle");
    $<HTMLElement>("#last-check").textContent=new Date().toISOString().slice(11,19)+"Z";
    $<HTMLElement>("#data-state").textContent="DATA STATE: API RESPONDING · FEED FRESHNESS NOT ASSUMED";
    message.classList.toggle("hidden",sourceFeatures.length>0);
  }catch(error){
    if(seq!==refreshSeq)return;
    status.textContent="SOURCE UNAVAILABLE";apiHealth.textContent="OFFLINE";
    $<HTMLElement>("#last-check").textContent=new Date().toISOString().slice(11,19)+"Z";
    message.textContent="Spatial API unavailable. No synthetic live tracks are displayed.";
    message.classList.remove("hidden");
    $<HTMLElement>("#data-state").textContent="DATA STATE: SOURCE UNAVAILABLE";
  }
}
function scheduleRefresh(){window.clearTimeout(refreshTimer);refreshTimer=window.setTimeout(()=>void refreshMap(),450);}
document.querySelectorAll<HTMLInputElement>("[data-layer]").forEach(input=>input.addEventListener("change",()=>{
  const kind=input.dataset.layer!;if(input.checked)activeLayers.add(kind);else activeLayers.delete(kind);applyLayerVisibility();
}));
$<HTMLButtonElement>("#refresh").addEventListener("click",()=>void refreshMap());
$<HTMLButtonElement>("#home").addEventListener("click",()=>viewer.camera.flyTo({destination:Cartesian3.fromDegrees(78,23,12500000),duration:.8}));
$<HTMLButtonElement>("#camera-reset").addEventListener("click",()=>viewer.camera.flyTo({destination:Cartesian3.fromDegrees(78,23,12500000),duration:.8}));
$<HTMLButtonElement>("#zoom-in").addEventListener("click",()=>viewer.camera.zoomIn(viewer.camera.positionCartographic.height*.35));
$<HTMLButtonElement>("#zoom-out").addEventListener("click",()=>viewer.camera.zoomOut(viewer.camera.positionCartographic.height*.35));
$<HTMLButtonElement>("#view-3d").addEventListener("click",()=>{viewer.scene.morphTo3D(.6);$<HTMLElement>("#view-3d").classList.add("active");$<HTMLElement>("#view-2d").classList.remove("active");});
$<HTMLButtonElement>("#view-2d").addEventListener("click",()=>{viewer.scene.morphTo2D(.6);$<HTMLElement>("#view-2d").classList.add("active");$<HTMLElement>("#view-3d").classList.remove("active");});
$<HTMLButtonElement>("#clear-selection").addEventListener("click",()=>{selected=null;$<HTMLDivElement>("#entity-details").hidden=true;$<HTMLDivElement>("#inspector-empty").hidden=false;$<HTMLSpanElement>("#data-state").textContent="DATA STATE: NO ENTITY SELECTED";});
$<HTMLButtonElement>("#close-inspector").addEventListener("click",()=>$<HTMLElement>("#inspector").classList.toggle("collapsed"));
$<HTMLButtonElement>("#toggle-right").addEventListener("click",()=>$<HTMLElement>("#inspector").classList.toggle("collapsed"));
function runSearch(){
  const q=$<HTMLInputElement>("#search").value.trim().toLowerCase();
  if(!q)return;
  const found=sourceFeatures.find(f=>JSON.stringify([f.id,f.properties]).toLowerCase().includes(q));
  if(!found){message.textContent="No matching entity in currently loaded viewport data.";message.classList.remove("hidden");return;}
  showEntity(found);
  const coords=found.geometry?.coordinates;
  if(Array.isArray(coords)&&coords.length>=2)viewer.camera.flyTo({destination:Cartesian3.fromDegrees(Number(coords[0]),Number(coords[1]),Math.max(120000,viewer.camera.positionCartographic.height*.25)),duration:1});
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
viewer.camera.changed.addEventListener(scheduleRefresh);
viewer.scene.postRender.addEventListener(()=>{
  const p=viewer.camera.positionCartographic;
  $<HTMLElement>("#altitude").textContent=p?Math.round(p.height/1000).toLocaleString()+" KM ALTITUDE":"GLOBAL VIEW";
});
window.setInterval(()=>{$<HTMLElement>("#clock").textContent=new Date().toISOString().slice(11,19)+" UTC";},1000);
viewer.camera.moveEnd.addEventListener(scheduleRefresh);
void refreshMap();
