// Node-only smoke tests for legacy browser scripts. No external dependencies.
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
function load(file, globals = {}) {
  const ctx = {
    // The legacy model loader now has an independent request watchdog.
    // These synchronous VM tests manually deliver XHR events; never leave
    // a real 30-second timer keeping the Node process alive.
    setTimeout() { return 1; }, clearTimeout() {},
    console, bkcore: { hexgl: {}, Timer: class {
      constructor() { this.time = { elapsed: 0 }; }
      start() { this.time.elapsed = 0; }
      getElapsedTime() { return this.time.elapsed; }
    } }, ...globals
  };
  vm.runInNewContext(fs.readFileSync(file, 'utf8'), ctx, {filename:file});
  return ctx;
}
function vector(x=0,y=0,z=0) { return {
  x,y,z,
  set(x,y,z) { this.x=x;this.y=y;this.z=z;return this; },
  copy(v) { return this.set(v.x,v.y,v.z); },
  addSelf(v) { return this.set(this.x+v.x,this.y+v.y,this.z+v.z); },
  subSelf(v) { return this.set(this.x-v.x,this.y-v.y,this.z-v.z); },
  lerpSelf(v,n) { return this.set(this.x+(v.x-this.x)*n,this.y+(v.y-this.y)*n,this.z+(v.z-this.z)*n); },
  isZero() { return this.x===0&&this.y===0&&this.z===0; },
  multiplyScalar(n) { return this.set(this.x*n,this.y*n,this.z*n); }
}; }
function Matrix() {}
Matrix.prototype.setPosition=Matrix.prototype.setRotationFromQuaternion=Matrix.prototype.identity=Matrix.prototype.rotateByAxis=Matrix.prototype.rotateAxis=function(){return this;};
function Quaternion() { this.x=0;this.y=0;this.z=0;this.w=1; }
Quaternion.prototype.set=function(x,y,z,w){this.x=x;this.y=y;this.z=z;this.w=w;return this;};
Quaternion.prototype.normalize=function(){
  const d=Math.hypot(this.x,this.y,this.z,this.w);
  this.x/=d;this.y/=d;this.z/=d;this.w/=d;return this;
};
Quaternion.prototype.multiplySelf=function(){return this;};
function Object3D() { this.position=vector();this.quaternion=new Quaternion();this.matrix=new Matrix();this.children=[]; }
Object3D.prototype.add=function(o){this.children.push(o);};
Object3D.prototype.translateX=function(x){this.position.x+=x;};
Object3D.prototype.translateY=function(y){this.position.y+=y;};
Object3D.prototype.translateZ=function(z){this.position.z+=z;};
const THREE = { Vector3:function(x,y,z){return vector(x,y,z);}, Quaternion, Object3D };

