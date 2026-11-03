const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

// The analyser is a *physics* dependency, unlike optional HUD or music.
// Missing/tainted/timeout images must never start Cityscape without collision.
const images = [];
const timers = new Map();
let nextTimer = 1;
let tainted = false;
let shortPixels = false;
class FakeImage {
  constructor() { this.width = 8; this.height = 8; images.push(this); }
  set src(value) { this.url = value; }
}
const context = {
  console, Image: FakeImage,
  setTimeout(fn) { const id=nextTimer++; timers.set(id,fn); return id; },
  clearTimeout(id) { timers.delete(id); },
  document: { createElement(tag) {
    assert.equal(tag,'canvas');
    return {width:0,height:0,getContext() {
      return {
        drawImage() {},
        getImageData(x,y,w,h) {
          if (tainted) throw new Error('SecurityError: tainted canvas');
          return {width:w,height:h,data:new Uint8ClampedArray(shortPixels ? 1 : w*h*4)};
        }
      };
    }};
  }},
  THREE: {JSONLoader: class {}}, bkcore: {}
};
vm.runInNewContext(fs.readFileSync('bkcore.coffee/ImageData.js','utf8'),context);
vm.runInNewContext(fs.readFileSync('bkcore/threejs/Loader.js','utf8'),context);

function makeLoader() {
  const ready=[], errors=[], fatal=[];
  const loader=new context.bkcore.threejs.Loader({
    onLoad(){ready.push(1);},
    onError(name){errors.push(name);},
    onFatal(name){fatal.push(name);}
  });
  loader.load({analysers:{
    'track.cityscape.collision':'collision.png',
    'track.cityscape.height':'height.png'
  }});
  return {loader,ready,errors,fatal};
}
function byUrl(url) { return images.filter(im=>im.url===url).at(-1); }

const ok=makeLoader();
byUrl('collision.png').onload();
byUrl('height.png').onload();
assert.deepEqual(ok.ready,[1]);
assert.equal(ok.loader.get('analysers','track.cityscape.collision').loaded,true);
assert.equal(ok.loader.progress.failed,false);
assert.equal(ok.loader.progress.loaded,2);
assert.equal(timers.size,0,'success clears image watchdogs');

const broken=makeLoader();
const missing=byUrl('collision.png');
assert.equal(typeof missing.onerror,'function','missing collision image needs onerror');
missing.onerror();
byUrl('height.png').onload();
assert.deepEqual(broken.errors,['track.cityscape.collision']);
assert.deepEqual(broken.fatal,['track.cityscape.collision']);
assert.deepEqual(broken.ready,[],'fatal collision must never start game');
assert.equal(broken.loader.progress.failed,true);
assert.equal(broken.loader.progress.loaded,2);
assert.equal(broken.loader.get('analysers','track.cityscape.collision').loaded,false);
missing.onload();
missing.onerror();
assert.deepEqual(broken.fatal,['track.cityscape.collision'],'late image events ignored');

const stalled=makeLoader();
byUrl('collision.png').onload();
assert.ok(timers.size,'pending height analyser has watchdog');
[...timers.values()].forEach(fn=>fn());
assert.deepEqual(stalled.ready,[]);
assert.deepEqual(stalled.fatal,['track.cityscape.height']);
assert.equal(stalled.loader.progress.loaded,2);
byUrl('height.png').onload();
assert.deepEqual(stalled.fatal,['track.cityscape.height']);

tainted=true;
const unsafe=makeLoader();
byUrl('collision.png').onload();
tainted=false;
byUrl('height.png').onload();
assert.deepEqual(unsafe.ready,[]);
assert.deepEqual(unsafe.fatal,['track.cityscape.collision'],'tainted canvas must fail closed');
assert.equal(unsafe.loader.get('analysers','track.cityscape.collision').loaded,false);
assert.equal(timers.size,0);

shortPixels=true;
const truncated=makeLoader();
byUrl('collision.png').onload();
shortPixels=false;
byUrl('height.png').onload();
assert.deepEqual(truncated.ready,[]);
assert.deepEqual(truncated.fatal,['track.cityscape.collision'],
  'incomplete pixel buffers must not enter the physics engine');
console.log('PASS analysers: success, 404, timeout, tainted/short pixels, fatal startup, late events');
