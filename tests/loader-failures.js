// Regression: optional visual assets failing HTTP must not strand WebGL startup.
// Run with: node tests/loader-failures.js
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const callbacks = {};
const timers = new Map();
let nextTimer = 1;
const failures = [];
const loaded = [];
const ctx = {
  console,
  setTimeout(fn) { const id=nextTimer++; timers.set(id,fn); return id; },
  clearTimeout(id) { timers.delete(id); },
  document: {createElement(tag) {
    assert.equal(tag, 'canvas');
    return {tagName:'CANVAS',width:0,height:0,
      getContext(){return {fillRect(){}};}};
  }},
  Image: class {
    constructor(){this.width=0;this.height=0;}
    set src(url){callbacks[url] = this;}
  },
  THREE: {
    JSONLoader: class {},
    ImageUtils: {loadTexture(url, mapping, success, error) {
      const texture = {image:null,needsUpdate:false};
      callbacks[url] = {success,error,texture};
      return texture;
    }}
  },
  bkcore: {}
};
vm.runInNewContext(fs.readFileSync('bkcore/threejs/Loader.js','utf8'),ctx);
const loader = new ctx.bkcore.threejs.Loader({
  onLoad(){loaded.push('ready');},
  onError(name){failures.push(name);}
});
loader.load({textures:{hex:'textures/hud/hex.jpg'},images:{'hud.bg':'textures/hud/hud-bg.png'}});
assert.equal(loader.progress.total,2);
callbacks['textures/hud/hex.jpg'].error('404');
callbacks['textures/hud/hud-bg.png'].onerror();
assert.deepEqual(failures,['hex','hud.bg']);
assert.equal(loader.progress.loaded,2,'failed optional visual assets must complete the loader');
assert.equal(loader.progress.remaining,0);
assert.deepEqual(loaded,['ready'],'the game must boot once');
assert.equal(timers.size,0,'completed optional images must cancel watchdogs');
assert.equal(loader.get('textures','hex').needsUpdate,true,'missing texture gets a GPU-safe fallback');
assert.ok(loader.get('textures','hex').image,'fallback texture has pixels');
assert.equal(loader.get('images','hud.bg').tagName,'CANVAS','HUD drawImage needs a drawable fallback');
assert.equal(loader.get('images','hud.bg').width / loader.get('images','hud.bg').height,1920/250,
  'HUD fallback keeps original aspect ratio');
// Browser events can be duplicated or race with load completion. Never
// count an already completed resource twice or trigger onLoad twice.
callbacks['textures/hud/hex.jpg'].error('404 again');
callbacks['textures/hud/hud-bg.png'].onerror();
assert.equal(loader.progress.loaded,2);
assert.deepEqual(loaded,['ready']);
// Normal success remains unchanged and should not be counted twice either.
const normal = [];
const loader2 = new ctx.bkcore.threejs.Loader({onLoad(){normal.push('ready');}});
loader2.load({textures:{good:'ok.png'},images:{'hud.speed':'ok-hud.png'}});
callbacks['ok.png'].success(callbacks['ok.png'].texture);
callbacks['ok-hud.png'].onload();
assert.equal(loader2.progress.loaded,2);
assert.deepEqual(normal,['ready']);
callbacks['ok.png'].success(callbacks['ok.png'].texture);
assert.equal(loader2.progress.loaded,2);
assert.deepEqual(normal,['ready']);
assert.equal(timers.size,0,'successful optional images must cancel watchdogs');
// Requests may hang forever without firing either onload or onerror.
const hanging=[];
const loader3 = new ctx.bkcore.threejs.Loader({
  onLoad(){hanging.push('ready');}, onError(name){hanging.push(name);} });
loader3.load({textures:{stalled:'stalled.png'},images:{'hud.stalled':'stalled-hud.png'}});
assert.equal(timers.size,2,'both optional image paths need a 15s watchdog');
for (const fn of [...timers.values()]) fn();
assert.deepEqual(hanging,['stalled','hud.stalled','ready']);
assert.equal(loader3.progress.loaded,2);
assert.equal(loader3.get('textures','stalled').needsUpdate,true);
assert.equal(loader3.get('images','hud.stalled').tagName,'CANVAS');
callbacks['stalled.png'].success(callbacks['stalled.png'].texture);
callbacks['stalled-hud.png'].onload();
callbacks['stalled.png'].error('late 404');
callbacks['stalled-hud.png'].onerror();
assert.equal(loader3.progress.loaded,2,'late success/error must not double count');
assert.deepEqual(hanging,['stalled','hud.stalled','ready']);
assert.equal(timers.size,0,'timeout watchdogs must be cleared');
console.log('PASS loader: texture/HUD 404 and timeout fallback, exact progress, late events');