{
  const ctx=load('bkcore/hexgl/Gameplay.js');
  ctx.bkcore.hexgl.RaceData=function(){this.tick=function(){};};
  const track={name:'unit-track',checkpoints:{list:[0,1,2],start:0,last:2},spawn:{},spawnRotation:{}};
  for(const laps of [1,3,5]){
    const controls={reset(){},active:true,destroyed:false};
    const g=new ctx.bkcore.hexgl.Gameplay({track,shipControls:controls,cameraControls:{},maxLaps:laps});
    g.start();g.step=4;
    let cp=-1,t=0;g.checkPoint=()=>cp;
    function pass(id){cp=id;g.timer.time.elapsed=++t*1000;g.modes.timeattack.call(g);}
    pass(2);pass(0);
    assert.equal(g.lap,1,'cannot skip the first checkpoint');
    assert.equal(g.result,g.results.NONE);
    for(let i=0;i<laps;i++){
      pass(1);pass(2);pass(0);
      assert.equal(g.result,i===laps-1?g.results.FINISH:g.results.NONE);
    }
    assert.equal(g.lapTimes.length,laps);
  }
  const g=new ctx.bkcore.hexgl.Gameplay({track,shipControls:{reset(){}},cameraControls:{}});
  g.raceData={seek:2,last:2,applyInterpolated(){}};
  g.modes.replay.call(g);
  assert.equal(g.result,g.results.REPLAY);
}
{
  const ctx=load('bkcore/hexgl/CameraChase.js',{THREE});
  const chase=new ctx.bkcore.hexgl.CameraChase({camera:{},target:{},yoffset:4.5});
  assert.equal(chase.yoffset,4.5);
}
{
  const ctx=load('bkcore/hexgl/ShipControls.js',{THREE,document:{addEventListener(){}}});
  const c=new ctx.bkcore.hexgl.ShipControls({document:{addEventListener(){}},controlType:0,width:800});
  const ship={position:vector(),matrixAutoUpdate:true,matrix:new Matrix(),applyMatrix(){},updateMatrixWorld(){}};
  c.control(ship);
  assert.equal(ship.matrixAutoUpdate,false);
  const half=Math.SQRT1_2;
  c.reset(vector(830,4,0),{x:0,y:half,z:0,w:half});
  assert.ok(Math.abs(c.quaternion.y-half)<1e-8);
  assert.ok(Math.abs(c.quaternion.w-half)<1e-8,
    'GeoJSON spawn must preserve full quaternion w');
  c.reset(vector(830,4,0),{x:0,y:0,z:0});
  assert.equal(c.quaternion.w,1,'old Cityscape rotations must remain compatible');
  // A restart after a crash must not inherit turn momentum or a collision
  // repulsion impulse from the previous race. Both were left untouched by
  // reset(), making a fresh stationary car move/turn without player input.
  c.angular=0.25;
  c.repulsionForce.set(2,0,-1);
  c.repulsionAmount=1.5;
  c.currentVelocity.set(1,0,1);
  c.collision.front=true;
  c.collision.left=true;
  c.shieldDelay=0;
  c.gradient=0.4;
  c.tilt=-0.3;
  c.reset(vector(830,4,0),{x:0,y:0,z:0});
  assert.equal(c.angular,0,'restart clears smoothed steering');
  assert.equal(c.repulsionForce.isZero(),true,'restart clears crash impulse');
  assert.equal(c.repulsionAmount,0,'restart clears collision strength');
  assert.equal(c.currentVelocity.isZero(),true,'restart clears prior velocity');
  assert.equal(c.collision.front,false,'restart clears collision HUD flags');
  assert.equal(c.collision.left,false,'restart clears collision HUD flags');
  assert.equal(c.shieldDelay,60,'restart restores shield delay');
  assert.equal(c.gradient,0,'restart clears old track visual lean');
  assert.equal(c.tilt,0,'restart clears old track visual tilt');
  c.boosterCheck=c.nitroCheck=c.collisionCheck=c.heightCheck=()=>{};
  c.speed=5;c.key.backward=true;
  ctx.bkcore.Audio={setListenerPos(){},setListenerVelocity(){}};
  c.update(1);
  assert.ok(c.speed<4.97,'brake should decrease speed');
  // M2 countdown frames are rendered with controls inactive. A nitro
  // press or touch request during countdown must not be saved and fired
  // automatically when the race starts; require a new racing-time press.
  ctx.bkcore.Audio.play=()=>{};
  c.reset(vector(830,4,0),{x:0,y:0,z:0});
  c.collisionMap={projectInside(){}};
  c.active=false;
  c.key.nitro=true;
  c.triggerNitro();
  c.update(1);
  c.active=true;
  ctx.bkcore.hexgl.ShipControls.prototype.nitroCheck.call(c,1);
  assert.equal(c.nitroActive,0,
    'holding nitro from countdown must not auto-fire at race start');
  c.key.nitro=false;
  ctx.bkcore.hexgl.ShipControls.prototype.nitroCheck.call(c,1);
  c.key.nitro=true;
  ctx.bkcore.hexgl.ShipControls.prototype.nitroCheck.call(c,1);
  assert.ok(c.nitroActive>0,'a fresh press during the race still fires nitro');
  // A one-shot touch nitro request during countdown is also discarded,
  // even if no keyboard key is held when racing begins.
  c.reset(vector(830,4,0),{x:0,y:0,z:0});
  c.active=false;
  c.triggerNitro();
  c.update(1);
  c.active=true;
  ctx.bkcore.hexgl.ShipControls.prototype.nitroCheck.call(c,1);
  assert.equal(c.nitroActive,0,
    'a queued countdown touch nitro must not fire after the start');
}
// A slow frame (or a timeattack sample every few physics frames) can move
// from before a 12m checkpoint disc to beyond it. Endpoint-only sampling
// misses the gate and leaves the race stuck despite staying on the road.
{
  const ctx=load('bkcore/hexgl/Gameplay.js');
  vm.runInNewContext(fs.readFileSync('bkcore/hexgl/MoatCollision.js','utf8'),ctx);
  const route={closed:true,road_width_m:14,
    points:[[0,0],[100,0],[100,100],[0,100]],
    checkpoints:[{x:0,z:0},{x:50,z:0},{x:100,z:100},{x:0,z:100}]};
  const map=new ctx.bkcore.hexgl.MoatCollision.Collision(route);
  const ship={dummy:{position:{x:65,z:0}},collision:{front:false}};
  const gp=new ctx.bkcore.hexgl.Gameplay({
    track:{checkpoints:{list:[0,1,2,3],start:0,last:3}},
    shipControls:ship,analyser:map,pixelRatio:1});
  gp.nextCheckPointIndex=1;
  gp._lastCheckpointSample={x:35,z:0};
  assert.equal(map.getPixel(35,0).b,255);
  assert.equal(map.getPixel(65,0).b,255);
  assert.equal(gp.checkPoint(),1,'swept OSM gate must register between samples');
  assert.equal(gp.checkPoint(),-1,'stationary car cannot repeatedly sweep gate');
  // The straight chord cuts through the square's non-road interior.
  // A nearby gate on the far edge must not be credited as a shortcut.
  map.route.checkpoints[1]={x:100,z:50};
  gp._lastCheckpointSample={x:100,z:40};
  ship.dummy.position.x=0;ship.dummy.position.z=60;
  assert.equal(gp.checkPoint(),-1,'off-road shortcut cannot sweep a gate');
  // A teleport can also land *inside* the gate. The endpoint shortcut
  // previously bypassed the road sweep and awarded the next checkpoint.
  map.route.checkpoints[1]={x:50,z:0};
  gp._lastCheckpointSample={x:0,z:50};
  ship.dummy.position.x=50;ship.dummy.position.z=0;
  assert.equal(gp.checkPoint(),-1,
    'long diagonal jump across the city must not earn an endpoint gate');
  gp._lastCheckpointSample={x:20,z:0};
  assert.equal(gp.checkPoint(),1,
    'long but legal movement along the road must still earn the gate');
  // Two parallel road ribbons are separated by a 6m off-road gap.
  // A 6.2m jump (< old 24m guard) lands inside the next gate disc.
  // Neither endpoint is off-road, but the crossing must be rejected.
  const narrowRoute={closed:true,road_width_m:14,
    points:[[-100,0],[100,0],[100,20],[-100,20]],
    checkpoints:[{x:-50,z:0},{x:0,z:20},{x:50,z:20},{x:50,z:0}]};
  const narrowMap=new ctx.bkcore.hexgl.MoatCollision.Collision(narrowRoute);
  gp.analyser=narrowMap;
  gp._lastCheckpointSample={x:0,z:6.9};
  ship.dummy.position.x=0;ship.dummy.position.z=13.1;
  assert.equal(narrowMap.getPixel(0,6.9).b,255);
  assert.equal(narrowMap.getPixel(0,13.1).b,1);
  assert.equal(gp.checkPoint(),-1,
    'sub-24m crossing of a road gap cannot earn the next checkpoint');
  assert.equal(gp.checkPoint(),-1,
    'remaining at the rejected endpoint must not award the gate next tick');
  gp._lastCheckpointSample={x:0,z:14};
  assert.equal(gp.checkPoint(),1,'same-side short legal gate entry still works');
  // Crossing between streets before reaching a gate must not replace the
  // last trusted sample, even if that intermediate frame hits no gate.
  gp._lastCheckpointSample={x:40,z:6.9};
  ship.dummy.position.x=40;ship.dummy.position.z=13.1;
  assert.equal(gp.checkPoint(),-1,'intermediate off-road crossing rejected');
  assert.equal(gp._lastCheckpointSample.z,6.9,
    'rejected intermediate sample must not become the trusted origin');
  ship.dummy.position.x=0;
  assert.equal(gp.checkPoint(),-1,
    'gate reached after an invalid intermediate crossing stays blocked');
  ship.dummy.position.x=40;ship.dummy.position.z=6.9;
  assert.equal(gp.checkPoint(),-1,'return to the trusted road is safe');
  assert.equal(gp._lastCheckpointSample.z,6.9);
  gp.analyser=map;
  ctx.bkcore.hexgl.RaceData=function(){};
  ship.reset=function(){};
  gp.spawn={x:0,z:0};gp.spawnRotation={x:0,y:0,z:0,w:1};
  gp.start();
  assert.equal(gp._lastCheckpointSample.x,0,'restart resets swept gate origin');
  assert.equal(gp._lastCheckpointSample.z,0,'restart resets swept gate origin');
}
console.log('PASS: 1/3/5 laps, checkpoint order, replay, camera, brake, matrix');

