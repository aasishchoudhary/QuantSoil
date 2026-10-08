import {Viewer,Cartesian3,GeoJsonDataSource,Color,OpenStreetMapImageryProvider,EllipsoidTerrainProvider} from "cesium";
import "cesium/Build/Cesium/Widgets/widgets.css";
import "./style.css";

const API=import.meta.env.VITE_ANALYST_API_BASE||"/v1/analyst";
const app=document.querySelector<HTMLDivElement>("#app")!;
app.innerHTML=`
<div class="shell">
  <header><div><strong>GOD'S EYE</strong><span>WORLD INTELLIGENCE</span></div><div id="status">CONNECTING</div></header>
  <main><section id="globe"></section><aside>
    <h2>Evidence-first analyst</h2>
    <p class="muted">Authoritative state is read-only. Every result retains evidence references.</p>
    <label>Entity ID<input id="entity" placeholder="entity-id"/></label>
    <div class="actions"><button id="timeline">Timeline</button><button id="clear">Clear</button></div>
    <div id="results" class="results">Move the globe or query an entity.</div>
    <footer>© OpenStreetMap contributors • intelligence data served by governed analyst API</footer>
  </aside></main>
</div>`;

const viewer=new Viewer("globe",{
  animation:false,timeline:false,baseLayerPicker:false,geocoder:false,homeButton:true,
  navigationHelpButton:false,sceneModePicker:false,terrainProvider:new EllipsoidTerrainProvider(),
});
viewer.imageryLayers.removeAll();
viewer.imageryLayers.addImageryProvider(new OpenStreetMapImageryProvider({url:"https://tile.openstreetmap.org/"}));
viewer.camera.setView({destination:Cartesian3.fromDegrees(78,23,9000000)});
const status=document.querySelector("#status")!;
const results=document.querySelector<HTMLDivElement>("#results")!;

function bbox():string{
  const r=viewer.camera.computeViewRectangle(viewer.scene.globe.ellipsoid);
  if(!r) return "";
  const d=(x:number)=>x*180/Math.PI;
  return [d(r.west),d(r.south),d(r.east),d(r.north)].join(",");
}
let requestSeq=0;
async function refreshMap(){
  const id=++requestSeq; const box=bbox(); if(!box)return;
  try{
    const response=await fetch(`${API}/spatial?bbox=${encodeURIComponent(box)}&limit=500`);
    if(!response.ok) throw new Error(`HTTP ${response.status}`);
    const data=await response.json();
    if(id!==requestSeq)return;
    const existing=viewer.dataSources.getByName("analyst")[0]; if(existing) viewer.dataSources.remove(existing,true);
    const ds=await GeoJsonDataSource.load(data,{clampToGround:false});
    ds.name="analyst";
    ds.entities.values.forEach(e=>{if(e.point)e.point.color=Color.ORANGE;if(e.point)e.point.pixelSize=8;});
    await viewer.dataSources.add(ds);
    status.textContent=`${data.count} FEATURES`;
  }catch(e){status.textContent="ANALYST OFFLINE"; results.textContent=String(e);}
}
let timer:number|undefined;
viewer.camera.changed.addEventListener(()=>{window.clearTimeout(timer);timer=window.setTimeout(refreshMap,500)});
document.querySelector("#timeline")!.addEventListener("click",async()=>{
  const entity=(document.querySelector<HTMLInputElement>("#entity")!).value.trim();
  if(!entity){results.textContent="Enter an entity ID.";return;}
  const start=new Date(Date.now()-7*86400000).toISOString(), end=new Date().toISOString();
  try{
    const r=await fetch(`${API}/timeline/${encodeURIComponent(entity)}?start=${encodeURIComponent(start)}&end=${encodeURIComponent(end)}`);
    const data=await r.json(); if(!r.ok) throw new Error(data.detail||`HTTP ${r.status}`);
    results.innerHTML=data.changes.length?data.changes.map((c:any)=>
      `<article><b>${c.from_state_id||"initial"} → ${c.to_state_id}</b><small>${c.valid_from||""}</small><div>${c.changed_properties.join(", ")||"no property change"}</div><code>${c.evidence_refs.join(", ")}</code></article>`).join(""):"No changes in requested window.";
  }catch(e){results.textContent=String(e);}
});
document.querySelector("#clear")!.addEventListener("click",()=>{results.textContent="Move the globe or query an entity.";});
refreshMap();
