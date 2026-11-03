// Tests for opt-in Chiang Mai moat track without relying on a browser.
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');

function compile(path,scope) {
  vm.runInNewContext(fs.readFileSync(path,'utf8'),scope,{filename:path});
}
function context() {return {console:{warn(){}}, bkcore:{hexgl:{tracks:{}}}};}
function routeContext(){
  const ctx=context();
  compile('assets/tracks/chiangmai-moat/route-data.js',ctx);
  compile('bkcore/hexgl/MoatCollision.js',ctx);
  return ctx;
}
{
  const ctx=routeContext();
  const route=ctx.bkcore.hexgl.MoatRouteData;
  const api=ctx.bkcore.hexgl.MoatCollision;
  const collider=new api.Collision(route);
  assert.equal(collider.loaded,true);
  assert.equal(collider.pixels.width,0);
  assert.equal(route.source,'© OpenStreetMap contributors');
  assert.equal(route.source_license,'Open Database License (ODbL) 1.0');
  assert.equal(route.osm_way_ids.length,90);
  assert.equal(route.water_polygon_count,19);
  assert.equal(route.water_way_ids.length,19);
  assert.equal(route.historic_gates.length,4);
  assert.equal(route.building_count,815,'OSM roadside building footprints');
  assert.equal(route.building_estimated_height_count,776,
               'estimated heights must be explicitly disclosed');
  assert.equal(route.building_source,'OpenStreetMap building footprints (ODbL)');
  assert.equal(route.gate_source,'OpenStreetMap historic=city_gate nodes (ODbL)');
  assert.deepEqual(Array.from(route.checkpoints,cp=>cp.point_index),[0,119,320,488]);
  assert.deepEqual(Array.from(route.historic_gates,g=>g.osm_node_id),
                   ['1017379824','6107975995','6717438786','11229077788']);
  assert.equal(route.moat_width_m,null,
               'OSM water polygons must not advertise a fake fixed width');
  for(let i=0;i<4;i++) {
    const cp=route.checkpoints[i];
    assert.equal(collider.getPixel(cp.x,cp.z).b,i,
                 'OSM checkpoint '+i+' must be on the driveable road');
  }
  const road=route.points[30];
  assert.equal(collider.getPixel(road[0],road[1]).r,255);
  assert.equal(collider.getPixel(road[0],road[1]).g,255);
  assert.equal(collider.getPixel(0,0).r,0,'old-city interior is not a road');
  assert.equal(collider.getPixel(1500,1500).r,0,'outside the moat is not a road');
  const boost=collider.boostPoints[0];
  assert.equal(collider.getPixel(boost[0],boost[1]).g,0);
  // A car just outside the 14m ribbon must be projected back into the
  // corridor rather than triggering the legacy fall() game-over path.
  const cp=route.points[80];
  const previous=route.points[79],next=route.points[81];
  const tx=next[0]-previous[0],tz=next[1]-previous[1];
  const tl=Math.hypot(tx,tz), nx=-tz/tl,nz=tx/tl;
  const inside=collider.projectInside(cp[0]+nx*2,cp[1]+nz*2,0.8);
  assert.equal(inside.corrected,false);
  const outside=collider.projectInside(cp[0]+nx*11,cp[1]+nz*11,0.8);
  assert.equal(outside.corrected,true);
  assert.ok(collider.distanceSquared(outside.x,outside.z)<=6.25*6.25);
  assert.ok(Math.hypot(outside.x-cp[0],outside.z-cp[1])<7);
  assert.equal(new api.HeightMap().getPixelFBilinear(999,999),0);
  assert.ok(route.length_m>=6540*.97 && route.length_m<=6540*1.03);
}
{
  const ctx=routeContext();
  let originalCalls=0, loaderInstance;
  const original={
    name:'Cityscape',trackScale:1.5,pixelRatio:0.2,
    spawn:{x:1000,y:400,z:50},spawnRotation:{x:0,y:0,z:0},
    checkpoints:{list:[0,1,2],start:0,last:2},
    load(opts){originalCalls++;opts.onLoad();}
  };
  ctx.bkcore.hexgl.tracks.Cityscape=original;
  ctx.bkcore.threejs={Loader:function(opts){
    this.opts=opts;
    loaderInstance=this;
    this.load=function(manifest){this.manifest=manifest;};
    this.get=function(type,name){return type+':'+name;};
  }};
  let roadLoad;
  ctx.THREE={
    StaticModelLoader:{load(url,success,error){roadLoad={url,success,error};}},
    MeshBasicMaterial:function(params){this.params=params;}
  };
  ctx.bkcore.Utils={createNormalMaterial(params){return params;}};
  compile('bkcore/hexgl/tracks/ChiangMaiMoat.js',ctx);
  const moat=ctx.bkcore.hexgl.tracks.ChiangMaiMoat;
  const yaw=ctx.bkcore.hexgl.MoatRouteData.spawn.yaw_rad;
  assert.ok(Math.abs(moat.spawnLateral.x-Math.cos(yaw))<1e-8);
  assert.ok(Math.abs(moat.spawnLateral.z+Math.sin(yaw))<1e-8);
  assert.equal(moat.spawnRotation.w,
               ctx.bkcore.hexgl.MoatRouteData.spawn.quaternion[3]);
  assert.equal(moat.moatMode,true);
  assert.equal(moat.checkpoints.list.length,4);
  assert.equal(moat.spawn.y,4);
  let calls=0;
  moat.load({onLoad(){calls++;},onError(){throw new Error('unexpected error');}},2);
  assert.equal(calls,0,'race waits for road mesh before starting');
  assert.equal(originalCalls,0,'must not preload the full Cityscape');
  const roadData=JSON.parse(fs.readFileSync(
    'assets/tracks/chiangmai-moat/road.json','utf8'));
  const road={modelData:roadData,children:[{
    name:'race-asphalt',geometry:{faces:new Array(roadData.meshes[0].indices.length/3)}
  }]};
  roadLoad.success(road);
  assert.equal(calls,0,'race waits for minimal resources after road');
  assert.equal(moat.roadModel,road);
  assert.equal(originalCalls,0);
  assert.equal(loaderInstance.manifest.geometries['ship.feisar'],
               'geometries/ships/feisar/feisar.js');
  assert.equal(loaderInstance.manifest.analysers,undefined,
               'moat must not fetch old collision/height PNG');
  const count=Object.values(loaderInstance.manifest)
    .reduce((sum,section)=>sum+Object.keys(section).length,0);
  assert.equal(count,17,'quality 2 M2 resource count should remain minimal');
  assert.equal(loaderInstance.manifest.geometries['track.cityscape'],undefined,
               'moat must not fetch old track geometry');
  assert.equal(loaderInstance.manifest.textures['track.cityscape.diffuse'],undefined,
               'moat must not fetch old asphalt texture');
  assert.equal(loaderInstance.manifest.textures['ship.feisar.normal'],
               'textures.full/ships/feisar/normal.jpg');
  moat.buildMaterials(2);
  assert.ok(moat.materials.ship);
  assert.ok(moat.materials.booster);
  loaderInstance.opts.onLoad();
  assert.equal(calls,1);
}
{
  const ctx=routeContext();
  let originalCalls=0;
  const original={
    name:'Cityscape',trackScale:1.5,pixelRatio:0.2,
    spawn:{x:1000,y:400,z:50},spawnRotation:{x:0,y:0,z:0},
    checkpoints:{list:[0,1,2],start:0,last:2},
    buildMaterials(){this.materials.fallback=true;},
    load(opts){originalCalls++;opts.onLoad();}
  };
  ctx.bkcore.hexgl.tracks.Cityscape=original;
  ctx.THREE={StaticModelLoader:{load(url,success,error){error(new Error('missing json'));}}};
  compile('bkcore/hexgl/tracks/ChiangMaiMoat.js',ctx);
  const moat=ctx.bkcore.hexgl.tracks.ChiangMaiMoat;
  let ready=0;
  moat.load({onLoad(){ready++;}},2);
  assert.equal(ready,1,'fallback continues to playable Cityscape');
  assert.equal(originalCalls,1,'fallback loads complete Cityscape manifest');
  assert.equal(moat.moatMode,false);
  assert.equal(moat.name,'Cityscape');
  assert.equal(moat.spawn.x,original.spawn.x);
  assert.equal(moat.pixelRatio,original.pixelRatio);
  moat.buildMaterials(2);
  assert.equal(moat.materials.fallback,true);
}
// A syntactically valid 200-OK static model is not necessarily the OSM
// asphalt. Missing or stale road geometry must fall back rather than let
// collision/physics run on an invisible or displaced surface.
{
  const real=JSON.parse(fs.readFileSync(
    'assets/tracks/chiangmai-moat/road.json','utf8'));
  for(const corrupt of [
    data=>{data.meshes[0].name='not-asphalt';},
    data=>{data.meshes[0].positions[0]+=100;},
    data=>{data.meshes[0].positions[111*6]+=100;},
    data=>{data.meshes[0].indices=data.meshes[0].indices.slice(0,3);},
    // Valid counts and in-range indices can still form a triangle across
    // the old city rather than the local road strip.
    data=>{data.meshes[0].indices[0]=800;},
    data=>{data.meshes[0].indices[0]=data.meshes[0].indices[1];},
    data=>{const mesh=data.meshes[0];mesh.indices[mesh.indices.length-1]=4;},
    // The static loader applies an optional mesh offset *after* reading
    // local vertices. Existing centreline checks ignored that transform.
    data=>{data.meshes[0].offset=[100,0,0];},
    // Geometry can match X/Z but hover far above the physics corridor.
    data=>{data.meshes[0].positions[111*6+1]+=50;},
    // Swapping the two sides preserves midpoint/width and valid topology
    // but flips local triangle winding and tears the strip.
    data=>{const p=data.meshes[0].positions,i=111*6;
      for(const axis of [0,1,2]) [p[i+axis],p[i+3+axis]]=[p[i+3+axis],p[i+axis]];},
    // A second asphalt mesh can render a phantom road away from collision.
    // The old validator checked only the FIRST named mesh and accepted it.
    data=>{const extra=JSON.parse(JSON.stringify(data.meshes[0]));
      extra.positions[0]+=100;data.meshes.push(extra);},
    // Valid triangles with an invisible asphalt material leave driveable
    // physics but no visible road; the material must be visibly opaque.
    data=>{data.materials[data.meshes[0].material].opacity=0;},
    data=>{data.materials[data.meshes[0].material].transparent=true;},
    // StaticModelLoader uses !!transparent, not strict boolean equality.
    data=>{data.materials[data.meshes[0].material].transparent=1;},
    data=>{data.materials[data.meshes[0].material].name='water';}
  ]) {
    const ctx=routeContext();
    let roadLoad, fallback=0, minimal=0;
    const legacy={name:'Cityscape',trackScale:1,pixelRatio:1,
      spawn:{x:0,y:4,z:0},spawnRotation:{x:0,y:0,z:0},
      checkpoints:{list:[0,1,2],start:0,last:2},
      load(opts){fallback++;opts.onLoad();}};
    ctx.bkcore.hexgl.tracks.Cityscape=legacy;
    ctx.bkcore.threejs={Loader:function(){
      this.load=function(){minimal++;};
    }};
    ctx.THREE={StaticModelLoader:{load(url,success,error){
      roadLoad={success,error};
    }}};
    compile('bkcore/hexgl/tracks/ChiangMaiMoat.js',ctx);
    const track=ctx.bkcore.hexgl.tracks.ChiangMaiMoat;
    let ready=0;
    track.load({onLoad(){ready++;}},0);
    const data=JSON.parse(JSON.stringify(real));
    corrupt(data);
    roadLoad.success({modelData:data,children:data.meshes.map(mesh=>({
      name:mesh.name,geometry:{faces:new Array(mesh.indices.length/3)}
    }))});
    assert.equal(fallback,1,'bad asphalt must load complete Cityscape');
    assert.equal(minimal,0,'bad asphalt must not load OSM-only assets');
    assert.equal(ready,1,'fallback must finish loading');
    assert.equal(track.moatMode,false);
    assert.equal(track.roadModel,null);
  }
}
// Corrupt route metadata must never silently mark every world coordinate
// driveable. Previously NaN widths bypassed the outside-road comparison.
{
  const ctx=routeContext();
  const Collision=ctx.bkcore.hexgl.MoatCollision.Collision;
  const base={closed:true,road_width_m:14,
    points:[[0,0],[100,0],[100,100],[0,100]],checkpoints:[]};
  for(const width of [NaN,Infinity,-14,0,null,'14']) {
    assert.throws(()=>new Collision({...base,road_width_m:width}),
                  /invalid road width/);
  }
  assert.throws(()=>new Collision({...base,points:[[0,0],[100,0],
    [NaN,100],[0,100]]}),/invalid road point/);
  assert.throws(()=>new Collision({...base,points:[[0,0],[0,0],
    [0,0],[0,0]]}),/zero-length route/);
  assert.equal(new Collision(base).getPixel(500,500).r,0);
}
// Even an unusually narrow but positive imported road must recover a car
// to a *driveable* point. The old fixed 0.5m minimum recovery offset
// pushed a car outside a 0.6m-wide corridor forever.
{
  const ctx=routeContext();
  const Collision=ctx.bkcore.hexgl.MoatCollision.Collision;
  const narrow=new Collision({closed:true,road_width_m:0.6,
    points:[[0,0],[100,0],[100,100],[0,100]],checkpoints:[]});
  const recovered=narrow.projectInside(50,5,0.8);
  assert.equal(recovered.corrected,true);
  assert.ok(narrow.distanceSquared(recovered.x,recovered.z)<=0.3**2,
    'recovery must stay within the actual half-width, even below 1m');
  assert.equal(narrow.getPixel(recovered.x,recovered.z).r,255,
    'recovered point must be drivable');
  const regular=new Collision({closed:true,road_width_m:14,
    points:[[0,0],[100,0],[100,100],[0,100]],checkpoints:[]});
  assert.ok(Math.abs(regular.projectInside(50,15,0.8).z-6.2)<1e-9,
    'ordinary 14m-road shoulder behaviour must remain unchanged');
}
// A corrupt route can allocate millions of spatial-index buckets before
// rendering anything. Fail fast on excessive span/width, and reject a
// silently broken OSM polyline whose measured length contradicts metadata.
{
  const ctx=routeContext();
  const Collision=ctx.bkcore.hexgl.MoatCollision.Collision;
  const base={closed:true,road_width_m:14,
    points:[[0,0],[100,0],[100,100],[0,100]],checkpoints:[]};
  assert.throws(()=>new Collision({...base,road_width_m:1e12}),
                /spatial index|road width/);
  assert.throws(()=>new Collision({...base,
    points:[[0,0],[1e9,0],[1e9,100],[0,100]]}),
                /spatial index|segment/);
  assert.throws(()=>new Collision({...base,
    points:Array.from({length:10001},(_,i)=>[i,0])}),
                /too many|point count/);
  const real=JSON.parse(JSON.stringify(ctx.bkcore.hexgl.MoatRouteData));
  real.points[12][0]+=100000;
  assert.throws(()=>new Collision(real),/length mismatch|spatial index/);
  const wrongLength=JSON.parse(JSON.stringify(ctx.bkcore.hexgl.MoatRouteData));
  wrongLength.length_m=1;
  assert.throws(()=>new Collision(wrongLength),/length mismatch/);
}
// Missing or corrupt route scripts must fall back to a playable legacy
// track, not leave the requested ChiangMaiMoat track undefined.
for(const badRoute of [undefined,{
  id:'corrupt',closed:true,road_width_m:NaN,
  points:[[0,0],[100,0],[100,100],[0,100]],
  spawn:{x:0,z:0,yaw_rad:0,quaternion:[0,0,0,1]},
  checkpoints:[{x:0,z:0},{x:100,z:0},{x:100,z:100},{x:0,z:100}]
}]) {
  const ctx=routeContext();
  const legacy={name:'Cityscape',load(){}};
  ctx.bkcore.hexgl.tracks.Cityscape=legacy;
  ctx.bkcore.hexgl.MoatRouteData=badRoute;
  compile('bkcore/hexgl/tracks/ChiangMaiMoat.js',ctx);
  assert.equal(ctx.bkcore.hexgl.tracks.ChiangMaiMoat,legacy);
}
// Regression: a bucket can contain a farther road segment while the
// truly nearest one is just outside the bucket's 19m search padding.
// Before the fallback, (75,100) snapped left to x=16.2 rather than
// right to x=103.8, potentially moving a stranded car across streets.
{
  const ctx=routeContext();
  const route={closed:true,road_width_m:14,
    points:[[10,10],[10,200],[110,200],[110,10]],checkpoints:[]};
  const collider=new ctx.bkcore.hexgl.MoatCollision.Collision(route);
  assert.equal(collider.distanceSquared(75,100),35*35);
  const recovered=collider.projectInside(75,100,0.8);
  assert.equal(recovered.corrected,true);
  assert.ok(Math.abs(recovered.x-103.8)<1e-8,recovered);
  assert.equal(recovered.z,100);
  // Ordinary near-road lookups must continue to use the indexed path.
  assert.equal(collider.distanceSquared(108,100),4);
  assert.equal(collider.projectInside(108,100,0.8).corrected,false);
}
// A large physics step can cross the old-city interior and land on the
// opposite road. Endpoint-only collision must not permit that shortcut.
{
  const ctx=routeContext();
  const route={closed:true,road_width_m:14,
    points:[[-100,-100],[100,-100],[100,100],[-100,100]],checkpoints:[]};
  const collider=new ctx.bkcore.hexgl.MoatCollision.Collision(route);
  assert.equal(collider.projectInside(100,0,0.8).corrected,false,
    'the destination is on the opposite valid road');
  const swept=collider.projectMovement(-100,0,100,0,0.8);
  assert.equal(swept.corrected,true,'crossing city interior must hit shoulder');
  assert.ok(swept.x < -90 && Math.abs(swept.z)<1,swept);
  const offroadEnd=collider.projectMovement(-100,0,60,0,0.8);
  assert.ok(offroadEnd.corrected && offroadEnd.x < -90,offroadEnd);
  const huge=collider.projectMovement(-100,0,10000,0,0.8);
  assert.ok(huge.corrected && huge.x===-100 && huge.z===0,huge);
  const along=collider.projectMovement(-100,-50,-100,50,0.8);
  assert.equal(along.corrected,false,'long travel along road stays legal');
  const short=collider.projectMovement(-100,-10,-100,-9,0.8);
  assert.equal(short.corrected,false,'normal frame must stay on fast path');
}
// A short step can cross a narrow *gap* between two nearby road ribbons.
// Both endpoints are valid, and a half-road-width (7m) early exit used to
// tunnel across the 4m non-road gap in a single 6m physics step.
{
  const ctx=routeContext();
  const route={closed:true,road_width_m:14,
    points:[[-100,0],[100,0],[100,18],[-100,18]],checkpoints:[]};
  const collider=new ctx.bkcore.hexgl.MoatCollision.Collision(route);
  assert.equal(collider.projectInside(0,6,0.8).corrected,false);
  assert.equal(collider.projectInside(0,12,0.8).corrected,false);
  assert.ok(collider.distanceSquared(0,9)>49,'the middle is not road');
  const crossing=collider.projectMovement(0,6,0,12,0.8);
  assert.ok(crossing.corrected && crossing.z<=7+1e-8,
    'short step must not tunnel through a narrow non-road gap');
}
// A normal sub-metre physics step can also cross a narrow gap. Both
// endpoints are on separate legal road ribbons, so endpoint checks alone
// are insufficient even for moves under one metre.
{
  const ctx=routeContext();
  const route={closed:true,road_width_m:14,
    points:[[-100,0],[100,0],[100,14.4],[-100,14.4]],checkpoints:[]};
  const collider=new ctx.bkcore.hexgl.MoatCollision.Collision(route);
  assert.equal(collider.projectInside(0,6.9,0.8).corrected,false);
  assert.equal(collider.projectInside(0,7.5,0.8).corrected,false);
  assert.ok(collider.distanceSquared(0,7.2)>49);
  const crossing=collider.projectMovement(0,6.9,0,7.5,0.8);
  assert.ok(crossing.corrected && crossing.z<=7+1e-8,
    'sub-metre move must not tunnel through 0.4m road gap');
  const along=collider.projectMovement(-30,6.9,-29.4,6.9,0.8);
  assert.equal(along.corrected,false,
    'near-shoulder movement along the same road must remain legal');
}
// A sub-metre shoulder step can land *inside the gap* between two roads.
// The endpoint recovery must not snap the car onto the opposite road.
// This is distinct from the previous test, where both endpoints were legal.
{
  const ctx=routeContext();
  const route={closed:true,road_width_m:14,
    points:[[-100,0],[100,0],[100,14.4],[-100,14.4]],checkpoints:[]};
  const collider=new ctx.bkcore.hexgl.MoatCollision.Collision(route);
  assert.equal(collider.projectInside(0,7.3,0.8).corrected,true,
    'destination is in the 0.4m gap');
  for(const endZ of [7.25,7.3,7.35,7.39]) {
    const crossing=collider.projectMovement(0,6.9,0,endZ,0.8);
    assert.ok(crossing.corrected && crossing.z<=7+1e-8,
      'shoulder recovery must not teleport across the gap at z='+endZ+': '+
      JSON.stringify(crossing));
  }
  const sameSide=collider.projectMovement(0,6.9,0,7.1,0.8);
  assert.ok(sameSide.corrected && Math.abs(sameSide.z-6.2)<1e-8,
    'ordinary same-side shoulder recovery must still work');
}
// Near-road lookups must stop after the padded spatial bucket search.
// A missing padding threshold silently made *every* lookup scan all 650
// segments, including getPixel calls in the per-frame collision loop.
{
  const ctx=routeContext();
  const route=ctx.bkcore.hexgl.MoatRouteData;
  const collider=new ctx.bkcore.hexgl.MoatCollision.Collision(route);
  let reads=0;
  collider.points=new Proxy(collider.points,{
    get(target,key,receiver){
      if(typeof key==='string' && /^(0|[1-9][0-9]*)$/.test(key))reads++;
      return Reflect.get(target,key,receiver);
    }
  });
  const p=route.points[100];
  assert.equal(collider.distanceSquared(p[0],p[1]),0);
  assert.ok(reads<200,'on-road distance must not scan every segment: '+reads);
  reads=0;
  assert.equal(collider.projectInside(p[0],p[1],0.8).corrected,false);
  assert.ok(reads<200,'on-road recovery must not scan every segment: '+reads);
  // The opposite case still requires a global search when outside the
  // padding, even if the current 80m bucket contains a farther segment.
  const far={closed:true,road_width_m:14,
    points:[[10,10],[10,200],[110,200],[110,10]],checkpoints:[]};
  const distant=new ctx.bkcore.hexgl.MoatCollision.Collision(far);
  assert.equal(distant.distanceSquared(75,100),1225);
  assert.ok(Math.abs(distant.projectInside(75,100,0.8).x-103.8)<1e-8);
}
// A route can have valid numeric coordinates but place the start or a gate
// off the actual drivable ribbon. Such a track boots but cannot reliably
// start or finish; it must use the existing Cityscape fallback instead.
for(const mutate of [
  r=>{r.spawn.x+=100000;},
  r=>{r.checkpoints[2].z+=100000;},
  r=>{r.spawn.quaternion=[0,0,0,0];},
  r=>{r.spawn.quaternion=[0,2,0,2];}
]) {
  const ctx=routeContext();
  const legacy={name:'Cityscape',load(){}};
  const corrupt=JSON.parse(JSON.stringify(ctx.bkcore.hexgl.MoatRouteData));
  mutate(corrupt);
  ctx.bkcore.hexgl.tracks.Cityscape=legacy;
  ctx.bkcore.hexgl.MoatRouteData=corrupt;
  compile('bkcore/hexgl/tracks/ChiangMaiMoat.js',ctx);
  assert.ok(ctx.bkcore.hexgl.tracks.ChiangMaiMoat===legacy,
            'invalid start/checkpoint geometry must fall back');
}
// The OSM analyser accepts continuous world metres, unlike the legacy
// Cityscape bitmap. Rounding a car near a diagonal 14m road edge can move
// its sampled position outside the road and silently miss a checkpoint or
// nitro pad even though the physical car remains in the legal corridor.
{
  const ctx=routeContext();
  const route={closed:true,road_width_m:14,
    points:[[0,0],[100,100],[200,0],[100,-100]],
    checkpoints:[{x:50,z:50},{x:150,z:50},{x:150,z:-50},{x:50,z:-50}]};
  const collider=new ctx.bkcore.hexgl.MoatCollision.Collision(route);
  const x=50.2,z=59.6;
  assert.ok(collider.distanceSquared(x,z)<49,'car remains on the diagonal road');
  assert.equal(collider.getPixel(x,z).b,0,'real position is in checkpoint');
  assert.equal(collider.getPixel(Math.round(x),Math.round(z)).r,0,
    'integer bitmap sampling would incorrectly put the car off-road');
  ctx.bkcore.Timer=function(){this.time={elapsed:0};};
  compile('bkcore/hexgl/Gameplay.js',ctx);
  const game=new ctx.bkcore.hexgl.Gameplay({
    track:{spawn:{},spawnRotation:{},checkpoints:{list:[0,1,2,3],start:0,last:3}},
    analyser:collider,pixelRatio:1,
    shipControls:{dummy:{position:{x,z}}},cameraControls:{}
  });
  assert.equal(game.checkPoint(),0,
    'OSM checkpoints must sample exact world metres at diagonal road edges');
  collider.route.checkpoints=[];
  collider.boostPoints=[[50,50]];
  assert.equal(collider.getPixel(x,z).g,0,'same physical position is on boost pad');
  ctx.THREE={Vector3:function(px,py,pz){this.x=px;this.y=py;this.z=pz;}};
  ctx.bkcore.Audio={play(){},stop(){}};
  compile('bkcore/hexgl/ShipControls.js',ctx);
  const car={collisionMap:collider,collisionPixelRatio:1,
    dummy:{position:{x,z}},boosterDecay:0.01,boosterSpeed:0.5,
    boost:0,onBoostPad:false,nitro:0.5,nitroMax:1,movement:{z:0}};
  ctx.bkcore.hexgl.ShipControls.prototype.boosterCheck.call(car,1);
  assert.equal(car.onBoostPad,true,
    'OSM boost pad must sample exact world metres at diagonal road edges');
  assert.ok(car.boost>0 && car.nitro>0.5,'boost must actually activate');
}
console.log('PASS: moat collision, minimal resource manifest, materials and full fallback');