// CC0 models attach to physics roots and preserve the original mesh on errors.
{
  const ctx=load('bkcore/hexgl/VehicleModels.js',{console:{warn(){}}});
  const carModels=ctx.bkcore.hexgl.VehicleModels;
  const urls=[];
  const models=[];
  const loader={load(url,success){urls.push(url); const model={position:{set(...p){this.coords=p;}},modelData:{bounds:{min:[-1,0,-2],max:[1,1,2]}}};models.push(model);success(model);}};
  const roots=[new Object3D(),new Object3D()];
  const ships=roots.map(ship=>({ship,legacy:{visible:true},
    booster:{visible:true},boosterSprite:{visible:true},boosterLight:{visible:true}}));
  const controls=[{heightBias:4,repulsionVScale:4},{heightBias:4,repulsionVScale:4}];
  const cameras=[{yoffset:8},{yoffset:8}];
  carModels.attachShips(ships,controls,cameras,true,'?car=kenney',loader);
  assert.equal(urls.length,2);
  assert.match(urls[0],/kenney-race-future/);
  assert.match(urls[1],/grab3d-race-car/);
  assert.equal(ships[0].legacy.visible,false);
  assert.equal(ships[1].legacy.visible,false);
  for(const ship of ships){
    assert.equal(ship.booster.visible,false);
    assert.equal(ship.boosterSprite.visible,false);
    assert.equal(ship.boosterLight.visible,false);
  }
  assert.deepEqual(models[0].position.coords,[0,-4,0]);
  assert.equal(controls[0].repulsionVScale,1.5);
  assert.equal(cameras[0].yoffset,4.5);
  const failed={ship:new Object3D(),legacy:{visible:true}};
  carModels.attachShips([failed],[{heightBias:4}],[{}],false,'',{
    load(url,success,error){error(new Error('offline'));}
  });
  assert.equal(failed.legacy.visible,true);
  assert.equal(failed.ship.children.length,0);
  const untouched={ship:new Object3D(),legacy:{visible:true}};
  carModels.attachShips([untouched],[{heightBias:4}],[{}],false,'?ship=1',{
    load(){throw new Error('should not load');}
  });
  assert.equal(untouched.legacy.visible,true);
}

