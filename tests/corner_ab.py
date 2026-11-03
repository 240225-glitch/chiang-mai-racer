#!/usr/bin/env python3
"""Repeatable TEST-ONLY A/B corner-driving experiment on r50 WebGL.

Each run resets the same vehicle at an OSM point and advances real
ShipControls.update(1) frames. Does not modify game physics or assets.
"""
import argparse
import http.server
import json
import os
import shutil
import threading
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait

ROOT=Path(__file__).resolve().parents[1]
class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,directory=str(ROOT),**kwargs)
    def log_message(self,*args):
        pass

DRIVE = r"""
var start=arguments[0],end=arguments[1],cfg=arguments[2];
var g=window.hexGL,c=g.getShipControls()[0],
    pts=g.track.analyser.route.points,a=pts[start],b=pts[start+1],
    yaw=Math.atan2(b[0]-a[0],b[1]-a[1]);
c.reset({x:a[0],y:4,z:a[1]},
        {x:0,y:Math.sin(yaw/2),z:0,w:Math.cos(yaw/2)});
c.active=true;c.collisionDetection=true;c.speed=.27;
var progress=start,impacts=0,frames=0,impactPoints=[];
for(var i=0;i<cfg.limit;i++){
    var nearest=start-2,best=Infinity;
    for(var j=start-2;j<=end+6;j++){
        var dx=c.dummy.position.x-pts[j][0],
            dz=c.dummy.position.z-pts[j][1],d=dx*dx+dz*dz;
        if(d<best){best=d;nearest=j;}
    }
    progress=Math.max(progress,nearest);
    if(nearest>=end || c.falling || c.destroyed)break;
    var target=pts[Math.min(end+6,nearest+cfg.lookahead)],
        targetYaw=Math.atan2(target[0]-c.dummy.position.x,
                             target[1]-c.dummy.position.z),
        actualYaw=2*Math.atan2(c.dummy.quaternion.y,c.dummy.quaternion.w),
        err=((targetYaw-actualYaw+3*Math.PI)%(2*Math.PI))-Math.PI;
    c.key.left=err>cfg.steerDeadzone;
    c.key.right=err<-cfg.steerDeadzone;
    c.key.forward=true;
    c.key.backward=Math.abs(err)>cfg.brakeAngle&&c.speed>cfg.brakeSpeed;
    c.key.ltrigger=err>cfg.driftAngle&&c.speed>cfg.driftSpeed;
    c.key.rtrigger=err<-cfg.driftAngle&&c.speed>cfg.driftSpeed;
    c.update(1);frames++;
    if(c.collision.front){impacts++;impactPoints.push([frames,nearest,c.speed]);}
}
c.clearKeys();
return {progress:progress,impacts:impacts,frames:frames,
        completed:progress>=end,falling:c.falling,destroyed:c.destroyed,
        shield:c.shield,impactPoints:impactPoints};
"""

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',default=None,help='Optional JSON output path')
    args=p.parse_args()
    os.environ['NO_PROXY']=os.environ['no_proxy']='localhost,127.0.0.1'
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
    threading.Thread(target=server.serve_forever,daemon=True).start()
    browser=shutil.which('google-chrome') or shutil.which('chromium')
    if not browser: raise SystemExit('Chrome is required')
    opts=Options();opts.binary_location=browser
    for flag in ('--headless=new','--no-sandbox','--disable-dev-shm-usage',
                 '--enable-unsafe-swiftshader','--use-gl=angle',
                 '--use-angle=swiftshader','--window-size=1280,800'):
        opts.add_argument(flag)
    configs={
        'baseline':dict(lookahead=3,steerDeadzone=.04,brakeAngle=.23,
                        brakeSpeed=.25,driftAngle=.50,driftSpeed=.30,limit=800),
        'early_brake':dict(lookahead=3,steerDeadzone=.04,brakeAngle=.15,
                           brakeSpeed=.20,driftAngle=.50,driftSpeed=.30,limit=800),
        'short_lookahead':dict(lookahead=2,steerDeadzone=.04,brakeAngle=.18,
                               brakeSpeed=.22,driftAngle=.50,driftSpeed=.30,limit=800),
    }
    trials=[]
    driver=None
    try:
        driver=webdriver.Chrome(options=opts)
        driver.set_page_load_timeout(45)
        driver.get('http://127.0.0.1:%d/?track=moat&quality=0&hud=1&laps=0&players=0' % server.server_address[1])
        driver.execute_script("document.getElementById('start').click();document.getElementById('step-2').click();")
        WebDriverWait(driver,60).until(lambda d:d.execute_script(
            "return document.getElementById('step-4').style.display==='block'"))
        assert driver.execute_script('return window.hexGL.track.moatMode')
        for start,end in ((392,408),(558,578)):
            for name,cfg in configs.items():
                result=driver.execute_script(DRIVE,start,end,cfg)
                trial=dict(start=start,end=end,config=name,**result)
                trials.append(trial)
                print(json.dumps(trial,ensure_ascii=False),flush=True)
        # A/B test harness must prove baseline repeatability.
        for start,end in ((392,408),(558,578)):
            repeated=driver.execute_script(DRIVE,start,end,configs['baseline'])
            original=next(t for t in trials if t['start']==start and t['config']=='baseline')
            assert all(original[k]==repeated[k] for k in
                       ('progress','impacts','frames','completed','impactPoints')), (original,repeated)
        # This is a TEST-ONLY route follower, not a production steering
        # change. Guard the demonstrated shorter-lookahead corner clearance
        # against future geometry or physics regressions.
        for start in (392,558):
            baseline=next(t for t in trials if t['start']==start and t['config']=='baseline')
            short=next(t for t in trials if t['start']==start and t['config']=='short_lookahead')
            assert short['impacts']==0 and short['impacts']<baseline['impacts'],(baseline,short)
        assert all(t['completed'] and not t['falling'] and not t['destroyed'] for t in trials),trials
        if args.output: Path(args.output).write_text(json.dumps(trials,indent=2)+'\n', encoding="utf-8")
        print('PASS six corner trials, two repeated baselines and zero-impact short-lookahead controls',flush=True)
    finally:
        if driver: driver.quit()
        server.shutdown()

if __name__=='__main__': main()
