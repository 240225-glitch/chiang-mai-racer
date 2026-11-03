// Regression: r50 skybox must finish even if a face is missing or never responds.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');

const pending = [];
let timers = [];
const context = {
  console,
  document: {createElement(tag) {
    assert.equal(tag, 'canvas');
    return {tagName:'CANVAS',width:0,height:0,getContext() {
      return {fillRect() {}};
    }};
  }},
  Image: class {
    constructor() {this.tagName='IMG';}
    set src(url) {this.url=url;pending.push(this);}
  },
  setTimeout(fn) {timers.push(fn);return timers.length;},
  clearTimeout() {},
  THREE: {
    JSONLoader: class {},
    CubeRefractionMapping: class {},
    Texture: class {
      constructor(images, mapping) {this.image=images;this.mapping=mapping;this.needsUpdate=false;}
    },
    ImageUtils: {
      // r50 has no error callback for loadTextureCube.
      loadTextureCube(urls, mapping, done) {
        const images=urls.map(url => {const im=new context.Image();im.onload=()=> {
          if(images.filter(x=>x.loaded).length===6) done();
        };im.src=url;return im;});
        return {image:images,needsUpdate:false};
      }
    }
  },
  bkcore: {}
};
vm.runInNewContext(fs.readFileSync('bkcore/threejs/Loader.js','utf8'),context);
function loader() {
  const ready=[],errors=[];
  const lib=new context.bkcore.threejs.Loader({onLoad(){ready.push(1);},onError(n){errors.push(n);}});
  lib.load({texturesCube:{sky:'sky/%1.jpg'}});
  assert.equal(pending.length%6,0,'six skybox faces requested');
  return {lib,ready,errors,faces:pending.slice(-6)};
}
let a=loader();
a.faces[0].onload();
a.faces[1].onerror();
assert.deepEqual(a.errors,['sky'],'missing cube face must report one error');
assert.equal(a.lib.progress.loaded,1,'missing cube face must complete resource');
assert.deepEqual(a.ready,[1]);
const cube=a.lib.get('texturesCube','sky');
assert.equal(cube.image.length,6);
assert.ok(cube.image.every(img=>img.tagName==='CANVAS' && img.width===2 && img.height===2),
  'cube fallback faces must have identical GPU dimensions');
assert.equal(cube.flipY,false);
assert.equal(cube.needsUpdate,true);
a.faces.slice(2).forEach(f=>f.onload());
a.faces[1].onerror();
assert.deepEqual(a.ready,[1],'late face callbacks cannot double-complete');
assert.equal(a.lib.progress.loaded,1);

a=loader();
a.faces.forEach(f=>f.onload());
assert.deepEqual(a.ready,[1],'all six valid faces should complete normally');
assert.deepEqual(a.errors,[]);
assert.ok(a.lib.get('texturesCube','sky').image.every(img=>img.tagName==='IMG'));

a=loader();
const watchdog=timers[timers.length-1];
assert.equal(typeof watchdog,'function','unresponsive cube requests need a timeout');
watchdog();
assert.deepEqual(a.ready,[1],'timeout must release startup');
assert.deepEqual(a.errors,['sky']);
console.log('PASS cubemap: missing face, late events, success, timeout, r50 GPU fallback');