// The converter uses #RRGGBB, while Three.js r50 Color accepts numeric hex only.
{
  function Color(hex) { this.hex=hex; }
  function Geometry() { this.vertices=[];this.faces=[];this.faceVertexUvs=[[]]; }
  Geometry.prototype.computeFaceNormals=Geometry.prototype.computeVertexNormals=
  Geometry.prototype.computeBoundingBox=Geometry.prototype.computeBoundingSphere=function(){};
  function Face3(a,b,c) { this.a=a;this.b=b;this.c=c;this.normal={}; }
  function Mesh(g,m){this.geometry=g;this.material=m;}
  function Material(params){this.params=params;}
  const three={...THREE,Color,Geometry,Face3,Mesh,MeshPhongMaterial:Material,NoColors:0,
    FrontSide:0,DoubleSide:2,ImageUtils:{loadTexture(url){return url;}}};
  const ctx=load('bkcore/threejs/StaticModelLoader.js',{THREE:three});
  const model=ctx.THREE.StaticModelLoader.build({
    format:'cmr-static-v1',name:'test',materials:[{color:'#c8322b',specular:'#123456'}],
    meshes:[{material:0,positions:[0,0,0,1,0,0,0,1,0],indices:[0,1,2]}]
  });
  // Numbers only: r50's Color.set() zeroes a Color instance passed through
  // MeshPhongMaterial parameters, which made every imported material black.
  assert.equal(model.children[0].material.params.color,0xc8322b);
  assert.equal(model.children[0].material.params.specular,0x123456);
  assert.equal(model.children[0].material.params.ambient,0x222222);
}
console.log('PASS: CC0 vehicle loading/fallback and r50 material colors');

