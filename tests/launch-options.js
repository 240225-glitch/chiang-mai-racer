// Regression: URL options must be numeric, not strings.
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');

function boot(query, records, trackOverride, replayValue, useReplay) {
  const elements={};
  function element(id) {
    if (!elements[id]) elements[id]={
      id,innerHTML:'',style:{display:''},onclick:null
    };
    return elements[id];
  }
  const location={href:'http://localhost/'+query,search:query};
  const document={
    getElementById:element,
    createElement(tag){return {getContext(){return {};}}}
  };
  const localStorage={getItem(key){records.push(key);if(key==='race-Chiang Mai Moat (OSM prototype)-replay') return replayValue || null;return key==='hexgl-best-Chiang Mai Moat (OSM prototype)-0-1' ? '64230' : null;}};
  const params={};
  for(const [k,v] of new URLSearchParams(query)) params[k]=v;
  let chosen=null;
  function HexGL(opts){chosen=opts;}
  HexGL.prototype.load=function(){};
  function RaceData(){}
  RaceData.prototype.import=function(frames){if(!Array.isArray(frames)||!frames.length||frames[0].length!==8) throw Error('bad replay');this.data=frames;this.last=frames.length-1;};
  const ctx={document,localStorage,window:{location,innerWidth:1280,innerHeight:800},
    bkcore:{Utils:{getURLParameter(name){return params[name];},isTouchDevice(){return false;}},
      Timer:{msToTimeString(){return {m:1,s:4,ms:230};}},
      hexgl:{HexGL,RaceData,tracks:{Cityscape:{name:'Cityscape'},ChiangMaiMoat:trackOverride || {name:'Chiang Mai Moat (OSM prototype)',moatMode:true}}}},console};
  vm.runInNewContext(fs.readFileSync('launch.js','utf8'),ctx,{filename:'launch.js'});
  if (useReplay) element('menu-replay').onclick();
  else { element('start').onclick(); element('step-2').onclick(); }
  return {opts:chosen,elements};
}

{
  const keys=[];
  const {opts,elements}=boot('?track=moat&players=1&hud=1&quality=0&laps=2&difficulty=1',keys);
  assert.equal(opts.track,'ChiangMaiMoat');
  assert.equal(opts.twoPlayer,true,'URL ?players=1 must launch split-screen');
  assert.equal(opts.hud,true,'URL ?hud=1 must enable HUD');
  assert.equal(opts.cornerGuide,true,'default corner guidance enabled');
  assert.equal(opts.quality,0,'URL ?quality=0 must be a number');
  assert.equal(opts.laps,5);
  assert.equal(opts.difficulty,1);
  assert.equal(elements['s-players'].innerHTML,'模式：双人');
  assert.ok(elements['step-2'].innerHTML.includes('双人同屏对战'));
}
{
  const keys=[];
  const {opts,elements}=boot('?track=moat&players=0&hud=0&laps=0',keys);
  assert.equal(opts.twoPlayer,false);
  assert.equal(opts.hud,false);
  assert.equal(opts.cornerGuide,true);
  assert.equal(opts.laps,1);
  assert.ok(keys.includes('hexgl-best-Chiang Mai Moat (OSM prototype)-0-1'), 'menu must read the same key that HexGL.displayScore writes');
  assert.ok(elements['best'].innerHTML.includes('1\'4\'\'230'), 'saved OSM record must be visible in menu');
}
{
  const keys=[];
  const {opts,elements}=boot('?quality=banana&players=5&laps=-1&hud=100',keys);
  assert.equal(opts.track,'Cityscape');
  assert.equal(opts.quality,3,'invalid quality falls back to default');
  assert.equal(opts.twoPlayer,false,'invalid players falls back to default');
  assert.equal(opts.hud,true,'invalid hud falls back to default');
  assert.equal(opts.laps,3,'invalid lap option falls back to default');
  assert.equal(opts.cornerGuide,true,'invalid guide option uses default');
  assert.equal(elements['s-quality'].innerHTML,'画质：极高');
  assert.equal(elements['s-cornerGuide'].style.display,'none','Cityscape hides irrelevant corner option');
  assert.ok(keys.some(key=>key.startsWith('hexgl-best-Cityscape-')));
}
{
  const keys=[];
  const {opts}=boot('?track=moat&laps=0',keys,{name:'Cityscape'});
  assert.equal(opts.track,'ChiangMaiMoat');
  assert.ok(keys.includes('hexgl-best-Cityscape-0-1'), 'invalid route alias should show actual Cityscape records');
  const fallback=boot('?track=moat&laps=0',[],{name:'Cityscape'});
  assert.equal(fallback.elements['s-cornerGuide'].style.display,'none','fallback hides corner option');
}
console.log('PASS: numeric URL options, split-screen, HUD, invalid query fallback and per-track records');

{
  const keys=[];
  const {opts,elements}=boot('?track=moat&cornerGuide=0',keys);
  assert.equal(opts.cornerGuide,false,'URL can disable corner guidance');
  assert.equal(elements['s-cornerGuide'].style.display,'','OSM displays corner option');
  assert.equal(elements['s-cornerGuide'].innerHTML,'弯道提示：关');
  elements['s-cornerGuide'].onclick();
  assert.equal(elements['s-cornerGuide'].innerHTML,'弯道提示：开');
}

// Saved replay must be available from the menu only for the selected
// track and only when it passes the replay import validation.
{
  const valid=JSON.stringify([[0,0,0,0,0,0,0,1],[100,1,0,0,0,0,0,1]]);
  const a=boot('?track=moat&quality=0',[],undefined,valid,true);
  assert.equal(a.elements['menu-replay'].style.display,'');
  assert.equal(a.opts.twoPlayer,false);
  assert.equal(a.opts.quality,0);
  assert.equal(a.elements['step-3'].style.display,'block');
  const b=boot('?track=moat',[],undefined,'not-json');
  assert.equal(b.elements['menu-replay'].style.display,'none','corrupt replay must not offer a broken viewer');
  const c=boot('?track=moat&players=1',[],undefined,valid);
  assert.equal(c.elements['menu-replay'].style.display,'none','no replay in versus mode');
  const d=boot('?track=moat',[],{name:'Cityscape'},valid);
  assert.equal(d.elements['menu-replay'].style.display,'none','fallback track must not use OSM recording');
}
