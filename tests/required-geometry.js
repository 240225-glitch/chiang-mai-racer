// A missing Cityscape road is not an optional prop: it must fail closed.
// Run: node tests/required-geometry.js
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const requests = [];
const timers = new Map();
let nextTimer = 1;
class FakeXHR {
  open(method, url) { this.url = url; }
  overrideMimeType() {}
  send() { requests.push(this); }
}
const ctx = {
  console, XMLHttpRequest: FakeXHR,
  setTimeout(fn) { const id = nextTimer++; timers.set(id, fn); return id; },
  clearTimeout(id) { timers.delete(id); },
  THREE: {
    Geometry: class { constructor() { this.faces=[]; this.vertices=[]; } },
    JSONLoader: class {
      createModel(json, done) {
        if (json.throw) throw new Error('bad model');
        done({faces: json.empty ? [] : [{}],
          vertices: json.empty ? [] : [{}, {}, {}], computeTangents() {}});
      }
      extractUrlBase() { return '.'; }
    }
  },
  bkcore: {}
};
vm.runInNewContext(fs.readFileSync('bkcore/threejs/Loader.js','utf8'), ctx);
function setup() {
  const ready=[], fatal=[], errors=[];
  const loader = new ctx.bkcore.threejs.Loader({
    onLoad() { ready.push('ready'); },
    onFatal(name) { fatal.push(name); },
    onError(name) { errors.push(name); }
  });
  loader.load({
    requiredGeometries: {'track.cityscape': true},
    geometries: {'track.cityscape': 'road.js', booster: 'booster.js'}
  });
  return {loader,ready,fatal,errors};
}
function complete(url, status, body) {
  const request = requests.filter(req=>req.url===url).at(-1);
  assert.ok(request, 'request ' + url);
  request.status = status;
  request.responseText = body;
  request.readyState = 4;
  request.onreadystatechange();
  return request;
}

const missing = setup();
const lateRoad = complete('road.js',404,'not found');
complete('booster.js',200,'{"empty":false}');
assert.deepEqual(missing.fatal,['track.cityscape'],
  'missing core road must stop the race');
assert.deepEqual(missing.ready,[], 'do not launch without a road mesh');
assert.equal(missing.loader.progress.failed,true);
assert.equal(missing.loader.progress.loaded,2,'drain resource progress for diagnostics');
assert.deepEqual(Array.from(missing.loader.progress.failures),['track.cityscape']);
lateRoad.onerror();
assert.deepEqual(missing.fatal,['track.cityscape'],'late events must not duplicate fatal UI');

const empty = setup();
complete('road.js',200,'{"empty":true}');
complete('booster.js',200,'{"empty":false}');
assert.deepEqual(empty.fatal,['track.cityscape'],'empty core road is unusable');
assert.deepEqual(empty.ready,[]);

const timedOut = setup();
complete('booster.js',200,'{"empty":false}');
assert.equal(timers.size,1,'required road request must have a watchdog');
for (const fn of [...timers.values()]) fn();
assert.deepEqual(timedOut.fatal,['track.cityscape'],'stalled road must fail closed');
assert.deepEqual(timedOut.ready,[]);
assert.equal(timedOut.loader.progress.loaded,2);

const optional = setup();
complete('road.js',200,'{"empty":false}');
complete('booster.js',404,'not found');
assert.deepEqual(optional.ready,['ready'],'optional booster failure may degrade');
assert.deepEqual(optional.fatal,[]);
assert.equal(optional.loader.get('geometries','booster').faces.length,0);

const good = setup();
complete('road.js',200,'{"empty":false}');
complete('booster.js',200,'{"empty":false}');
assert.deepEqual(good.ready,['ready']);
assert.deepEqual(good.fatal,[]);
assert.equal(timers.size,0,'all geometry watchdogs cleared');
// Both legacy quality manifests must actually opt into the safety rule.
const manifests = [];
const trackContext = {bkcore: {hexgl: {tracks: {}}, threejs: {
  Loader: class { load(manifest) { manifests.push(manifest); } }
}}};
vm.runInNewContext(fs.readFileSync('bkcore/hexgl/tracks/Cityscape.js','utf8'), trackContext);
const track = trackContext.bkcore.hexgl.tracks.Cityscape;
track.load({},0);
track.load({},3);
assert.equal(manifests.length,2);
for (const manifest of manifests) {
  assert.equal(manifest.requiredGeometries['track.cityscape'],true,
    'Cityscape must mark its road required in both quality modes');
  assert.equal(manifest.geometries['track.cityscape'],
    'geometries/tracks/cityscape/track.js');
}
console.log('PASS required geometry: missing/empty/stalled road fails closed, optional fallback and both quality manifests');