// Reject corrupted / oversized externally generated model assets before
// Three.js r50 receives Face3 indices or non-finite vertices. Such meshes
// previously passed build() and could fail later during WebGL rendering.
{
  function Color(hex) { this.hex=hex;this.setRGB=function(){}; }
  function Geometry() { this.vertices=[];this.faces=[];this.faceVertexUvs=[[]]; }
  Geometry.prototype.computeFaceNormals=Geometry.prototype.computeVertexNormals=
  Geometry.prototype.computeBoundingBox=Geometry.prototype.computeBoundingSphere=function(){};
  function Face3(a,b,c) { this.a=a;this.b=b;this.c=c;this.normal={}; }
  function Mesh(g,m){this.geometry=g;this.material=m;this.position=vector();}
  const three={...THREE,Color,Geometry,Face3,Mesh,
    MeshPhongMaterial:function(){},NoColors:0,FrontSide:0,DoubleSide:2,
    ImageUtils:{loadTexture(){return {};}}};
  const ctx=load('bkcore/threejs/StaticModelLoader.js',{THREE:three});
  const make=(changes={})=>({
    format:'cmr-static-v1',name:'test',materials:[{color:'#ffffff'}],
    meshes:[Object.assign({material:0,positions:[0,0,0,1,0,0,0,1,0],
                           indices:[0,1,2]},changes)]
  });
  assert.equal(ctx.THREE.StaticModelLoader.build(make()).children.length,1);
  const chunk=ctx.THREE.StaticModelLoader.build(make({offset:[800,0,-450]})).children[0];
  assert.deepEqual([chunk.position.x,chunk.position.y,chunk.position.z],
                   [800,0,-450], 'r50 chunk offset must restore world position');
  for(const bad of [
    {offset:[0,0]},
    {offset:[0,NaN,0]},
    {offset:[0,'5',0]},
    {indices:[0,1,9]},
    {indices:[0,1,-1]},
    {indices:[0,1,1.5]},
    {indices:[0,1]},
    {positions:[0,0,0,Infinity,0,0,0,1,0]},
    {positions:[0,0,0,1,0,0,0,1]},
    {uvs:[0,0,1,0]},
    {normals:[0,1,0]},
    {colors:[0,0,1]}
  ]) {
    assert.throws(()=>ctx.THREE.StaticModelLoader.build(make(bad)),
      /StaticModelLoader/,JSON.stringify(bad));
  }
  assert.throws(()=>ctx.THREE.StaticModelLoader.build({...make(),materials:[]}),
    /StaticModelLoader/);
  assert.throws(()=>ctx.THREE.StaticModelLoader.build(make({material:5})),
    /StaticModelLoader/);
  // Each mesh may satisfy the 1.2M-index limit while the combined
  // model allocates unbounded Face3 objects. Two 1.05M-index meshes
  // would otherwise create 700,000 faces with only six vertices.
  const manyFaces=Array(1050000).fill(0);
  const faceBomb=make();
  faceBomb.meshes=[
    {...faceBomb.meshes[0],indices:manyFaces},
    {...faceBomb.meshes[0],indices:manyFaces}
  ];
  assert.throws(()=>ctx.THREE.StaticModelLoader.build(faceBomb),
    /model face index limit exceeded/);
  // Local file:// XHR responses use status=0. A valid model must still load,
  // and a later duplicate readyState event must not invoke callbacks twice.
  let xhr;
  ctx.XMLHttpRequest=class {
    constructor(){xhr=this;}
    open(){}
    send(){}
  };
  let successes=0, failures=0;
  ctx.THREE.StaticModelLoader.load('file-model.json',()=>successes++,()=>failures++);
  xhr.readyState=4;xhr.status=0;xhr.responseText=JSON.stringify(make());
  xhr.onreadystatechange();xhr.onreadystatechange();
  assert.equal(successes,1);
  assert.equal(failures,0);
  // A syntactically valid 200-OK asset over the aggregate face budget
  // must call onError once, allowing the track's Cityscape fallback.
  let oversizedFailures=0;
  ctx.THREE.StaticModelLoader.load('oversized-road.json',
    ()=>{throw Error('oversized road must not render');},
    ()=>oversizedFailures++);
  xhr.readyState=4;xhr.status=200;
  xhr.responseText=JSON.stringify(faceBomb);
  xhr.onreadystatechange();xhr.onreadystatechange();
  assert.equal(oversizedFailures,1);
  console.log('PASS: malformed/oversized r50 geometry rejected; local status=0 loads once');
}

