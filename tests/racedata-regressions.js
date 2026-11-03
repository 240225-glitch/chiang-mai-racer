// Regression tests for legacy HexGL replay capture and interpolation.
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');

function Vector3(x=0,y=0,z=0){this.set(x,y,z);}
Vector3.prototype.set=function(x,y,z){this.x=x;this.y=y;this.z=z;return this;};
Vector3.prototype.copy=function(p){return this.set(p.x,p.y,p.z);};
Vector3.prototype.lerpSelf=function(p,t){
  return this.set(this.x+(p.x-this.x)*t,
                  this.y+(p.y-this.y)*t,
                  this.z+(p.z-this.z)*t);
};
function Quaternion(x=0,y=0,z=0,w=1){this.set(x,y,z,w);}
Quaternion.prototype.set=function(x,y,z,w){this.x=x;this.y=y;this.z=z;this.w=w;return this;};
Quaternion.prototype.copy=function(q){return this.set(q.x,q.y,q.z,q.w);};
Quaternion.prototype.normalize=function(){const n=Math.hypot(this.x,this.y,this.z,this.w);return this.set(this.x/n,this.y/n,this.z/n,this.w/n);};
Quaternion.prototype.slerpSelf=function(q,t){
  return this.set(this.x+(q.x-this.x)*t,
                  this.y+(q.y-this.y)*t,
                  this.z+(q.z-this.z)*t,
                  this.w+(q.w-this.w)*t);
};
const ctx={THREE:{Vector3,Quaternion},bkcore:{hexgl:{}},console};
vm.runInNewContext(fs.readFileSync('bkcore/hexgl/RaceData.js','utf8'),
                   ctx,{filename:'RaceData.js'});
const RaceData=ctx.bkcore.hexgl.RaceData;

let current=0,positions=[];
const ship={
  getPosition(){return {x:current,y:0,z:0};},
  getQuaternion(){return {x:0,y:0,z:0,w:1};},
  teleport(p,q){positions.push({x:p.x,qw:q.w});}
};
const recording=new RaceData('moat','timeattack',ship);
for(let i=0;i<10;i++){current=i;recording.tick(i*16);}
assert.equal(recording.rate,2,'capture interval must stay constant');
assert.equal(recording.rateState,1,'sampling counter should wrap');
assert.equal(recording.data.length,5,'one sample every two physics frames');
assert.deepEqual(Array.from(recording.data,r=>r[1]),[0,2,4,6,8]);
assert.equal(recording.last,4);

const playback=new RaceData('moat','replay',ship);
assert.equal(playback.applyInterpolated(0),false,'empty replay must not throw');
assert.equal(positions.length,0);
playback.import([[100,10,0,0,0,0,0,1]]);
assert.equal(playback.applyInterpolated(50),true);
assert.equal(positions.at(-1).x,10,'single sample clamps before start');
assert.equal(playback.applyInterpolated(200),true);
assert.equal(positions.at(-1).x,10,'single sample clamps after end');
playback.import([
  [100,10,0,0,0,0,0,1],
  [200,20,0,0,0,0,0,1],
  [300,30,0,0,0,0,0,1]
]);
playback.reset();
playback.applyInterpolated(50);
assert.equal(positions.at(-1).x,10,'before first frame clamps');
playback.applyInterpolated(150);
assert.equal(positions.at(-1).x,15,'interpolates between frames');
playback.applyInterpolated(250);
assert.equal(positions.at(-1).x,25,'interpolates later interval');
playback.applyInterpolated(1000);
assert.equal(positions.at(-1).x,30,'after last frame clamps');
assert.equal(playback.seek,playback.last);
// Replay seeking backwards (including a UI restart) must not leave the
// cursor pinned at the last frame and show the wrong car position.
playback.applyInterpolated(150);
assert.equal(positions.at(-1).x,15,
  'rewinding playback time must interpolate the earlier interval');
playback.applyInterpolated(50);
assert.equal(positions.at(-1).x,10,
  'rewinding before the first sample must clamp to the first position');
playback.import([
  [100,10,0,0,0,0,0,1],
  [100,20,0,0,0,0,0,1],
  [200,30,0,0,0,0,0,1]
]);
playback.reset();
for(const bad of [
  [], null, {}, [[0,0]], [[0,0,0,0,0,0,0,Infinity]],
  [[100,0,0,0,0,0,0,1],[99,0,0,0,0,0,0,1]]
]){
  assert.throws(()=>playback.import(bad),/Invalid|Non-finite|out of order/,
                'malformed or empty replay must be rejected');
}
playback.import([
  [100,10,0,0,0,0,0,1],
  [100,20,0,0,0,0,0,1],
  [200,30,0,0,0,0,0,1]
]);
playback.reset();
playback.applyInterpolated(150);
assert.ok(Number.isFinite(positions.at(-1).x),
          'duplicate timestamps must never produce NaN');
// Duplicate-timestamp replays must seek deterministically regardless of
// whether playback came from an earlier or later frame. The latest sample
// at an exact timestamp wins (a paused physics frame may update the pose).
playback.reset();
playback.applyInterpolated(100);
const duplicateFromForward=positions.at(-1).x;
playback.applyInterpolated(250);
playback.applyInterpolated(100);
assert.equal(positions.at(-1).x,duplicateFromForward,
  'duplicate timestamp result must not depend on previous seek direction');
