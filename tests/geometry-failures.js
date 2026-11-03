// Legacy r50 JSONLoader does not complete on HTTP errors, empty JSON or stalled XHR.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const requests = [];
const timers = new Map();
let nextTimer = 1;
class FakeXHR {
  open(method, url) { this.url = url; }
  setRequestHeader() {}
  overrideMimeType() {}
  send() { requests.push(this); }
}
const context = {
  console, XMLHttpRequest: FakeXHR,
  setTimeout(fn) { const id=nextTimer++; timers.set(id,fn); return id; },
  clearTimeout(id) { timers.delete(id); },
  THREE: {
    Geometry: class { constructor() {this.faces=[];this.vertices=[];} computeTangents() {} },
    JSONLoader: class {
      createModel(json, callback) {
        if (json.invalid) throw Error('malformed geometry');
        callback({valid:json.valid,computeTangents() {}});
      }
      extractUrlBase() {return '.';} 
      load(url, callback) {requests.push({url,callback});}
    }
  },
  bkcore: {}
};
vm.runInNewContext(fs.readFileSync('bkcore/threejs/Loader.js','utf8'),context);
const ready=[], errors=[];
const loader=new context.bkcore.threejs.Loader({
  onLoad(){ready.push(1);},onError(name){errors.push(name);}
});
loader.load({geometries:{good:'good.js',missing:'missing.js',bad:'bad.js',stall:'stall.js'}});
assert.equal(requests.length,4);
function finish(url, status, body) {
  const req=requests.find(r=>r.url===url);
  req.status=status; req.responseText=body;
  req.readyState=4; req.DONE=4;
  req.onreadystatechange();
  return req;
}
finish('good.js',200,'{"valid":true}');
const missing=finish('missing.js',404,'not found');
finish('bad.js',200,'{"invalid":true}');
const stalled=requests.find(r=>r.url==='stall.js');
assert.ok(timers.size,'pending geometry must have a timeout');
[...timers.values()].forEach(fn=>fn());
assert.equal(loader.progress.loaded,4);
assert.equal(loader.progress.remaining,0);
assert.deepEqual(ready,[1]);
assert.deepEqual(errors,['missing','bad','stall']);
assert.equal(loader.get('geometries','good').valid,true);
for(const name of ['missing','bad','stall']) {
  const geom=loader.get('geometries',name);
  assert.ok(geom && typeof geom.computeTangents==='function',name+' fallback is safe for r50 createMesh');
}
missing.onerror();
stalled.status=200;stalled.responseText='{"valid":true}';stalled.onreadystatechange();
assert.equal(loader.progress.loaded,4,'late XHR cannot double-complete');
assert.deepEqual(ready,[1]);
console.log('PASS geometry: HTTP 404, invalid JSON model, timeout, late events, r50 fallback');