// A stalled road.json request must fail instead of leaving the loading
// screen indefinitely. XHR network/timeout/abort signals can overlap with
// readyState=4, so a fallback must be invoked exactly once.
{
  const pending=[];
  class FakeXHR {
    constructor(){pending.push(this);this.readyState=1;this.status=0;this.responseText='';}
    open(){}
    send(){if(FakeXHR.throwOnSend) throw Error('send blocked');}
  }
  const ctx=load('bkcore/threejs/StaticModelLoader.js',{
    THREE:{},XMLHttpRequest:FakeXHR
  });
  const loadModel=ctx.THREE.StaticModelLoader.load;
  for(const failure of ['ontimeout','onerror','onabort']) {
    let calls=0;
    loadModel('assets/tracks/chiangmai-moat/road.json',()=>{throw Error('unexpected success');},
      error=>{assert.ok(error instanceof Error || error.message);calls++;});
    const xhr=pending[pending.length-1];
    assert.ok(xhr.timeout>0,'road loading needs a finite XHR timeout');
    assert.equal(typeof xhr[failure],'function',failure+' handler missing');
    xhr[failure]();
    xhr.readyState=4;xhr.status=0;xhr.onreadystatechange();
    assert.equal(calls,1,failure+' should trigger only one fallback');
  }
  let httpFailures=0;
  loadModel('road.json',()=>{throw Error('unexpected success');},()=>httpFailures++);
  const http=pending[pending.length-1];
  http.readyState=4;http.status=404;http.onreadystatechange();
  http.onerror();
  assert.equal(httpFailures,1,'HTTP and network failure signals must not double-fallback');
  FakeXHR.throwOnSend=true;
  let sendFailures=0;
  loadModel('road.json',()=>{throw Error('unexpected success');},()=>sendFailures++);
  assert.equal(sendFailures,1,'synchronous XHR send failures must trigger fallback');
  console.log('PASS: road model XHR timeout/network/abort/HTTP/send fallback is one-shot');
}
