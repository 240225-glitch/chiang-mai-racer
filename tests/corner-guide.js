// M3 optional corner guidance: direction, wraparound, state and fallbacks.
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const ctx={bkcore:{hexgl:{}}};
vm.runInNewContext(fs.readFileSync('assets/tracks/chiangmai-moat/route-data.js','utf8'),ctx);
vm.runInNewContext(fs.readFileSync('bkcore/hexgl/CornerGuide.js','utf8'),ctx);
const Guide=ctx.bkcore.hexgl.CornerGuide;
const route=ctx.bkcore.hexgl.MoatRouteData;
const elements=[{style:{display:'none'},textContent:''},{style:{display:'none'},textContent:''}];
const guide=new Guide(route,elements);
assert.equal(guide.turns.length,2,'OSM prototype should have two merged warning clusters');
assert.ok(guide.turns.some(t=>t.index===400),'first acute bend');
assert.ok(guide.turns.some(t=>t.index===566),'second acute bend');
function runAt(i,player=0,active=true,step=4) {
  const p=route.points[i];
  const controls=[null,null],games=[null,null];
  controls[player]={dummy:{position:{x:p[0],z:p[1]}},active};
  games[player]={active:true,step};
  guide.tick=5;
  guide.update(controls,games);
  return elements[player];
}
assert.match(runAt(390).textContent,/急弯向[左右] · [0-9]+ 米/);
assert.equal(elements[0].style.display,'block');
assert.equal(runAt(370).style.display,'none','no alert >150m ahead');
assert.equal(runAt(408).style.display,'none','past bend should clear warning');
assert.equal(runAt(555,1).style.display,'block','P2 independent guidance');
assert.equal(elements[0].style.display,'none','inactive P1 cleared');
assert.equal(runAt(555,1,false).style.display,'none','inactive car never warned');
assert.equal(runAt(555,1,true,3).style.display,'none','countdown never warned');
guide.reset();
assert.equal(elements[1].style.display,'none','restart hides warnings');
assert.equal(guide.lastIndices[0],-1,'restart clears route tracking');
// Synthetic four-corner course: warnings must wrap across route point 0.
const square={points:[[0,0],[100,0],[100,100],[0,100]]};
const synth=new Guide(square,[{style:{},textContent:''}]);
assert.ok(synth.warningAt(3),'turn at index 0 is ahead across the lap seam');
assert.equal(synth.warningAt(3).side,'右','from -Z to +X is a right turn in r50 +Y-up coordinates');
const reverse=new Guide({points:[[0,0],[0,100],[100,100],[100,0]]},[{style:{},textContent:''}]);
assert.equal(reverse.warningAt(3).side,'左','from -X to +Z is a left turn in r50 +Y-up coordinates');
assert.equal(synth.warningAt(-1),null,'off-route position hides guidance');

// Two nearby parallel roads: after a position discontinuity, the previous
// 12-point search window must not pin guidance to the wrong road. Real OSM
// routes are resampled at ~10m; both sides here are 12m apart.
const parallel=[];
for (let x=0;x<=200;x+=10) parallel.push([x,0]);
for (let x=200;x>=0;x-=10) parallel.push([x,12]);
const nearGuide=new Guide({points:parallel},[{style:{},textContent:''}]);
assert.equal(nearGuide.nearestIndex(100,0,0),10);
assert.equal(nearGuide.nearestIndex(100,12,0),parallel.length-11,
  'nearby parallel lane should reacquire the exact route point, not stay on old lane');
// A closer road only 8m away remains inside the 11m local acceptance
// radius. The old cache must not hide a strictly closer route point.
const tight=[];
for (let x=0;x<=200;x+=10) tight.push([x,0]);
for (let x=200;x>=0;x-=10) tight.push([x,8]);
const tightGuide=new Guide({points:tight},[{style:{},textContent:''}]);
assert.equal(tightGuide.nearestIndex(100,0,0),10);
assert.equal(tightGuide.nearestIndex(100,8,0),tight.length-11,
  'nearest road must win even if previous road is within tolerance');