assert.equal(duplicateFromForward,20,
  'the latest sample at a duplicate timestamp should be displayed');
const beforeInvalidTime=positions.length;
assert.equal(playback.applyInterpolated(NaN),false,
  'invalid playback time must not teleport a ship to NaN');
assert.equal(positions.length,beforeInvalidTime);
// Scrubbing a large recording should not scan tens of thousands of frames
// on the UI thread. Count array reads instead of using a flaky time limit.
const longFrames=Array.from({length:65536},(_,i)=>[i,i,0,0,0,0,0,1]);
const longPlayback=new RaceData('moat','replay',ship);
longPlayback.import(longFrames);
let frameReads=0;
const replayFrames=longPlayback.data;
longPlayback.data=new Proxy(replayFrames,{
  get(target,key){if(/^\d+$/.test(String(key)))frameReads++;return target[key];}
});
longPlayback.applyInterpolated(60000);
assert.ok(frameReads<100,
  'large forward replay seek should use logarithmic rather than linear reads');
frameReads=0;
longPlayback.applyInterpolated(10);
assert.ok(frameReads<100,
  'large backward replay seek should use logarithmic rather than linear reads');
// A damaged localStorage replay with a zero or over-length orientation
// must not reach the r50 quaternion slerp (acos(dot) becomes invalid).
for(const q of [[0,0,0,0],[0,0,0,2]]) {
  assert.throws(()=>playback.import([[100,0,0,0,...q]]),/quaternion/,
    'invalid quaternion must be rejected before playback');
}
assert.equal(playback.data.length,3,
  'failed import must preserve the last valid replay');
// Small finite rounding errors in legacy saved quaternions are allowed,
// but are normalized before slerp to keep dot products within [-1,1].
playback.import([[100,0,0,0,0,0,0,1.004],[200,1,0,0,0,0,0,1.004]]);
playback.applyInterpolated(150);
assert.ok(Math.abs(positions.at(-1).qw-1)<1e-10,
  'slightly rounded quaternions must be normalized during playback');

// A caller may retain its parsed localStorage array. Mutating it after
// import must not bypass the validation that protects r50 playback.
const untrustedFrames=[
  [100,10,0,0,0,0,0,1],
  [200,20,0,0,0,0,0,1]
];
playback.import(untrustedFrames);
untrustedFrames[0][1]=999;
untrustedFrames[1][7]=0;
untrustedFrames.push([300,30,0,0,0,0,0,1]);
playback.applyInterpolated(100);
assert.equal(positions.at(-1).x,10,
  'post-import source mutation must not change validated replay positions');
assert.equal(playback.data.length,2,
  'post-import source mutation must not alter validated frame count');
playback.applyInterpolated(150);
assert.ok(Number.isFinite(positions.at(-1).qw),
  'post-import source mutation must not corrupt replay orientation');

// A completed single-player race needs to persist a validated recording;
// otherwise Gameplay's replay mode has no recording to load on the next run.
const store={values:{},setItem(key,value){this.values[key]=value;}};
assert.equal(recording.save(store),true,'valid timeattack capture should be saved');
const replayKey='race-moat-replay';
assert.ok(store.values[replayKey],'recording must use the key replay mode reads');
const saved=JSON.parse(store.values[replayKey]);
assert.equal(saved.length,5);
const savedPlayback=new RaceData('moat','replay',ship);
savedPlayback.import(saved);
savedPlayback.applyInterpolated(32);
assert.equal(positions.at(-1).x,2,'persisted capture must be playable');
const previousSave=store.values[replayKey];
// Import accepts one-frame/zero-span data for safe interpolation, but
// saving such a capture must not replace a previously watchable race.
for (const unwatchable of [
  [[0,0,0,0,0,0,0,1]],
  [[100,0,0,0,0,0,0,1],[100,1,0,0,0,0,0,1]],
  [[-1,0,0,0,0,0,0,1],[100,1,0,0,0,0,0,1]]
]) {
  const candidate=new RaceData('moat','timeattack',ship);
  candidate.import(unwatchable);
  assert.equal(candidate.save(store),false,
    'unwatchable recording must not replace an existing replay');
  assert.equal(store.values[replayKey],previousSave,
    'failed save must preserve last watchable replay');
}
recording.data[0][7]=0; // simulate a damaged capture, do not erase good save
assert.equal(recording.save(store),false,'invalid capture must not overwrite a replay');
assert.equal(store.values[replayKey],previousSave);
assert.equal(new RaceData('moat','replay',ship).save(store),false,
  'playback must never overwrite a completed recording');
let quotaAttempted=false;
const quota={setItem(){quotaAttempted=true;throw new Error('QuotaExceededError');}};
const quotaRecording=new RaceData('moat','timeattack',ship);
quotaRecording.import([[0,0,0,0,0,0,0,1],[100,1,0,0,0,0,0,1]]);
assert.equal(quotaRecording.save(quota),false,
  'storage failures must not crash results');
assert.equal(quotaAttempted,true,'quota regression must reach storage.setItem');

console.log('PASS: replay downsampling, empty/single-frame, interpolation and end bounds');
