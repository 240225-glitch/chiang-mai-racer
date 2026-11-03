// Regression: an optional audio failure must not strand WebGL startup.
// Run with: node tests/audio-regressions.js
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

function makeAudioHarness(webAudio = true) {
  const requests = [], timers = new Map(), warnings = [];
  let nextTimer = 1, decodeFails = false;
  class FakeXHR {
    open(method, url) { this.url = url; }
    send() { requests.push(this); }
  }
  class FakeAudio {
    constructor() { this.handlers = {}; this.currentTime = 0; }
    addEventListener(event, cb) { this.handlers[event] = cb; }
    pause() {}
    play() { if (this.failed) throw new Error('failed audio played'); }
  }
  class FakeContext {
    constructor() { this.destination = {}; }
    createPanner() { return {connect() {}}; }
    createGain() { return {gain: {value: 0}, connect() {}}; }
    createBufferSource() {
      return {connect() {}, start() {}, stop() {}};
    }
    decodeAudioData(data, success, failure) {
      if (decodeFails) failure(new Error('bad codec'));
      else success({decoded: true});
    }
  }
  const sandbox = {
    bkcore: {}, window: webAudio ? {AudioContext: FakeContext} : {},
    XMLHttpRequest: FakeXHR, Audio: FakeAudio,
    console: {warn(...args) { warnings.push(args.join(' ')); }, error() {}},
    setTimeout(cb) { const id = nextTimer++; timers.set(id, cb); return id; },
    clearTimeout(id) { timers.delete(id); }
  };
  vm.runInNewContext(fs.readFileSync('bkcore/Audio.js', 'utf8'), sandbox);
  return {
    audio: sandbox.bkcore.Audio, requests, timers, warnings,
    setDecodeFails(value) { decodeFails = value; },
    failTimer() { const cb = [...timers.values()][0]; assert.ok(cb); cb(); }
  };
}

{
  const h = makeAudioHarness();
  let callbacks = 0;
  h.audio.addSound('audio/missing.ogg', 'bg', true, () => { callbacks++; });
  const req = h.requests[0];
  req.status = 404;
  req.onload();
  assert.equal(callbacks, 1, 'HTTP 404 must finish the optional audio load');
  assert.equal(h.audio.sounds.bg.failed, true);
  assert.doesNotThrow(() => {
    h.audio.play('bg');
    h.audio.stop('bg');
    h.audio.volume('bg', 0.3);
  }, 'silent audio must not crash game lifecycle');
  if (typeof req.onerror === 'function') req.onerror();
  assert.equal(callbacks, 1, 'late duplicate events must not complete twice');
}
{
  const h = makeAudioHarness();
  h.setDecodeFails(true);
  let callbacks = 0;
  h.audio.addSound('audio/bad.ogg', 'crash', false, () => { callbacks++; });
  const req = h.requests[0];
  req.status = 200;
  req.response = new ArrayBuffer(8);
  req.onload();
  assert.equal(callbacks, 1, 'decode failure must not hang startup');
  assert.equal(h.audio.sounds.crash.failed, true);
  assert.doesNotThrow(() => h.audio.play('crash'));
}
{
  const h = makeAudioHarness();
  let callbacks = 0;
  h.audio.addSound('audio/stalled.ogg', 'wind', true, () => { callbacks++; });
  h.failTimer();
  assert.equal(callbacks, 1, 'watchdog must settle stalled audio');
  assert.equal(h.audio.sounds.wind.failed, true);
  const req = h.requests[0];
  req.status = 200;
  req.response = new ArrayBuffer(8);
  req.onload();
  assert.equal(callbacks, 1, 'late successful decode must not re-complete');
}
{
  const h = makeAudioHarness();
  let callbacks = 0;
  h.audio.addSound('audio/good.ogg', 'boost', false, () => { callbacks++; });
  const req = h.requests[0];
  req.status = 200;
  req.response = new ArrayBuffer(8);
  req.onload();
  assert.equal(callbacks, 1);
  assert.equal(h.audio.sounds.boost.failed, false);
  assert.equal(h.timers.size, 0, 'successful audio clears watchdog');
  assert.doesNotThrow(() => {
    h.audio.play('boost');
    h.audio.volume('boost', 0.5);
    h.audio.stop('boost');
  });
}
{
  // Static file:// installs may report HTTP status 0 for valid audio bytes.
  const h = makeAudioHarness();
  let callbacks = 0;
  h.audio.addSound('audio/local.ogg', 'bg', true, () => { callbacks++; });
  const req = h.requests[0];
  req.status = 0;
  req.response = new ArrayBuffer(8);
  req.onload();
  assert.equal(callbacks, 1);
  assert.equal(h.audio.sounds.bg.failed, false);
}
{
  const h = makeAudioHarness(false);
  let callbacks = 0;
  h.audio.addSound('audio/missing.ogg', 'bg', true, () => { callbacks++; });
  const nativeAudio = h.audio.sounds.bg;
  nativeAudio.handlers.error();
  assert.equal(callbacks, 1, 'HTMLAudioElement error must finish loading');
  assert.equal(nativeAudio.failed, true);
  assert.doesNotThrow(() => h.audio.play('bg'));
}
{
  // The manifest's usePanner flag must reach Audio.addSound. The legacy
  // loader silently discarded the fourth argument, disabling crash audio
  // spatialisation even when the manifest explicitly requested it.
  const calls = [];
  const sandbox = {
    bkcore: {Audio: {addSound(...args) { calls.push(args); }}},
    THREE: {JSONLoader: class {}}, console
  };
  vm.runInNewContext(fs.readFileSync('bkcore/threejs/Loader.js', 'utf8'), sandbox);
  const loader = new sandbox.bkcore.threejs.Loader({});
  loader.loadSound('audio/crash.ogg', 'crash', false, true);
  assert.equal(calls[0][4], true, 'spatial audio flag must reach Audio.addSound');
}
console.log('PASS audio: 404, decode failure, timeout, late callback, success, native fallback, panner flag');