assert.equal(tightGuide.nearestIndex(100,4,0),tight.length-11,
  'exact midpoint tie should keep the previous road to avoid flicker');
assert.equal(nearGuide.nearestIndex(100,30,0),-1,
  'far outside the 14m road should not retain a misleading turn warning');
assert.notEqual(nearGuide.nearestIndex(105,7,1),-1,
  'on-road edge between 10m samples must remain valid for P2');

// A car on the first road between samples is closer to a *sample* on
// the second road, but the first road's segment is exactly beneath it.
const offsetRoad=[[0,0],[10,0],[20,0],[20,4],[15,4],[5,4],[0,4]];
const offsetGuide=new Guide({points:offsetRoad},[{style:{},textContent:''}]);
assert.equal(offsetGuide.nearestIndex(5,0,0),0,
  'continuous segment projection must win over a nearer sample on another road');
assert.equal(offsetGuide.nearestIndex(5,4,0),5,
  'moving onto adjacent road should reacquire its segment');
assert.equal(offsetGuide.nearestIndex(5,2,0),5,
  'equal-distance roads should preserve the previous segment');
// A long but valid centreline segment must not be classified as off-road
// merely because the nearest endpoint is tens of metres away.
const longGuide=new Guide(square,[{style:{},textContent:''}]);
assert.equal(longGuide.nearestIndex(50,0,0),0);
assert.equal(longGuide.locate(50,0,0).t,0.5);
assert.equal(longGuide.warningAt(0,0.5).distance,50,
  'warning distance should reflect the car position between samples');
assert.equal(longGuide.nearestIndex(50,20,0),-1,
  'segment projection must still reject positions outside road tolerance');

// Driving against the OSM route must not show a misleading turn direction.
// On the +X segment, yaw +90deg faces forward and -90deg faces backwards.
const wrongWayEl={style:{display:'none'},textContent:''};
const wrongWayGuide=new Guide(square,[wrongWayEl]);
function warningFacing(yaw) {
  wrongWayGuide.tick=5;
  wrongWayGuide.update([{
    dummy:{position:{x:50,z:0},quaternion:{x:0,y:Math.sin(yaw/2),z:0,w:Math.cos(yaw/2)}},
    active:true
  }],[{active:true,step:4}]);
  return wrongWayEl.style.display;
}
assert.equal(warningFacing(Math.PI/2),'block','forward heading keeps corner warning');
assert.equal(warningFacing(-Math.PI/2),'none',
  'reverse heading must not display a misleading clockwise corner warning');
assert.equal(warningFacing(Math.PI/2),'block','warning resumes when heading recovers');
assert.equal(warningFacing(0),'block','perpendicular cornering must not flicker as wrong-way');

// Spatial index must never drop a road segment inside the acceptance
// radius. Compare exact projected distance with a full segment scan at
// deterministic on-road, shoulder and off-road OSM positions.
function projectedDistanceSquared(seg,x,z) {
  const t=Math.max(0,Math.min(1,
    ((x-seg.x)*seg.vx+(z-seg.z)*seg.vz)*seg.invLen2));
  const dx=x-seg.x-t*seg.vx,dz=z-seg.z-t*seg.vz;
  return dx*dx+dz*dz;
}
for (let k=0;k<250;k++) {
  const p=route.points[(k*37)%route.points.length];
  const x=p[0]+((k%11)-5)*2.5,z=p[1]+((k%13)-6)*2.5;
  const expected=Math.min(...guide.segments.map(s=>projectedDistanceSquared(s,x,z)));
  const found=guide.locate(x,z,0);
  if (expected>guide.maxSampleDistanceSquared+1e-7) {
    assert.equal(found,null,'off-road indexed search must hide warnings');
  } else {
    assert.ok(found,'indexed search must find a segment inside road tolerance');
    assert.ok(Math.abs(projectedDistanceSquared(guide.segments[found.index],x,z)-expected)<1e-7,
      'indexed projection must match exhaustive nearest segment');
  }
}

assert.throws(()=>new Guide({points:[[0,0],[0,0],[1,0]]}),/invalid segment/);
console.log('PASS: opt-in M3 corner guide OSM bends, two-player, countdown, restart and lap seam');
