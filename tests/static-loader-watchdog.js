// A stalled road.json request must fall back even if the browser never
// dispatches XHR timeout/error/readyState. Run with Node, no browser needed.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const timers = new Map();
const requests = [];
let nextTimer = 1;
class XHR {
  constructor() { requests.push(this); }
  open() {}
  send() {}
}
const ctx = {
  THREE: {}, XMLHttpRequest: XHR,
  setTimeout(fn, ms) {
    assert.equal(ms, 30000);
    const id = nextTimer++;
    timers.set(id, fn);
    return id;
  },
  clearTimeout(id) { timers.delete(id); }
};
vm.runInNewContext(fs.readFileSync('bkcore/threejs/StaticModelLoader.js','utf8'), ctx);
const load = ctx.THREE.StaticModelLoader.load;
const failures = [];
load('assets/tracks/chiangmai-moat/road.json',
  () => assert.fail('stalled road must not succeed'), e => failures.push(e.message));
assert.equal(timers.size, 1, 'road loader needs an independent watchdog, not only xhr.timeout');
const hung = requests.at(-1);
for (const fn of [...timers.values()]) fn();
assert.equal(failures.length, 1, 'watchdog must trigger Cityscape fallback');
assert.match(failures[0], /timeout/);
assert.equal(timers.size, 0, 'watchdog must be cleared after failure');
hung.ontimeout(); hung.onerror(); hung.onabort();
hung.readyState = 4; hung.status = 200; hung.responseText = '{}'; hung.onreadystatechange();
assert.equal(failures.length, 1, 'late XHR events must not trigger another fallback');
let bad = 0;
load('road.json', () => assert.fail('invalid JSON must fail'), () => bad++);
const invalid = requests.at(-1);
invalid.readyState = 4; invalid.status = 200; invalid.responseText = 'not-json';
invalid.onreadystatechange();
assert.equal(bad, 1);
assert.equal(timers.size, 0, 'normal HTTP completion must clear watchdog');
let network = 0;
load('road.json', () => assert.fail('network error must fail'), () => network++);
requests.at(-1).onerror();
assert.equal(network, 1);
assert.equal(timers.size, 0, 'network failure must clear watchdog');
console.log('PASS static model watchdog: hung XHR fallback, late events, timer cleanup');
