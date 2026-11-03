#!/usr/bin/env python3
"""Optional headless Chrome + WebGL smoke tests for Chiang Mai Racer.

Requires google-chrome (or chromium) and Python selenium. No internet.
Runs its own localhost HTTP server and does not modify a deployed site.

Usage: python3 tests/browser_smoke.py
"""
from __future__ import annotations

import argparse
import http.server
import importlib.util
import json
import math
import os
import shutil
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BLOCK_ROAD = False
BLOCK_AUDIO = False
BLOCK_VISUAL = False
BLOCK_CUBEMAP = False
BLOCK_GEOMETRY = False
BLOCK_CORE_GEOMETRY = False
BLOCK_ANALYSER = None
ROTATED_ASSETS = {}


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, *args):
        pass

    def do_GET(self):
        if self.path.split("?")[0] in ROTATED_ASSETS:
            body=ROTATED_ASSETS[self.path.split("?")[0]]
            self.send_response(200)
            self.send_header("Content-Type", "application/javascript" if
                             self.path.endswith(".js") else "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
            return
        if BLOCK_ROAD and self.path.split("?")[0].endswith("/chiangmai-moat/road.json"):
            self.send_error(404, "intentional road load failure")
            return
        if BLOCK_AUDIO and self.path.split("?")[0] == "/audio/bg.ogg":
            self.send_error(404, "intentional optional audio failure")
            return
        if BLOCK_CUBEMAP and self.path.split("?")[0] == "/textures/skybox/dawnclouds/nx.jpg":
            self.send_error(404, "intentional skybox face failure")
            return
        if BLOCK_GEOMETRY and self.path.split("?")[0] == "/geometries/booster/booster.js":
            self.send_error(404, "intentional legacy geometry failure")
            return
        if BLOCK_CORE_GEOMETRY and self.path.split("?")[0] == "/geometries/tracks/cityscape/track.js":
            self.send_error(404, "intentional mandatory Cityscape road failure")
            return
        if BLOCK_ANALYSER and self.path.split("?")[0] == BLOCK_ANALYSER:
            self.send_error(404, "intentional mandatory physics analyser failure")
            return
        if BLOCK_VISUAL and self.path.split("?")[0] in (
                "/textures/hud/hex.jpg", "/textures/hud/hud-bg.png"):
            self.send_error(404, "intentional optional visual failure")
            return
        return super().do_GET()


def main():
    global BLOCK_ROAD, BLOCK_AUDIO, BLOCK_VISUAL, BLOCK_CUBEMAP, BLOCK_GEOMETRY, BLOCK_CORE_GEOMETRY, BLOCK_ANALYSER, ROTATED_ASSETS
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=int, default=35)
    parser.add_argument("--physical-laps", type=int, choices=(1,3,5), default=1,
                        help="number of full physics-driven OSM laps")
    parser.add_argument("--follower-lookahead", type=int, choices=(2,3), default=3,
                        help="TEST-ONLY OSM full-lap follower target point offset")
    args = parser.parse_args()

    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.common.exceptions import TimeoutException
    except ImportError as exc:
        raise SystemExit("Selenium missing: pip install selenium") from exc

    browser = shutil.which("google-chrome") or shutil.which("chromium")
    if not browser:
        raise SystemExit("Headless Chrome/Chromium is required")

    # Browser must not route localhost through a system-wide proxy.
    os.environ["NO_PROXY"] = "localhost,127.0.0.1"
    os.environ["no_proxy"] = "localhost,127.0.0.1"
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = "http://127.0.0.1:%d/" % server.server_address[1]

    options = Options()
    options.binary_location = browser
    for flag in (
        "--headless=new", "--no-sandbox", "--disable-dev-shm-usage",
        "--enable-unsafe-swiftshader", "--use-gl=angle",
        "--use-angle=swiftshader", "--window-size=1280,800",
        "--autoplay-policy=no-user-gesture-required",
    ):
        options.add_argument(flag)
    options.set_capability("goog:loggingPrefs", {"browser": "ALL"})
    driver = None
    cases = 0
    try:
        def fresh_browser():
            nonlocal driver
            # Long physics/WebGL tests can retain renderer resources across
            # navigations. Isolate later quality/fallback cases in a new
            # browser process rather than assuming navigation frees them.
            if driver is not None:
                driver.quit()
            driver = webdriver.Chrome(options=options)
            driver.execute_cdp_cmd("Network.enable", {})
            # The 404 fallback test must not use Chrome's HTTP cache.
            driver.execute_cdp_cmd("Network.setCacheDisabled", {"cacheDisabled": True})
            driver.set_page_load_timeout(args.timeout)

        fresh_browser()

        def errors():
            return [
                entry["message"] for entry in driver.get_log("browser")
                if entry["level"] == "SEVERE"
                and "/favicon.ico" not in entry["message"]
            ]

        def boot(query):
            driver.get(base + query)
            # Catch synchronous exceptions thrown by menu click handlers.
            # Chrome sometimes leaves window.hexGL undefined without a
            # SEVERE console entry after repeated SwiftShader contexts.
            driver.execute_script("""window.__cmrStartupErrors=[];
                window.addEventListener('error',function(e){
                  window.__cmrStartupErrors.push({message:e.message,
                    filename:e.filename,line:e.lineno,column:e.colno});
                },true);
                window.addEventListener('unhandledrejection',function(e){
                  window.__cmrStartupErrors.push({rejection:String(e.reason)});
                });""")
            driver.execute_script(
                "document.getElementById('start').click();"
                "document.getElementById('step-2').click();"
            )
            try:
                WebDriverWait(driver, args.timeout).until(
                    lambda d: d.execute_script(
                        "return document.getElementById('step-4').style.display==='block'"
                    )
                )
            except TimeoutException as exc:
                # An intermittent late-case timeout is otherwise opaque.
                # Preserve the loading stage and browser errors for triage.
                try:
                    diagnostic = driver.execute_script(
                        """var track=window.hexGL && window.hexGL.track;
                        var lib=track && track.lib;
                        var pending=[];
                        if(lib && lib.states) Object.keys(lib.states).forEach(function(type) {
                          Object.keys(lib.states[type]).forEach(function(name) {
                            if(lib.states[type][name] !== true && pending.length < 20)
                              pending.push(type+':'+name);
                          });
                        });
                        return {
                          readyState: document.readyState,
                          startupErrors: window.__cmrStartupErrors || [],
                          webglAvailable: !!(window.WebGLRenderingContext),
                          startHandler: typeof document.getElementById('start').onclick,
                          step2Handler: typeof document.getElementById('step-2').onclick,
                          startText: document.getElementById('start').textContent,
                          step2Visible: document.getElementById('step-2').style.display,
                          loadError: document.getElementById('load-error').style.display,
                          step4: document.getElementById('step-4').style.display,
                          track: track && track.name,
                          progress: lib && lib.progress &&
                            {loaded:lib.progress.loaded,total:lib.progress.total,
                             remaining:lib.progress.remaining},
                          pending: pending,
                          audioFailures: Object.keys(bkcore.Audio.sounds).filter(function(id) {
                            return bkcore.Audio.sounds[id].failed;
                          }),
                          resourceCount: performance.getEntriesByType('resource').length,
                          pageUrl: location.href
                        };""")
                    browser_errors = errors()
                except Exception as inspect_exc:
                    diagnostic = {"inspectionError": repr(inspect_exc)}
                    browser_errors = []
                raise AssertionError(
                    "boot timeout for %s: state=%r severeLogs=%r" %
                    (query, diagnostic, browser_errors[-12:])) from exc
            return driver.execute_script(
                """var g=window.hexGL;return {
                  track:g.track.name,moat:!!g.track.moatMode,
                  players:g.getShipControls().length,
                  gameplays:g.getGameplays().length,
                  huds:g.getHuds().length,
                  quality:g.quality,
                  road:!!g.track.roadModel,
                  source:g.track.moatMode ? g.track.analyser.route.source : null,
                  osmWays:g.track.moatMode && g.track.analyser.route.osm_way_ids ? g.track.analyser.route.osm_way_ids.length : 0,
                  waterPolygons:g.track.moatMode ? (g.track.analyser.route.water_polygon_count||0) : 0,
                  meshCount:g.track.moatMode && g.track.roadModel ? g.track.roadModel.children.length : 0,
                  meshNames:g.track.moatMode && g.track.roadModel ?
                    g.track.roadModel.children.map(function(m){return m.name;}) : [],
                  buildingChunkBounds:g.track.moatMode && g.track.roadModel ?
                    g.track.roadModel.children.filter(function(m){
                      return m.name.indexOf('osm-roadside-') === 0;
                    }).map(function(m){
                      return {radius:m.geometry.boundingSphere.radius,
                              culled:m.frustumCulled};
                    }) : [],
                  landmarks:g.track.moatMode ? (g.track.analyser.route.landmarks||[]) : [],
                  landmarkSource:g.track.moatMode ? (g.track.analyser.route.landmark_source||null) : null,
                  landmarkModelStatus:g.track.moatMode ? (g.track.analyser.route.landmark_model_status||null) : null,
                  buildingCount:g.track.moatMode ? (g.track.analyser.route.building_count||0) : 0,
                  estimatedBuildingHeights:g.track.moatMode ? (g.track.analyser.route.building_estimated_height_count||0) : 0,
                  historicGates:g.track.moatMode ? (g.track.analyser.route.historic_gates||[]) : [],
                  checkpointIds:g.track.moatMode ? g.track.analyser.route.checkpoints.map(function(c){return c.point_index;}) : [],
                  routeLength:g.track.moatMode ? g.track.analyser.route.length_m : null,
                  osmAttribution:document.getElementById('osm-attribution').style.display,
                  spawns:g.components.spawns,
                  spawnYaw:g.track.moatMode ? g.track.spawnRotation : null,
                  lateral:g.track.moatMode ? g.track.spawnLateral : null,
                  corridorDistances:g.track.moatMode ?
                    g.components.spawns.map(function(p){
                      return g.track.analyser.distanceSquared(p.x,p.z);
                    }) : null
                };"""
            )

        driver.get(base + "tools/moat-preview.html")
        WebDriverWait(driver, args.timeout).until(
            lambda d: "已载入" in d.execute_script(
                "return document.getElementById('status').textContent"
            )
        )
        assert driver.execute_script(
            "return !!document.querySelector('canvas')"
        ), "preview has no WebGL canvas"
        assert not errors(), "preview WebGL error"
        cases += 1
        print("PASS preview: merged OSM road, water, city gates and temple landmark rendered in WebGL")

        # Regression: the menu must read the actual OSM race record key.
        driver.get(base + "?track=moat&laps=0")
        menu_record = driver.execute_script("""var name=bkcore.hexgl.tracks.ChiangMaiMoat.name;
          var key='hexgl-best-'+name+'-0-1';
          localStorage.setItem(key, 64230);
          return {key:key,name:name};""")
        driver.refresh()
        menu_text = driver.execute_script("return document.getElementById('best').textContent")
        assert "最佳成绩" in menu_text and "暂无记录" not in menu_text, (menu_record, menu_text)
        driver.execute_script("localStorage.removeItem(arguments[0])", menu_record["key"])
        assert not errors(), "OSM saved-record menu error"
        cases += 1
        print("PASS OSM best-record menu: uses live track name shared with results screen")

        # The preview and saved-record menu use a separate WebGL lifecycle.
        # A fresh Chrome process avoids carrying their GPU allocations into
        # the first long physical-driving scenario.
        fresh_browser()
        state = boot("?track=moat&quality=0&hud=1&laps=0&players=0")

        # Real r50 game creates the optional guidance without changing
        # physics; simulate a vehicle near a known OSM corner in the guide.
        guide_state = driver.execute_script("""var g=window.hexGL;
          var guide=g.cornerGuide, p=g.track.analyser.route.points[390];
          if(!guide) return {exists:false};
          guide.tick=5;
          guide.update([{dummy:{position:{x:p[0],z:p[1]}},active:true}],
                       [{active:true,step:4}]);
          var el=document.getElementById('corner-guide-p1');
          var result={exists:true,turns:guide.turns.length,
                      visible:el.style.display,text:el.textContent};
          // 18m off the OSM road is not a valid warning position. The old
          // 30m threshold incorrectly kept showing the upcoming bend.
          var q=g.track.analyser.route.points[391],dx=q[0]-p[0],dz=q[1]-p[1];
          var norm=Math.sqrt(dx*dx+dz*dz);
          guide.tick=5;
          guide.update([{dummy:{position:{x:p[0]+18*dz/norm,
                                        z:p[1]-18*dx/norm}},active:true}],
                       [{active:true,step:4}]);
          result.offRoadHidden=el.style.display==='none';
          // r50's physics dummy faces local +Z; a reversed heading on the
          // same OSM segment must not display a misleading turn direction.
          var yaw=Math.atan2(dx,dz);
          function checkHeading(angle) {
            guide.tick=5;
            guide.update([{dummy:{position:{x:p[0],z:p[1]},
              quaternion:{x:0,y:Math.sin(angle/2),z:0,w:Math.cos(angle/2)}},
              active:true}],[{active:true,step:4}]);
            return el.style.display;
          }
          result.forwardShown=checkHeading(yaw)==='block';
          result.wrongWayHidden=checkHeading(yaw+Math.PI)==='none';
          result.forwardRestored=checkHeading(yaw)==='block';
          guide.reset();
          result.resetHidden=el.style.display==='none';
          return result;""")
        assert guide_state["exists"] and guide_state["turns"] == 2, guide_state
        assert guide_state["visible"] == "block" and "急弯" in guide_state["text"], guide_state
        assert guide_state["offRoadHidden"], guide_state
        assert guide_state["forwardShown"] and guide_state["wrongWayHidden"], guide_state
        assert guide_state["forwardRestored"], guide_state
        assert guide_state["resetHidden"], guide_state
        cases += 1
        print("PASS M3 optional guide: live OSM corner hint and restart hide")
        assert state["moat"] and state["road"] and state["players"] == 1
        assert state["source"] == "© OpenStreetMap contributors", state
        assert state["osmWays"] == 90 and 6350 < state["routeLength"] < 6740, state
        assert state["waterPolygons"] == 19, state
        assert 60 <= state["meshCount"] <= 85, state
        # The two clustered OSM bends render as merged, game-only signs;
        # no collision geometry or runtime traffic-rule claims are added.
        assert {"game-sharp-turn-signs", "game-sharp-turn-arrows"}.issubset(
            set(state["meshNames"])), state
        # Actual r50 projection test: two merged warning boards must be
        # inside a forward-facing road-level camera frustum at 30/50/70m.
        # This is an approximate view test, NOT a manual chase-camera or
        # real-GPU visibility/occlusion acceptance test.
        sign_views=driver.execute_script(
            """var g=window.hexGL,camera=g.manager.get('game').camera,
                   pts=g.track.analyser.route.points,
                   sign=g.track.roadModel.children.filter(function(m){
                     return m.name==='game-sharp-turn-signs';
                   })[0],projector=new THREE.Projector(),
                   savedPosition=camera.position.clone(),
                   savedRotation=camera.quaternion.clone(),views=[];
            try {
              for(var k=0;k<2;k++){
                var verts=sign.geometry.vertices,center=new THREE.Vector3();
                for(var j=k*16;j<k*16+8;j++)center.addSelf(verts[j]);
                center.divideScalar(8);
                var nearest=0,best=Infinity;
                pts.forEach(function(p,i){
                  var d=Math.pow(p[0]-center.x,2)+Math.pow(p[1]-center.z,2);
                  if(d<best){best=d;nearest=i;}
                });
                [3,5,7].forEach(function(back){
                  var i=(nearest-back+pts.length)%pts.length,
                      p=pts[i],q=pts[(i+5)%pts.length];
                  camera.position.set(p[0],4.5,p[1]);
                  camera.lookAt(new THREE.Vector3(q[0],2,q[1]));
                  camera.updateMatrixWorld();
                  var projected=projector.projectVector(
                    center.clone().setY(2.75),camera);
                  views.push({sign:k,back:back,
                    ndc:[projected.x,projected.y,projected.z]});
                });
              }
            } finally {
              camera.position.copy(savedPosition);
              camera.quaternion.copy(savedRotation);
              camera.updateMatrixWorld();
            }
            return views;"""
        )
        assert len(sign_views)==6, sign_views
        assert all(abs(v["ndc"][0])<.7 and abs(v["ndc"][1])<.7
                   and -1<v["ndc"][2]<1 for v in sign_views), sign_views
        assert not errors(), "sharp-turn sign projection WebGL error"
        cases+=1
        print("PASS M3 warning sightlines: both boards in forward r50 camera "
              "frustum at 30/50/70m")
        assert len([n for n in state["meshNames"]
                    if n.startswith("osm-moat-bank-")]) == 19, state
        assert len([n for n in state["meshNames"]
                    if n.startswith("osm-roadside-facades-")]) >= 15, state
        assert len(state["buildingChunkBounds"]) >= 30, state
        assert all(b["culled"] and b["radius"] < 250
                   for b in state["buildingChunkBounds"]), state
        assert len(state["landmarks"]) == 1, state
        assert state["landmarks"][0]["osm_way_ids"] == [
            "243018795","93413945","93413944","441418807"
        ], state
        assert state["landmarkSource"] == (
            "OpenStreetMap Wat Chedi Luang compound/building footprints (ODbL)"
        ), state
        assert "not an architectural reconstruction" in state["landmarkModelStatus"], state
        assert {
            "wat-chedi-luang-stupa",
            "wat-chedi-luang-stupa-buttresses",
            "wat-chedi-luang-viharn-and-shrine",
            "wat-chedi-luang-roofs"
        }.issubset(set(state["meshNames"])), state
        assert state["buildingCount"] == 815, state
        assert state["estimatedBuildingHeights"] == 776, state
        assert len(state["historicGates"]) == 4, state
        assert state["checkpointIds"] == [0,119,320,488], state
        assert state["osmAttribution"] == "block", state
        assert state["huds"] == 1 and state["quality"] == 0
        # Quantify the actual r50 WebGL draw-call benefit of M3 chunks.
        # Merely checking frustumCulled=true and small bounding spheres does
        # not prove that the renderer skips geometry. Render the SAME scene
        # and camera with building culling on/off at four route locations.
        # This uses SwiftShader, so report draw calls/faces, NOT GPU fps.
        culling = driver.execute_script(
            """var g=window.hexGL,setup=g.manager.get('game'),
                   scene=setup.scene,camera=setup.camera,renderer=g.renderer,
                   points=g.track.analyser.route.points,
                   chunks=g.track.roadModel.children.filter(function(m){
                     return m.name.indexOf('osm-roadside-')===0;
                   }), samples=[],savedPosition=camera.position.clone(),
                   savedRotation=camera.rotation.clone();
            try {
              [80,240,400,560].forEach(function(i){
                var p=points[i],q=points[(i+8)%points.length];
                camera.position.set(p[0],12,p[1]);
                camera.lookAt(new THREE.Vector3(q[0],4,q[1]));
                camera.updateMatrixWorld();
                renderer.render(scene,camera);
                var on={calls:renderer.info.render.calls,
                        faces:renderer.info.render.faces};
                chunks.forEach(function(m){m.frustumCulled=false;});
                renderer.render(scene,camera);
                var off={calls:renderer.info.render.calls,
                         faces:renderer.info.render.faces};
                chunks.forEach(function(m){m.frustumCulled=true;});
                samples.push({index:i,on:on,off:off});
              });
            } finally {
              chunks.forEach(function(m){m.frustumCulled=true;});
              camera.position.copy(savedPosition);
              camera.rotation.copy(savedRotation);
              camera.updateMatrixWorld();
            }
            return {chunks:chunks.length,samples:samples};"""
        )
        assert culling["chunks"] == 38, culling
        assert len(culling["samples"]) == 4, culling
        assert all(sample["on"]["calls"] < sample["off"]["calls"]
                   and sample["on"]["faces"] < sample["off"]["faces"]
                   for sample in culling["samples"]), culling
        assert not errors(), "M3 chunk culling WebGL error"
        cases += 1
        print("PASS M3 frustum culling: actual r50 WebGL draw calls "
              + ", ".join("%d->%d" % (s["off"]["calls"],s["on"]["calls"])
                          for s in culling["samples"]))

        driver.execute_script(
            "window.hexGL.getShipControls()[0].key.forward=true;"
        )
        time.sleep(5)
        moving = driver.execute_script(
            """var c=window.hexGL.getShipControls()[0];
            return {z:c.dummy.position.z,active:c.active,
                    destroyed:c.destroyed,speed:c.speed};"""
        )
        assert moving["active"] and not moving["destroyed"], moving
        assert moving["z"] > 2 and moving["speed"] > 0, moving
        # Fast-forward through real analyser positions to test a whole
        # one-lap Gameplay integration, without claiming manual driving.
        lap = driver.execute_script(
            """var g=window.hexGL,p=g.getGameplays()[0];
            var cps=g.track.analyser.route.checkpoints;
            p.step=4;
            for(var i=1;i<=4;i++){
                var cp=cps[i%4];
                // This is a checkpoint state-machine test, not physical
                // travel: seed a local prior sample for each injected pose.
                p._lastCheckpointSample={x:cp.x,z:cp.z};
                p.shipControls.dummy.position.x=cp.x;
                p.shipControls.dummy.position.z=cp.z;
                p.timer.time.elapsed+=1000;
                p.modes.timeattack.call(p);
            }
            return {result:p.result,expected:p.results.FINISH,
                    lapTimes:p.lapTimes.length};"""
        )
        assert lap["result"] == lap["expected"] and lap["lapTimes"] == 1, lap
        assert not errors(), "solo WebGL error"
        cases += 1
        print("PASS solo: forward driving and one simulated lap through live checkpoints")

        state = boot("?track=moat&quality=0&hud=1&laps=0&players=1")
        assert state["moat"] and state["players"] == 2, state
        assert state["gameplays"] == 2 and state["huds"] == 2, state
        steering=driver.execute_script(
            "return window.hexGL.getShipControls().map(function(c){"
            "return [c.angularSpeed,c.airAngularSpeed];});")
        assert steering == [[0.024,0.03],[0.024,0.03]], steering
        a,b=state["spawns"]
        dx=b["x"]-a["x"]
        dz=b["z"]-a["z"]
        assert abs((dx*dx+dz*dz)**0.5-5.6)<0.05, state
        assert all(distance<7*7 for distance in state["corridorDistances"]), state
        # Split-screen spacing must be perpendicular to road direction,
        # not hardcoded to world X when imported OSM route turns diagonal.
        yaw=2*math.atan2(state["spawnYaw"]["y"],
                                      state["spawnYaw"]["w"])
        forward=(math.sin(yaw),math.cos(yaw))
        assert abs(dx*forward[0]+dz*forward[1])<0.05, state
        # Move only P1 to the first non-start checkpoint, preserving P2 state.
        indices = driver.execute_script(
            """var g=window.hexGL;
            var p1=g.getGameplays()[0],p2=g.getGameplays()[1];
            var cp=g.track.analyser.route.checkpoints[1];
            p1._lastCheckpointSample={x:cp.x,z:cp.z};
            p1.shipControls.dummy.position.x=cp.x;
            p1.shipControls.dummy.position.z=cp.z;
            p1.step=4;p1.modes.timeattack.call(p1);
            return [p1.nextCheckPointIndex,p2.nextCheckPointIndex];"""
        )
        assert indices == [2, 1], indices
        assert not errors(), "split-screen WebGL error"
        cases += 1
        print("PASS split-screen: two independent controls/HUDs/checkpoints")

        # The legacy pixel collision used to call fall() as soon as both
        # lateral samples went black. A modest shoulder excursion on a
        # real 14m road must instead be corrected without killing the race.
        state = boot("?track=moat&quality=0&hud=1&laps=0&players=0")
        assert state["moat"]
        recovery = driver.execute_script(
            """var g=window.hexGL,c=g.getShipControls()[0],r=g.track.analyser.route;
            var a=r.points[79],p=r.points[80],b=r.points[81];
            var dx=b[0]-a[0],dz=b[1]-a[1],d=Math.sqrt(dx*dx+dz*dz);
            var nx=-dz/d,nz=dx/d;
            c.dummy.position.x=p[0]+nx*11;
            c.dummy.position.z=p[1]+nz*11;
            c.speed=0.5;c.boost=0.1;c.nitroActive=0.5;
            var before=g.track.analyser.distanceSquared(
                c.dummy.position.x,c.dummy.position.z);
            var collided=c.collisionCheck(1);
            return {before:before,after:g.track.analyser.distanceSquared(
                c.dummy.position.x,c.dummy.position.z),
                collided:collided,falling:c.falling,destroyed:c.destroyed,
                speed:c.speed,boost:c.boost,nitro:c.nitroActive};"""
        )
        assert recovery["before"]>49 and recovery["collided"], recovery
        assert recovery["after"]<49, recovery
        assert not recovery["falling"] and not recovery["destroyed"], recovery
        assert recovery["speed"]<0.5 and recovery["boost"]==0, recovery
        assert recovery["nitro"]==0, recovery
        assert not errors(), "shoulder recovery WebGL error"
        cases += 1
        print("PASS shoulder: actual physics collision clamps car inside OSM road")

        # Endpoint-only collision accepted a large one-frame jump from one
        # OSM road segment to another across the undriveable city interior.
        # Exercise the actual ShipControls.collisionCheck adapter in r50.
        state=boot("?track=moat&quality=0&hud=1&laps=0&players=0")
        jump=driver.execute_script(
            """var g=window.hexGL,c=g.getShipControls()[0],
                   pts=g.track.analyser.route.points;
            var start=pts[80],end=pts[400];
            c.collisionPreviousPosition.set(start[0],4,start[1]);
            c.dummy.position.set(end[0],4,end[1]);
            c.speed=.5;
            var endDistance=g.track.analyser.distanceSquared(end[0],end[1]);
            var hit=c.collisionCheck(1);
            return {hit:hit,endDistance:endDistance,
                    fromStart:Math.hypot(c.dummy.position.x-start[0],
                                         c.dummy.position.z-start[1]),
                    fromEnd:Math.hypot(c.dummy.position.x-end[0],
                                       c.dummy.position.z-end[1]),
                    falling:c.falling,destroyed:c.destroyed};"""
        )
        assert jump["endDistance"]<49 and jump["hit"],jump
        assert jump["fromStart"]<10 and jump["fromEnd"]>100,jump
        assert not jump["falling"] and not jump["destroyed"],jump
        assert not errors(), "swept road collision WebGL error"
        cases+=1
        print("PASS swept collision: road-to-road shortcut across city rejected")

        # Sub-metre travel can cross a narrow gap between two individually
        # legal road ribbons. Check the real ShipControls collision adapter,
        # not just the standalone MoatCollision Node implementation.
        narrow=driver.execute_script(
            """var c=window.hexGL.getShipControls()[0];
            c.collisionMap=new bkcore.hexgl.MoatCollision.Collision({
                closed:true,road_width_m:14,
                points:[[-100,0],[100,0],[100,14.4],[-100,14.4]],
                checkpoints:[]});
            c.collisionPreviousPosition.set(0,4,6.9);
            c.dummy.position.set(0,4,7.5);
            c.speed=.3;c.shieldDelay=60;
            var hit=c.collisionCheck(1);
            return {hit:hit,z:c.dummy.position.z,falling:c.falling,
                    destroyed:c.destroyed};"""
        )
        assert narrow["hit"] and narrow["z"]<=7+1e-8,narrow
        assert not narrow["falling"] and not narrow["destroyed"],narrow
        # The endpoint itself is off-road, so shoulder recovery must not
        # project the vehicle across the 0.4m gap to the opposite ribbon.
        shoulder_gap=driver.execute_script(
            """var c=window.hexGL.getShipControls()[0];
            c.collisionPreviousPosition.set(0,4,6.9);
            c.dummy.position.set(0,4,7.3);
            c.speed=.3;c.shieldDelay=60;
            var hit=c.collisionCheck(1);
            return {hit:hit,z:c.dummy.position.z,falling:c.falling,
                    destroyed:c.destroyed};"""
        )
        assert shoulder_gap["hit"] and shoulder_gap["z"]<=7+1e-8,shoulder_gap
        assert not shoulder_gap["falling"] and not shoulder_gap["destroyed"],shoulder_gap
        assert not errors(), "sub-metre swept collision WebGL error"
        cases+=1
        print("PASS sub-metre sweep: 0.4m gap blocked by real physics adapter")

        # Actual r50 Gameplay and ShipControls must use continuous OSM
        # metre coordinates, not round to legacy bitmap pixels. On a
        # diagonal road the rounded sample can fall outside a legal lane.
        fractional=driver.execute_script(
            """var g=window.hexGL,c=g.getShipControls()[0],p=g.getGameplays()[0];
            var map=new bkcore.hexgl.MoatCollision.Collision({
                closed:true,road_width_m:14,
                points:[[0,0],[100,100],[200,0],[100,-100]],
                checkpoints:[{x:50,z:50},{x:150,z:50},
                             {x:150,z:-50},{x:50,z:-50}]});
            c.dummy.position.set(50.2,4,59.6);
            p.analyser=map;p.pixelRatio=1;
            // This test swaps analysers, not a physical journey from
            // the prior scenario; seed its local trusted sample.
            p._lastCheckpointSample={x:50.2,z:59.6};
            var checkpoint=p.checkPoint();
            var rounded=map.getPixel(50,60);
            map.route.checkpoints=[];map.boostPoints=[[50,50]];
            c.collisionMap=map;c.collisionPixelRatio=1;
            c.boost=0;c.onBoostPad=false;c.nitro=0.5;
            c.boosterCheck(1);
            return {checkpoint:checkpoint,rounded:rounded.r,
                    pad:c.onBoostPad,boost:c.boost,nitro:c.nitro};"""
        )
        assert fractional["rounded"]==0 and fractional["checkpoint"]==0,fractional
        assert fractional["pad"] and fractional["boost"]>0,fractional
        assert fractional["nitro"]>0.5,fractional
        assert not errors(), "fractional OSM metre analyser WebGL error"
        cases+=1
        print("PASS fractional OSM coordinates: live checkpoint and boost-pad physics")

        # A frame hitch can skip a checkpoint disc entirely. Exercise the
        # actual r50 Gameplay.checkPoint() on a synthetic straight OSM road;
        # verify the sweep registers a legal crossing exactly once and
        # refuses a shortcut through the non-driveable city interior.
        gate_sweep=driver.execute_script(
            """var g=window.hexGL,c=g.getShipControls()[0],gp=g.getGameplays()[0];
            var map=new bkcore.hexgl.MoatCollision.Collision({
                closed:true,road_width_m:14,
                points:[[0,0],[100,0],[100,100],[0,100]],
                checkpoints:[{x:0,z:0},{x:50,z:0},{x:100,z:100},{x:0,z:100}]});
            gp.analyser=map;gp.pixelRatio=1;gp.nextCheckPointIndex=1;
            gp._lastCheckpointSample={x:35,z:0};
            c.dummy.position.set(65,4,0);
            var crossed=gp.checkPoint(),repeat=gp.checkPoint();
            map.route.checkpoints[1]={x:100,z:50};
            gp._lastCheckpointSample={x:100,z:40};
            c.dummy.position.set(0,4,60);
            var shortcut=gp.checkPoint();
            map.route.checkpoints[1]={x:50,z:0};
            gp._lastCheckpointSample={x:0,z:50};
            c.dummy.position.set(50,4,0);
            var endpointShortcut=gp.checkPoint();
            gp._lastCheckpointSample={x:20,z:0};
            var legalEndpoint=gp.checkPoint();
            var nearby=new bkcore.hexgl.MoatCollision.Collision({
                closed:true,road_width_m:14,
                points:[[-100,0],[100,0],[100,20],[-100,20]],
                checkpoints:[{x:-50,z:0},{x:0,z:20},
                    {x:50,z:20},{x:50,z:0}]});
            gp.analyser=nearby;
            gp._lastCheckpointSample={x:0,z:6.9};
            c.dummy.position.set(0,4,13.1);
            var shortGap=gp.checkPoint();
            var shortGapRepeat=gp.checkPoint();
            gp._lastCheckpointSample={x:0,z:14};
            var shortLegal=gp.checkPoint();
            return {crossed:crossed,repeat:repeat,shortcut:shortcut,
                endpointShortcut:endpointShortcut,legalEndpoint:legalEndpoint,
                shortGap:shortGap,shortGapRepeat:shortGapRepeat,
                shortLegal:shortLegal};"""
        )
        assert gate_sweep=={"crossed":1,"repeat":-1,"shortcut":-1,
                            "endpointShortcut":-1,"legalEndpoint":1,
                            "shortGap":-1,"shortGapRepeat":-1,
                            "shortLegal":1},gate_sweep
        assert not errors(), "swept checkpoint WebGL error"
        cases+=1
        print("PASS swept OSM gate: missed endpoint crossing recovered without shortcut")

        # The M2 controller is updated by the render manager even while
        # Gameplay is counting down or displaying the results screen.
        # Inactive cars must not coast or consume a boost pad before start.
        state=boot("?track=moat&quality=0&hud=1&laps=0&players=0")
        inactive=driver.execute_script(
            """var g=window.hexGL,c=g.getShipControls()[0],p=g.getGameplays()[0],
                   pad=g.track.analyser.boostPoints[0];
            c.reset({x:pad[0],y:4,z:pad[1]},p.spawnRotation);
            c.active=false;c.speed=.35;c.boost=.15;c.nitroActive=.8;
            var x=c.dummy.position.x,z=c.dummy.position.z;
            for(var i=0;i<20;i++)c.update(1);
            return {moved:Math.hypot(c.dummy.position.x-x,c.dummy.position.z-z),
                    speed:c.speed,boost:c.boost,nitro:c.nitro,
                    activeNitro:c.nitroActive,onPad:c.onBoostPad};"""
        )
        assert inactive["moved"]<1e-7,inactive
        assert abs(inactive["speed"]-.35)<1e-7,inactive
        assert abs(inactive["boost"]-.15)<1e-7,inactive
        assert abs(inactive["activeNitro"]-.8)<1e-7,inactive
        assert abs(inactive["nitro"]-.5)<1e-7,inactive
        assert not inactive["onPad"],inactive
        assert not errors(), "inactive physics WebGL error"
        countdown_nitro=driver.execute_script("""var g=window.hexGL,
            c=g.getShipControls()[0],p=g.getGameplays()[0];
            c.reset(p.spawn,p.spawnRotation);
            c.active=false;c.key.nitro=true;c.triggerNitro();c.update(1);
            c.active=true;c.nitroCheck(1);
            var heldFromCountdown=c.nitroActive;
            c.key.nitro=false;c.nitroCheck(1);
            c.key.nitro=true;c.nitroCheck(1);
            var freshPress=c.nitroActive;
            c.reset(p.spawn,p.spawnRotation);
            c.active=false;c.triggerNitro();c.update(1);
            c.active=true;c.nitroCheck(1);
            return {heldFromCountdown:heldFromCountdown,
                    freshPress:freshPress,queuedTouch:c.nitroActive};""")
        assert countdown_nitro["heldFromCountdown"]==0,countdown_nitro
        assert countdown_nitro["queuedTouch"]==0,countdown_nitro
        assert countdown_nitro["freshPress"]>0,countdown_nitro
        cases+=1
        print("PASS countdown/results: frozen M2 car, stale nitro ignored, fresh press accepted")

        # Verify real nitro physics and one-time boost-pad replenishment,
        # without changing the original Cityscape controller.
        nitro=driver.execute_script(
            """var g=window.hexGL,c=g.getShipControls()[0],p=g.getGameplays()[0];
            c.reset(p.spawn,p.spawnRotation);
            c.active=true;c.speed=.3;c.collisionDetection=false;
            c.triggerNitro();c.update(1);
            var first={remaining:c.nitro,active:c.nitroActive,
                       boosted:c.getNitroBoost(),speed:c.getRealSpeedRatio()};
            c.update(1);
            var held={remaining:c.nitro,active:c.nitroActive};
            var pad=g.track.analyser.boostPoints[1];
            c.dummy.position.x=pad[0];c.dummy.position.z=pad[1];
            c.boosterCheck(1);
            var replenished=c.nitro;
            c.boosterCheck(1);
            var repeated=c.nitro;
            return {first:first,held:held,replenished:replenished,
                    repeated:repeated};"""
        )
        assert nitro["first"]["active"]>0 and nitro["first"]["boosted"]>0,nitro
        assert nitro["first"]["remaining"]<.02,nitro
        assert nitro["held"]["remaining"]<.03,nitro
        assert nitro["replenished"]>nitro["held"]["remaining"]+.24,nitro
        assert abs(nitro["replenished"]-nitro["repeated"])<1e-6,nitro
        assert not errors(), "nitro/boost WebGL error"
        cases+=1
        print("PASS nitro: real physics boost and once-per-entry OSM boost pad recharge")

        # OSM corners include a ~55 degree heading change over 10m.
        # The original ship's 0.005 rad/frame steering can turn only ~4
        # degrees over 14 frames, even with handbrake, so a car would
        # repeatedly hit the shoulder. Exercise real r50 physics steering
        # here, not just static configuration values.
        turn=driver.execute_script(
            """var c=window.hexGL.getShipControls()[0];
            c.collisionDetection=false; // isolate steering from recovery
            c.active=true;c.speed=0.35;
            c.key.forward=true;c.key.left=true;c.key.ltrigger=true;
            var q=c.dummy.quaternion;
            var before=2*Math.atan2(q.y,q.w);
            for(var i=0;i<14;i++) c.update(1);
            var after=2*Math.atan2(q.y,q.w);
            var delta=((after-before+Math.PI*3)%(2*Math.PI))-Math.PI;
            c.key.left=false;c.key.ltrigger=false;c.key.forward=false;
            return {delta:delta,speed:c.speed,
                    angular:c.angularSpeed,driftAngular:c.airAngularSpeed,
                    destroyed:c.destroyed};"""
        )
        assert 1.0 < turn["delta"] < 1.45, turn
        assert turn["speed"] >= 0 and not turn["destroyed"], turn
        assert not errors(), "M2 tight-corner steering WebGL error"
        cases += 1
        print("PASS corner steering: handbrake rotates %.1f degrees in 14 physics frames" % (turn["delta"]*180/math.pi))

        # Restart after a collision: stale repulsion or smoothed yaw must
        # not move a stationary car on the first frame of the new race.
        restart=driver.execute_script(
            """var g=window.hexGL,c=g.getShipControls()[0],
                   gp=g.getGameplays()[0];
            c.reset(gp.spawn,gp.spawnRotation);
            c.angular=.3;c.repulsionForce.set(2,0,-1);
            c.collision.front=true;c.shieldDelay=0;
            c.reset(gp.spawn,gp.spawnRotation);
            c.active=true;
            var x=c.dummy.position.x,z=c.dummy.position.z;
            c.update(1);
            var result={distance:Math.hypot(c.dummy.position.x-x,
                                          c.dummy.position.z-z),
                        angular:c.angular,
                        repulsion:c.repulsionForce.length(),
                        collision:c.collision.front,
                        shieldDelay:c.shieldDelay};
            c.clearKeys();
            return result;"""
        )
        assert restart["distance"]<1e-7, restart
        assert abs(restart["angular"])<1e-10, restart
        assert restart["repulsion"]<1e-10, restart
        assert restart["collision"] is False, restart
        assert restart["shieldDelay"]>=59, restart
        assert not errors(), "restart physics WebGL error"
        cases += 1
        print("PASS race restart: no inherited steering or crash impulse")

        bend=driver.execute_script(
            """var c=window.hexGL.getShipControls()[0],
                   pts=window.hexGL.track.analyser.route.points;
            var a=pts[392],b=pts[393],yaw=Math.atan2(b[0]-a[0],b[1]-a[1]);
            c.reset({x:a[0],y:4,z:a[1]},
                {x:0,y:Math.sin(yaw/2),z:0,w:Math.cos(yaw/2)});
            c.active=true;c.collisionDetection=true;c.speed=.27;
            var progress=392,impacts=0,frames=0;
            for(var i=0;i<430;i++){
                var nearest=390,best=Infinity;
                for(var j=390;j<=415;j++){
                    var dx=c.dummy.position.x-pts[j][0];
                    var dz=c.dummy.position.z-pts[j][1];
                    var d=dx*dx+dz*dz;
                    if(d<best){best=d;nearest=j;}
                }
                progress=Math.max(progress,nearest);
                if(nearest>=408)break;
                var target=pts[Math.min(415,nearest+3)];
                var targetYaw=Math.atan2(target[0]-c.dummy.position.x,
                                         target[1]-c.dummy.position.z);
                var actualYaw=2*Math.atan2(c.dummy.quaternion.y,c.dummy.quaternion.w);
                var err=((targetYaw-actualYaw+3*Math.PI)%(2*Math.PI))-Math.PI;
                c.key.left=err>.045;c.key.right=err<-.045;
                c.key.forward=true;c.key.backward=Math.abs(err)>.25&&c.speed>.3;
                c.update(1);frames++;
                if(c.collision.front)impacts++;
                if(c.falling||c.destroyed)break;
            }
            c.clearKeys();
            return {progress:progress,impacts:impacts,frames:frames,
                    destroyed:c.destroyed,falling:c.falling};"""
        )
        assert bend["progress"] >= 408, bend
        assert bend["impacts"] <= 12, bend
        assert not bend["destroyed"] and not bend["falling"], bend
        assert not errors(), "OSM corner driving WebGL error"
        cases += 1
        print("PASS OSM corner: physics-driven follower crosses sharp bend "
              "(%d frames, %d shoulder corrections)" %
              (bend["frames"],bend["impacts"]))

        # Unlike the earlier checkpoint smoke test, this covers every metre
        # of the real OSM route using ShipControls.update(1). The route
        # follower is TEST-ONLY (not a production driving assistant). It
        # cannot teleport to checkpoints or write gameplay progress directly.
        # Use --physical-laps 3 or 5 for longer regression runs.
        driver.set_script_timeout(max(90, args.physical_laps*45))
        lap_drive=driver.execute_script(
            """var laps=arguments[0],lookahead=arguments[1],g=window.hexGL,
                   c=g.getShipControls()[0],gp=g.getGameplays()[0],
                   pts=g.track.analyser.route.points,n=pts.length;
            c.reset(gp.spawn,gp.spawnRotation);
            c.active=true;c.collisionDetection=true;c.speed=.27;
            gp.step=4;gp.active=true;gp.result=gp.results.NONE;
            gp.lap=1;gp.maxLaps=laps;gp.lapTimes=[];
            gp.lapTimeElapsed=0;gp.nextCheckPointIndex=1;
            gp.previousCheckPoint=0;gp.timer.time.elapsed=0;
            var progress=0,impacts=0,frames=0,stuck=0,stuckAt=0,impactPoints=[];
            var visited=[],lastCp=gp.nextCheckPointIndex;
            for(var i=0;i<24000*laps;i++){
                var best=Infinity,nearest=progress;
                for(var k=Math.max(0,progress-8);
                    k<=Math.min(progress+10,n*laps+8);k++){
                    var j=k%n;
                    var dx=c.dummy.position.x-pts[j][0];
                    var dz=c.dummy.position.z-pts[j][1];
                    var d=dx*dx+dz*dz;
                    if(d<best){best=d;nearest=k;}
                }
                if(nearest>progress)progress=nearest;
                if(gp.result===gp.results.FINISH)break;
                var target=pts[(progress+lookahead)%n];
                var targetYaw=Math.atan2(target[0]-c.dummy.position.x,
                                         target[1]-c.dummy.position.z);
                var actualYaw=2*Math.atan2(c.dummy.quaternion.y,
                                           c.dummy.quaternion.w);
                var err=((targetYaw-actualYaw+3*Math.PI)%(2*Math.PI))-Math.PI;
                c.key.left=err>.04;c.key.right=err<-.04;
                c.key.forward=true;
                c.key.backward=Math.abs(err)>.23&&c.speed>.25;
                c.key.ltrigger=err>.50&&c.speed>.30;
                c.key.rtrigger=err<-.50&&c.speed>.30;
                c.update(1);frames++;
                if(c.collision.front){impacts++;impactPoints.push([frames,progress,c.speed]);}
                gp.timer.time.elapsed+=1000/60;
                if(i%3===0){
                    gp.modes.timeattack.call(gp);
                    if(lastCp!==gp.nextCheckPointIndex){
                        visited.push([frames,gp.nextCheckPointIndex,progress]);
                        lastCp=gp.nextCheckPointIndex;
                    }
                }
                if(c.falling||c.destroyed)break;
                if(frames%500===0){
                    stuck=progress-stuckAt<5?stuck+1:0;
                    stuckAt=progress;
                    if(stuck>=3)break;
                }
            }
            c.clearKeys();
            return {progress:progress,routePoints:n,impacts:impacts,
                    frames:frames,lap:gp.lap,lapTimes:gp.lapTimes.length,
                    result:gp.result,expected:gp.results.FINISH,
                    next:gp.nextCheckPointIndex,visited:visited,
                    falling:c.falling,destroyed:c.destroyed,
                    shield:c.shield,recorded:gp.raceData.data.length,impactPoints:impactPoints};""",
            args.physical_laps, args.follower_lookahead
        )
        print("DIAGNOSTIC impact points:", lap_drive["impactPoints"])
        assert lap_drive["result"]==lap_drive["expected"],lap_drive
        assert lap_drive["lapTimes"]==args.physical_laps,lap_drive
        assert lap_drive["progress"]>=(
            args.physical_laps*lap_drive["routePoints"]-10),lap_drive
        assert [x[1] for x in lap_drive["visited"]]==(
            [2,3,0,1]*args.physical_laps),lap_drive
        assert lap_drive["impacts"]<=15*args.physical_laps,lap_drive
        assert not lap_drive["falling"] and not lap_drive["destroyed"],lap_drive
        assert lap_drive["recorded"]<lap_drive["frames"]/2,lap_drive
        # A single-player result must clear any stale bend warning, even
        # though HexGL.active stops the normal guide update loop.
        finish_guide = driver.execute_script("""var g=window.hexGL,el=document.getElementById('corner-guide-p1');
          if (!g.cornerGuide) return {guide:false};
          el.style.display='block';
          g.displayScore(g.gameplay.finishTime,g.gameplay.lapTimes);
          var stored=localStorage.getItem('race-'+g.track.name+'-replay');
          var parsed=stored ? JSON.parse(stored) : [];
          return {guide:true,hidden:el.style.display==='none',
                  savedFrames:parsed.length,expectedFrames:g.gameplay.raceData.data.length,
                  firstTime:parsed.length ? parsed[0][0] : null};""")
        assert finish_guide.get('guide') and finish_guide.get('hidden'),finish_guide
        assert finish_guide['savedFrames']==finish_guide['expectedFrames'],finish_guide
        assert finish_guide['savedFrames']>100,finish_guide
        assert not errors(), "full OSM lap physics WebGL error"
        cases+=1
        print("PASS OSM full %d-lap physics drive: %d frames, %d shoulder "
              "corrections, %d replay samples" %
              (args.physical_laps,lap_drive["frames"],lap_drive["impacts"],
               lap_drive["recorded"]))

        # Player-facing replay: use the saved race, pause and scrub both
        # directions in the actual r50 scene, then return to the score UI.
        replay_ui=driver.execute_script(
            """var g=window.hexGL,btn=document.getElementById('go-replay'),
                   stored=localStorage.getItem('race-'+g.track.name+'-replay'),
                   frames=JSON.parse(stored),a=frames[0],b=frames[1],
                   t=(a[0]+b[0])/2;
            var visible=btn.style.display!=='none';
            btn.click();
            var opened=!!g.replayViewer,
                controls=document.getElementById('replay-controls').style.display,
                scoreHidden=document.getElementById('step-5').style.display==='none';
            var toggle=document.getElementById('replay-toggle'),
                bounds=toggle.getBoundingClientRect(),
                hit=document.elementFromPoint(bounds.left+bounds.width/2,
                                              bounds.top+bounds.height/2),
                clickable=hit===toggle || toggle.contains(hit),
                nitroHidden=document.getElementById('race-ui').style.display==='none';
            toggle.click();
            var range=document.getElementById('replay-seek');
            range.value=String(t);
            range.dispatchEvent(new Event('input',{bubbles:true}));
            var x=g.components.shipControls.dummy.position.x,
                paused=g.replayViewer.paused,
                target=t, slider=Number(document.getElementById('replay-seek').value),
                expected=(a[1]+b[1])/2;
            g.seekReplay(frames[frames.length-1][0]);
            var end=g.components.shipControls.dummy.position.x;
            g.seekReplay(t);
            var rewind=g.components.shipControls.dummy.position.x;
            var rejectedInvalidSeek=!g.seekReplay(NaN);
            // Reaching the last saved pose should pause, and Play at the
            // end should restart from the beginning without re-importing.
            g.seekReplay(frames[frames.length-1][0]);
            g.toggleReplayPlayback();
            var restarted=g.replayViewer.elapsed===0 && !g.replayViewer.paused;
            document.getElementById('replay-exit').click();
            var closed=g.replayViewer===null &&
                document.getElementById('step-5').style.display==='block' &&
                document.getElementById('replay-controls').style.display==='none' &&
                document.getElementById('race-ui').style.display!== 'none';
            // A corrupted localStorage entry must not crash the viewer or
            // hide the score screen; restore the good capture afterwards.
            localStorage.setItem('race-'+g.track.name+'-replay','not-json');
            var invalidRejected=!g.openReplay() && !g.replayViewer;
            localStorage.setItem('race-'+g.track.name+'-replay',stored);
            return {visible:visible,opened:opened,target:t,controls:controls,
                    clickable:clickable,nitroHidden:nitroHidden,
                    scoreHidden:scoreHidden,paused:paused,slider:slider,
                    x:x,expected:expected,end:end,
                    expectedEnd:frames[frames.length-1][1],
                    rewind:rewind,closed:closed,
                    invalidRejected:invalidRejected,
                    rejectedInvalidSeek:rejectedInvalidSeek,restarted:restarted};"""
        )
        assert replay_ui["visible"] and replay_ui["opened"],replay_ui
        assert replay_ui["controls"]=="flex" and replay_ui["scoreHidden"] and replay_ui["clickable"] and replay_ui["nitroHidden"],replay_ui
        assert replay_ui["paused"] and abs(replay_ui["slider"]-replay_ui["target"])<1,replay_ui
        for key,expected in (("x","expected"),("end","expectedEnd"),
                             ("rewind","expected")):
            assert abs(replay_ui[key]-replay_ui[expected])<0.04,replay_ui
        assert replay_ui["closed"] and replay_ui["invalidRejected"] and replay_ui["rejectedInvalidSeek"] and replay_ui["restarted"],replay_ui
        assert not errors(), "player replay UI WebGL error"
        cases+=1
        print("PASS replay UI: saved race, pause, seek, rewind, close, bad save")

        # The original RaceData replay implementation accessed the frame
        # after the final sample and threw in the render loop. Exercise
        # real r50 interpolation and final-frame clamping in WebGL.
        playback=driver.execute_script(
            """var g=window.hexGL,c=g.getShipControls()[0],
                   source=g.getGameplays()[0].raceData.data;
            var replay=new bkcore.hexgl.RaceData('moat','replay',c);
            replay.import(JSON.parse(localStorage.getItem('race-'+g.track.name+'-replay')));
            var a=source[0],b=source[1],last=source[source.length-1];
            replay.applyInterpolated(a[0]-1000);
            var start=c.dummy.position.x;
            replay.applyInterpolated((a[0]+b[0])/2);
            var midpoint=c.dummy.position.x;
            replay.applyInterpolated(last[0]+1000);
            var end=c.dummy.position.x;
            // Rewind without calling reset/import: the replay cursor must
            // track the requested time instead of staying at its last frame.
            replay.applyInterpolated((a[0]+b[0])/2);
            var rewind=c.dummy.position.x,rewindSeek=replay.seek;
            replay.applyInterpolated(a[0]-1000);
            var rewindStart=c.dummy.position.x;
            // Damaged saved orientations must fail before reaching r50
            // slerp; small rounding errors must normalize safely.
            var badQuaternionRejected=false;
            try { replay.import([[100,0,0,0,0,0,0,0]]); }
            catch(e) { badQuaternionRejected=/quaternion/.test(e.message); }
            var rounded=new bkcore.hexgl.RaceData('moat','replay',c);
            rounded.import([[100,0,0,0,0,0,0,1.004],
                            [200,1,0,0,0,0,0,1.004]]);
            rounded.applyInterpolated(150);
            var roundedW=c.dummy.quaternion.w;
            // A previously validated import must not be corrupted through
            // an alias to its caller-owned frame array.
            var shared=[[100,7,0,0,0,0,0,1],[200,9,0,0,0,0,0,1]];
            var isolated=new bkcore.hexgl.RaceData('moat','replay',c);
            isolated.import(shared);
            shared[0][1]=777;
            shared[1][7]=0;
            isolated.applyInterpolated(100);
            var isolatedX=c.dummy.position.x;
            isolated.applyInterpolated(150);
            var isolatedW=c.dummy.quaternion.w;
            // Real r50 duplicate-time poses must not depend on seek history.
            var repeated=new bkcore.hexgl.RaceData('moat','replay',c);
            repeated.import([[100,10,0,0,0,0,0,1],
                             [100,20,0,0,0,0,0,1],
                             [200,30,0,0,0,0,0,1]]);
            repeated.applyInterpolated(100);
            var duplicateForward=c.dummy.position.x;
            repeated.applyInterpolated(250);
            repeated.applyInterpolated(100);
            var duplicateRewind=c.dummy.position.x;
            return {duplicateForward:duplicateForward,
                    duplicateRewind:duplicateRewind,
                    isolatedX:isolatedX,isolatedW:isolatedW,
                    isolatedCount:isolated.data.length,
                    badQuaternionRejected:badQuaternionRejected,
                    roundedW:roundedW,start:start,expectedStart:a[1],
                    midpoint:midpoint,expectedMid:(a[1]+b[1])/2,
                    end:end,expectedEnd:last[1],
                    rewind:rewind,rewindSeek:rewindSeek,
                    rewindStart:rewindStart,
                    seek:replay.seek,last:replay.last};"""
        )
        for actual,expected in (("start","expectedStart"),
                                ("midpoint","expectedMid"),
                                ("end","expectedEnd"),
                                ("rewind","expectedMid"),
                                ("rewindStart","expectedStart")):
            assert abs(playback[actual]-playback[expected])<0.03,playback
        assert playback["rewindSeek"]<playback["last"],playback
        assert playback["seek"]==0,playback
        assert playback["badQuaternionRejected"],playback
        assert abs(playback["roundedW"]-1)<0.01,playback
        assert abs(playback["isolatedX"]-7)<0.01,playback
        assert abs(playback["isolatedW"]-1)<0.01,playback
        assert playback["isolatedCount"]==2,playback
        assert abs(playback["duplicateForward"]-20)<0.01,playback
        assert abs(playback["duplicateRewind"]-20)<0.01,playback
        assert not errors(), "OSM replay interpolation WebGL error"
        cases+=1
        print("PASS replay: real r50 interpolation, end clamp and backward seek")

        # A recording from a previous page load must be accessible directly
        # from the main menu, without first driving another race. This also
        # checks that playback does not advance Gameplay or vehicle physics.
        driver.get(base + "?track=moat&quality=0&hud=1&laps=0")
        menu_saved = driver.execute_script("""var track=bkcore.hexgl.tracks.ChiangMaiMoat;
          var raw=localStorage.getItem('race-'+track.name+'-replay');
          return {visible:document.getElementById('menu-replay').style.display,
                  frames:raw ? JSON.parse(raw).length : 0};""")
        assert menu_saved['visible']!='none' and menu_saved['frames']>100,menu_saved
        driver.execute_script("document.getElementById('menu-replay').click()")
        WebDriverWait(driver,args.timeout).until(lambda d:d.execute_script(
            "return !!(window.hexGL && window.hexGL.replayViewer)"))
        history_view=driver.execute_script("""var g=window.hexGL,c=g.components.shipControls,
          viewer=g.replayViewer,frame=viewer.data.data[1];
          viewer.paused=true;
          g.seekReplay(frame[0]);
          var before=c.dummy.position.x, nitro=c.nitro;
          g.update();
          var after=c.dummy.position.x;
          var slider=document.getElementById('replay-seek');
          slider.value=String(frame[0]);
          slider.dispatchEvent(new Event('input',{bubbles:true}));
          return {fromMenu:viewer.fromMenu,paused:viewer.paused,
                  active:c.active,gameActive:g.gameplay.active,
                  scoreHidden:document.getElementById('step-5').style.display==='none',
                  controls:document.getElementById('replay-controls').style.display,
                  exitText:document.getElementById('replay-exit').textContent,
                  before:before,after:after,nitroSame:nitro===c.nitro};""")
        assert history_view['fromMenu'] and history_view['paused'],history_view
        assert not history_view['active'] and not history_view['gameActive'],history_view
        assert history_view['scoreHidden'] and history_view['controls']=='flex',history_view
        assert history_view['exitText']=='返回主菜单',history_view
        assert abs(history_view['before']-history_view['after'])<0.001 and history_view['nitroSame'],history_view
        driver.execute_script("document.getElementById('replay-exit').click()")
        WebDriverWait(driver,args.timeout).until(lambda d:d.execute_script(
            "return document.getElementById('step-1').style.display!=='none' && !window.hexGL"))
        # Corrupt and absent recordings should hide the shortcut on reload.
        driver.execute_script("""var name=bkcore.hexgl.tracks.ChiangMaiMoat.name;
          window.__testReplayKey='race-'+name+'-replay';
          sessionStorage.setItem('test-replay-backup',localStorage.getItem(window.__testReplayKey));
          localStorage.setItem(window.__testReplayKey,'broken-json');""")
        driver.refresh()
        bad_hidden=driver.execute_script("return document.getElementById('menu-replay').style.display==='none'")
        assert bad_hidden,'corrupt saved replay must hide main-menu entry'
        driver.execute_script("""var name=bkcore.hexgl.tracks.ChiangMaiMoat.name;
          localStorage.setItem('race-'+name+'-replay',sessionStorage.getItem('test-replay-backup'));
          sessionStorage.removeItem('test-replay-backup');""")
        assert not errors(), 'history replay WebGL error'
        cases+=1
        print('PASS history replay: cross-page menu entry, physics freeze, seek, exit, corrupt-save guard')

        # Both cars must drive the real OSM course through actual physics
        # simultaneously. The race ends as soon as P1 finishes; P2's
        # independent progress and the winner freeze must remain consistent.
        state=boot("?track=moat&quality=0&hud=1&laps=0&players=1")
        assert state["players"]==2 and state["moat"],state
        driver.set_script_timeout(120)
        duel=driver.execute_script(
            """var g=window.hexGL,cs=g.getShipControls(),gps=g.getGameplays(),
                   pts=g.track.analyser.route.points,n=pts.length;
            var progress=[0,0],impacts=[0,0],visited=[[],[]],last=[1,1],
                frames=0;
            g.raceOver=false;g.winner=-1;
            for(var k=0;k<2;k++){
                var c=cs[k],gp=gps[k];
                c.reset(gp.spawn,gp.spawnRotation);
                c.active=k===0;c.collisionDetection=true;c.speed=.27;
                gp.step=4;gp.active=true;gp.result=gp.results.NONE;
                gp.lap=1;gp.maxLaps=1;gp.lapTimes=[];
                gp.lapTimeElapsed=0;gp.nextCheckPointIndex=1;
                gp.previousCheckPoint=0;gp.timer.time.elapsed=0;
            }
            for(var i=0;i<15000 && !g.raceOver;i++){
                for(var k=0;k<2;k++){
                    if(k===1 && i<240)continue; // P2 starts four seconds later
                    var c=cs[k],gp=gps[k];
                    if(!c.active)c.active=true;
                    var best=Infinity,nearest=progress[k];
                    for(var j=Math.max(0,progress[k]-8);
                        j<=Math.min(n+8,progress[k]+10);j++){
                        var point=pts[j%n],dx=c.dummy.position.x-point[0],
                            dz=c.dummy.position.z-point[1],d=dx*dx+dz*dz;
                        if(d<best){best=d;nearest=j;}
                    }
                    if(nearest>progress[k])progress[k]=nearest;
                    var target=pts[(progress[k]+3)%n];
                    var desired=Math.atan2(target[0]-c.dummy.position.x,
                                            target[1]-c.dummy.position.z);
                    var actual=2*Math.atan2(c.dummy.quaternion.y,c.dummy.quaternion.w);
                    var err=((desired-actual+3*Math.PI)%(2*Math.PI))-Math.PI;
                    c.key.left=err>.04;c.key.right=err<-.04;
                    c.key.forward=true;
                    c.key.backward=Math.abs(err)>.23&&c.speed>.25;
                    c.key.ltrigger=err>.50&&c.speed>.30;
                    c.key.rtrigger=err<-.50&&c.speed>.30;
                    c.update(1);
                    if(c.collision.front)impacts[k]++;
                    gp.timer.time.elapsed+=1000/60;
                    if(i%3===0){
                        gp.modes.timeattack.call(gp);
                        if(last[k]!==gp.nextCheckPointIndex){
                            visited[k].push(gp.nextCheckPointIndex);
                            last[k]=gp.nextCheckPointIndex;
                        }
                    }
                    if(g.raceOver)break;
                }
                frames++;
            }
            for(var k=0;k<2;k++)cs[k].clearKeys();
            return {frames:frames,progress:progress,impacts:impacts,
                    visited:visited,winner:g.winner,raceOver:g.raceOver,
                    results:gps.map(function(p){return p.result;}),
                    expected:gps[0].results.FINISH,
                    active:cs.map(function(c){return c.active;}),
                    gameplayActive:gps.map(function(p){return p.active;}),
                    destroyed:cs.map(function(c){return c.destroyed;})};"""
        )
        assert duel["raceOver"] and duel["winner"]==0,duel
        assert duel["results"]==[duel["expected"],-1],duel
        assert duel["progress"][0]>=635 and duel["progress"][1]>=550,duel
        assert duel["visited"][0]==[2,3,0,1],duel
        assert duel["visited"][1][:3]==[2,3,0],duel
        assert max(duel["impacts"])<=15,duel
        assert not any(duel["active"]) and not any(duel["gameplayActive"]),duel
        assert not any(duel["destroyed"]),duel
        assert not errors(), "split-screen full physics race WebGL error"
        cases+=1
        print("PASS dual OSM physics race: P1 wins after %d frames; "
              "P2 independently reaches route point %d" %
              (duel["frames"],duel["progress"][1]))

        # Keep the expensive full-lap WebGL run from affecting the
        # following quality and fallback smoke scenarios.
        fresh_browser()
        state = boot("?track=moat&quality=2&hud=1&laps=0&players=0")
        assert state["moat"] and state["quality"] == 2
        assert not errors(), "higher-quality WebGL error"
        cases += 1
        print("PASS higher quality: loaded without WebGL errors")

        state = boot("?track=moat&quality=3&hud=1&laps=0&players=0")
        assert state["moat"] and state["quality"] == 3
        assert not errors(), "very-high-quality WebGL error"
        cases += 1
        print("PASS very high quality: particle resources and WebGL loaded")

        state = boot("?quality=0&hud=1&laps=0&players=0")
        assert state["track"] == "Cityscape" and not state["moat"]
        legacy_steer=driver.execute_script(
            "return window.hexGL.getShipControls()[0].angularSpeed")
        assert legacy_steer == 0.019, legacy_steer
        assert not errors(), "default Cityscape regression"
        cases += 1
        print("PASS default: Cityscape remains playable")
        assert driver.execute_script("return window.hexGL.cornerGuide === null"), "Cityscape guide must stay disabled"

        # Release quality-test WebGL contexts before the fallback series.
        fresh_browser()
        BLOCK_ROAD = True
        state = boot("?track=moat&quality=0&hud=1&laps=0&players=0")
        assert state["track"] == "Cityscape" and not state["moat"], state
        assert state["players"] == 1
        cases += 1
        print("PASS fallback: missing M2 road loads Cityscape")
        BLOCK_ROAD = False
        errors()  # discard the intentional fallback 404 before the next case

        # A 200 OK road response with invalid triangle indices used to pass
        # StaticModelLoader.build() and fail only when r50 uploads geometry.
        # The model validator must reject it before GPU work and invoke the
        # same complete Cityscape fallback as an HTTP 404.
        corrupt=json.loads((ROOT/"assets/tracks/chiangmai-moat/road.json").read_text(encoding="utf-8"))
        corrupt["meshes"][0]["indices"][2]=len(corrupt["meshes"][0]["positions"])//3+5
        ROTATED_ASSETS={
            "/assets/tracks/chiangmai-moat/road.json":
                json.dumps(corrupt,separators=(",",":")).encode()
        }
        state=boot("?track=moat&quality=0&hud=1&laps=0&players=0")
        assert state["track"]=="Cityscape" and not state["moat"],state
        assert not errors(),"corrupt M2 mesh must fall back before WebGL errors"
        ROTATED_ASSETS={}
        cases+=1
        print("PASS fallback: corrupt 200-OK M2 geometry rejected before GPU")

        # A 200-OK road.json may be structurally valid yet have the asphalt
        # displaced relative to the OSM route. StaticModelLoader accepts it,
        # but the race must not show an invisible/misaligned drivable road.
        fresh_browser()
        stale=json.loads((ROOT/"assets/tracks/chiangmai-moat/road.json").read_text(encoding="utf-8"))
        stale["meshes"][0]["positions"][0]+=100
        ROTATED_ASSETS={
            "/assets/tracks/chiangmai-moat/road.json":
                json.dumps(stale,separators=(",",":")).encode()
        }
        state=boot("?track=moat&quality=0&hud=1&laps=0&players=0")
        assert state["track"]=="Cityscape" and not state["moat"],state
        assert not errors(),"misaligned 200-OK asphalt must fall back safely"
        ROTATED_ASSETS={}
        cases+=1
        print("PASS fallback: 200-OK road asphalt mismatched with route")

        # In-range triangle indices with correct counts are valid JSON and
        # valid r50 geometry, but a scrambled strip can draw an asphalt
        # triangle straight across the old city while physics stays on OSM.
        fresh_browser()
        torn=json.loads((ROOT/"assets/tracks/chiangmai-moat/road.json").read_text(encoding="utf-8"))
        torn["meshes"][0]["indices"][0]=800
        ROTATED_ASSETS={
            "/assets/tracks/chiangmai-moat/road.json":
                json.dumps(torn,separators=(",",":")).encode()
        }
        state=boot("?track=moat&quality=0&hud=1&laps=0&players=0")
        assert state["track"]=="Cityscape" and not state["moat"],state
        assert not errors(),"misindexed asphalt must fall back before rendering"
        ROTATED_ASSETS={}
        cases+=1
        print("PASS fallback: in-range but misindexed asphalt rejected")

        # An otherwise valid asphalt strip may have a baked offset applied
        # by StaticModelLoader after vertex validation. The road then
        # renders away from the metre-based collision corridor.
        fresh_browser()
        offset_road=json.loads((ROOT/"assets/tracks/chiangmai-moat/road.json").read_text(encoding="utf-8"))
        offset_road["meshes"][0]["offset"]=[100,0,0]
        ROTATED_ASSETS={
            "/assets/tracks/chiangmai-moat/road.json":
                json.dumps(offset_road,separators=(",",":")).encode()
        }
        state=boot("?track=moat&quality=0&hud=1&laps=0&players=0")
        assert state["track"]=="Cityscape" and not state["moat"],state
        assert not errors(),"transformed asphalt must fall back before racing"
        ROTATED_ASSETS={}
        cases+=1
        print("PASS fallback: transformed 200-OK asphalt rejected")

        # A second named asphalt strip can be displaced while the first
        # matches all 650 centreline points. Never render two conflicting
        # driveable surfaces against a single collision corridor.
        fresh_browser()
        duplicate=json.loads((ROOT/"assets/tracks/chiangmai-moat/road.json").read_text(encoding="utf-8"))
        extra=json.loads(json.dumps(duplicate["meshes"][0]))
        extra["positions"][0]+=100
        duplicate["meshes"].append(extra)
        ROTATED_ASSETS={
            "/assets/tracks/chiangmai-moat/road.json":
                json.dumps(duplicate,separators=(",",":")).encode()
        }
        state=boot("?track=moat&quality=0&hud=1&laps=0&players=0")
        assert state["track"]=="Cityscape" and not state["moat"],state
        assert not errors(),"duplicate asphalt must fall back safely"
        ROTATED_ASSETS={}
        cases+=1
        print("PASS fallback: duplicate asphalt mesh rejected")

        # Opaque geometry with opacity=0 is still valid r50 JSON but leaves
        # the player driving on an invisible road.
        fresh_browser()
        invisible=json.loads((ROOT/"assets/tracks/chiangmai-moat/road.json").read_text(encoding="utf-8"))
        invisible["materials"][invisible["meshes"][0]["material"]]["opacity"]=0
        ROTATED_ASSETS={
            "/assets/tracks/chiangmai-moat/road.json":
                json.dumps(invisible,separators=(",",":")).encode()
        }
        state=boot("?track=moat&quality=0&hud=1&laps=0&players=0")
        assert state["track"]=="Cityscape" and not state["moat"],state
        assert not errors(),"invisible asphalt must fall back safely"
        ROTATED_ASSETS={}
        cases+=1
        print("PASS fallback: invisible asphalt material rejected")

        # Avoid retaining multiple Cityscape fallback renderer contexts.
        fresh_browser()
        # A 200-OK but invalid route-data.js used to abort registration of
        # ChiangMaiMoat, leaving the requested track missing at startup.
        # The new preflight must choose Cityscape before loading the road.
        invalid_route=json.loads((ROOT/"assets/tracks/chiangmai-moat/route.json").read_text(encoding="utf-8"))
        invalid_route["road_width_m"]=None
        ROTATED_ASSETS={
            "/assets/tracks/chiangmai-moat/route-data.js":
                ("var bkcore=bkcore||{};bkcore.hexgl=bkcore.hexgl||{};"
                 "bkcore.hexgl.MoatRouteData="+json.dumps(invalid_route)+";").encode()
        }
        state=boot("?track=moat&quality=0&hud=1&laps=0&players=0")
        assert state["track"]=="Cityscape" and not state["moat"],state
        assert not errors(),"invalid route must fall back before gameplay"
        ROTATED_ASSETS={}
        cases+=1
        print("PASS fallback: invalid 200-OK route metadata uses Cityscape")

        # Isolate corrupt-route fallback tests from the many earlier WebGL
        # scene loads. SwiftShader sometimes stalls late navigations without
        # a JS error when too many renderer contexts have been retained.
        fresh_browser()
        # A syntactically valid route with a checkpoint far outside the
        # road must not start an unwinnable race. Exercise the actual HTTP
        # asset/registration fallback, not only the Node VM path.
        invalid_route=json.loads((ROOT/"assets/tracks/chiangmai-moat/route.json").read_text(encoding="utf-8"))
        invalid_route["checkpoints"][2]["z"]+=100000
        ROTATED_ASSETS={
            "/assets/tracks/chiangmai-moat/route-data.js":
                ("var bkcore=bkcore||{};bkcore.hexgl=bkcore.hexgl||{};"
                 "bkcore.hexgl.MoatRouteData="+json.dumps(invalid_route)+";").encode()
        }
        state=boot("?track=moat&quality=0&hud=1&laps=0&players=0")
        assert state["track"]=="Cityscape" and not state["moat"],state
        assert not errors(),"off-road checkpoint must fall back before gameplay"
        ROTATED_ASSETS={}
        cases+=1
        print("PASS fallback: off-road OSM checkpoint rejected before gameplay")

        # Finite but extreme route coordinates previously made the 80m
        # bucket builder iterate millions of cells and hang the browser.
        # This is a real 200-OK asset; verify startup falls back promptly.
        invalid_route=json.loads((ROOT/"assets/tracks/chiangmai-moat/route.json").read_text(encoding="utf-8"))
        invalid_route["points"][12][0]+=1_000_000_000
        ROTATED_ASSETS={
            "/assets/tracks/chiangmai-moat/route-data.js":
                ("var bkcore=bkcore||{};bkcore.hexgl=bkcore.hexgl||{};"
                 "bkcore.hexgl.MoatRouteData="+json.dumps(invalid_route)+";").encode()
        }
        state=boot("?track=moat&quality=0&hud=1&laps=0&players=0")
        assert state["track"]=="Cityscape" and not state["moat"],state
        assert not errors(),"oversized spatial index must fall back without WebGL errors"
        ROTATED_ASSETS={}
        cases+=1
        print("PASS fallback: huge finite route segment rejected before index allocation")

        # Serve an in-memory 45-degree rotated *synthetic* course without
        # modifying the real tracked assets. This catches heading bugs
        # that an axis-aligned schematic cannot expose.
        spec=importlib.util.spec_from_file_location(
            "moat_blockout", ROOT/"tools"/"build_moat_blockout.py")
        builder=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(builder)
        angle=math.pi/4
        rotated=[(x*math.cos(angle)-z*math.sin(angle),
                  x*math.sin(angle)+z*math.cos(angle))
                 for x,z in builder.build_points()]
        start=min(range(len(rotated)),key=lambda i:
                  (rotated[i][0]-builder.HALF_WIDTH)**2+rotated[i][1]**2)
        rotated=rotated[start:]+rotated[:start]
        route=builder.metadata(rotated)
        route["source"]="synthetic rotated browser fixture (NOT OSM)"
        road=builder.model(rotated)
        ROTATED_ASSETS={
            "/assets/tracks/chiangmai-moat/road.json":
                json.dumps(road,separators=(",",":")).encode(),
            "/assets/tracks/chiangmai-moat/route-data.js":
                ("var bkcore=bkcore||{};bkcore.hexgl=bkcore.hexgl||{};"
                 "bkcore.hexgl.MoatRouteData="+json.dumps(route)+";").encode()
        }
        # The synthetic fixture is an independent geometry/physics test.
        fresh_browser()
        state=boot("?track=moat&quality=0&hud=1&laps=0&players=1")
        assert state["moat"] and state["players"]==2, state
        yaw=2*math.atan2(state["spawnYaw"]["y"],state["spawnYaw"]["w"])
        assert abs(yaw)>0.2, state
        a,b=state["spawns"]
        dx=b["x"]-a["x"];dz=b["z"]-a["z"]
        assert abs(dx*math.sin(yaw)+dz*math.cos(yaw))<0.05, state
        assert all(distance<49 for distance in state["corridorDistances"]), state
        WebDriverWait(driver,args.timeout).until(
            lambda d: d.execute_script(
                "return window.hexGL.getGameplays()[0].step===4"))
        driver.execute_script("window.hexGL.getShipControls()[0].key.forward=true;")
        # SwiftShader headless frame pacing varies significantly under load.
        # Wait for actual physical travel instead of assuming two wall-clock
        # seconds always execute enough ShipControls.update() frames.
        def travelled_forward(d):
            moved=d.execute_script(
                "var c=window.hexGL.getShipControls()[0],p=c.dummy.position;"
                "return {x:p.x,z:p.z,speed:c.speed,active:c.active,falling:c.falling,destroyed:c.destroyed,step:window.hexGL.getGameplays()[0].step};")
            dx=moved["x"]-a["x"];dz=moved["z"]-a["z"]
            return moved if dx*math.sin(yaw)+dz*math.cos(yaw)>2 else False
        moved=WebDriverWait(driver,args.timeout).until(travelled_forward)
        dx=moved["x"]-a["x"];dz=moved["z"]-a["z"]
        assert abs(dx*math.cos(yaw)-dz*math.sin(yaw))<2.5, (state,moved)
        rotated_errors=errors()
        assert not rotated_errors, rotated_errors
        ROTATED_ASSETS={}
        cases+=1
        print("PASS rotated course: tangent-aligned spawn and physics travel")

        # Audio is optional: a missing music file previously kept the asset
        # counter pending forever, leaving players stuck at the loading
        # screen. Exercise the real browser's XHR/decode and game lifecycle.
        fresh_browser()
        BLOCK_AUDIO = True
        state = boot("?track=moat&quality=0&hud=1&laps=0&players=0")
        assert state["moat"], state
        audio_state = driver.execute_script("""var g=window.hexGL;
          var failed=bkcore.Audio.sounds.bg;
          g.restartRace();
          return {failed:failed.failed,loaded:g.track.lib.progress.loaded,
            total:g.track.lib.progress.total,
            gameplay:!!g.gameplay};""")
        assert audio_state["failed"] is True, audio_state
        assert audio_state["loaded"] == audio_state["total"], audio_state
        assert audio_state["gameplay"], audio_state
        other_errors = [msg for msg in errors() if "audio/bg.ogg" not in msg]
        assert not other_errors, other_errors
        BLOCK_AUDIO = False
        cases += 1
        print("PASS optional audio 404: WebGL boots and race restarts with silent music")

        # A missing HUD PNG or postprocessing texture previously left the
        # Loader counter pending forever. Verify real r50 rendering still
        # accepts the drawable fallback, including the restart lifecycle.
        fresh_browser()
        BLOCK_VISUAL = True
        state = boot("?track=moat&quality=0&hud=1&laps=0&players=0")
        assert state["moat"], state
        visual_state = driver.execute_script("""var g=window.hexGL,lib=g.track.lib;
          var texture=lib.get('textures','hex'),hud=lib.get('images','hud.bg');
          g.restartRace();
          return {loaded:lib.progress.loaded,total:lib.progress.total,
            finished:lib.progress.finished,
            textureFallback:!!texture.image && texture.image.tagName==='CANVAS',
            textureReady:texture.needsUpdate,
            hudFallback:hud.tagName==='CANVAS',
            hudRatio:hud.width/hud.height,gameplay:!!g.gameplay};""")
        assert visual_state["loaded"] == visual_state["total"], visual_state
        assert visual_state["finished"] and visual_state["gameplay"], visual_state
        assert visual_state["textureFallback"] and visual_state["hudFallback"], visual_state
        assert abs(visual_state["hudRatio"] - 1920/250) < 0.001, visual_state
        # needsUpdate can be reset by the renderer after the GPU upload.
        other_errors = [msg for msg in errors() if not any(path in msg for path in (
            "textures/hud/hex.jpg", "textures/hud/hud-bg.png",
            "Error loading hex.", "Error loading hud.bg."))]
        assert not other_errors, other_errors
        BLOCK_VISUAL = False
        cases += 1
        print("PASS optional visual 404: r50 texture/HUD fallback boots and restarts")

        # r50's ImageUtils.loadTextureCube lacks an error handler. A missing
        # face must not strand loading or produce mismatched cube dimensions.
        fresh_browser()
        BLOCK_CUBEMAP = True
        state = boot("?track=moat&quality=0&hud=1&laps=0&players=0")
        assert state["moat"], state
        cube_state = driver.execute_script("""var g=window.hexGL,lib=g.track.lib;
          var cube=lib.get('texturesCube','skybox.dawnclouds');
          g.restartRace();
          return {loaded:lib.progress.loaded,total:lib.progress.total,
            finished:lib.progress.finished,gameplay:!!g.gameplay,
            faces:cube.image.map(function(im) {
              return {tag:im.tagName,width:im.width,height:im.height};
            })};""")
        assert cube_state["loaded"] == cube_state["total"], cube_state
        assert cube_state["finished"] and cube_state["gameplay"], cube_state
        assert len(cube_state["faces"]) == 6, cube_state
        assert all(face == {"tag":"CANVAS","width":2,"height":2}
                   for face in cube_state["faces"]), cube_state
        other_errors = [msg for msg in errors() if not any(path in msg for path in (
            "textures/skybox/dawnclouds/nx.jpg", "Error loading skybox.dawnclouds."))]
        assert not other_errors, other_errors
        BLOCK_CUBEMAP = False
        cases += 1
        print("PASS skybox face 404: r50 cube fallback boots and restarts")

        # r50 JSONLoader has no HTTP error callback. A missing legacy
        # booster geometry must not strand the M2 game at the loading UI.
        fresh_browser()
        BLOCK_GEOMETRY = True
        state = boot("?track=moat&quality=0&hud=1&laps=0&players=0")
        assert state["moat"], state
        geometry_state = driver.execute_script("""var g=window.hexGL,lib=g.track.lib;
          var geom=lib.get('geometries','booster');
          g.restartRace();
          return {loaded:lib.progress.loaded,total:lib.progress.total,
            finished:lib.progress.finished,gameplay:!!g.gameplay,
            empty:!!geom && geom.faces.length===0 && geom.vertices.length===0};""")
        assert geometry_state["loaded"] == geometry_state["total"], geometry_state
        assert geometry_state["finished"] and geometry_state["gameplay"], geometry_state
        assert geometry_state["empty"], geometry_state
        other_errors = [msg for msg in errors() if not any(path in msg for path in (
            "geometries/booster/booster.js", "Error loading booster."))]
        assert not other_errors, other_errors
        BLOCK_GEOMETRY = False
        cases += 1
        print("PASS legacy geometry 404: empty r50 mesh fallback boots and restarts")

        # Unlike the optional booster, the Cityscape road mesh is a
        # required gameplay asset. A 404 must fail closed and retry must
        # recover after the missing resource becomes available.
        fresh_browser()
        BLOCK_CORE_GEOMETRY = True
        driver.get(base + "?quality=0&hud=1&laps=0&players=0")
        driver.execute_script(
            "document.getElementById('start').click();"
            "document.getElementById('step-2').click();"
        )
        WebDriverWait(driver, args.timeout).until(
            lambda d: d.execute_script(
                "return document.getElementById('load-error').style.display==='block'"
            )
        )
        WebDriverWait(driver, args.timeout).until(
            lambda d: d.execute_script(
                "return window.hexGL.track.lib.progress.finished"
            )
        )
        required_state = driver.execute_script("""var g=window.hexGL,lib=g.track.lib;
          return {failed:lib.progress.failed,failures:lib.progress.failures,
            loaded:lib.progress.loaded,total:lib.progress.total,
            game:document.getElementById('step-4').style.display,
            message:document.getElementById('load-error-detail').textContent};""")
        assert required_state["failed"], required_state
        assert required_state["failures"] == ["track.cityscape"], required_state
        assert required_state["loaded"] == required_state["total"], required_state
        assert required_state["game"] != "block", required_state
        assert "已停止比赛" in required_state["message"], required_state
        BLOCK_CORE_GEOMETRY = False
        driver.find_element("id", "load-retry").click()
        WebDriverWait(driver, args.timeout).until(
            lambda d: d.execute_script(
                "return document.getElementById('step-1').style.display!=='none'"
            )
        )
        driver.execute_script(
            "document.getElementById('start').click();"
            "document.getElementById('step-2').click();"
        )
        WebDriverWait(driver, args.timeout).until(
            lambda d: d.execute_script(
                "return document.getElementById('step-4').style.display==='block'"
            )
        )
        assert driver.execute_script(
            "return !window.hexGL.track.lib.progress.failed && "
            "window.hexGL.track.lib.get('geometries','track.cityscape').faces.length>0"
        )
        cases += 1
        print("PASS mandatory Cityscape road 404: safe stop and retry recovery")

        # Cityscape's collision and height analysers are mandatory physics
        # inputs. A 404 must show an actionable error, never start a race
        # with missing collision or silently substitute zero pixels.
        for kind in ("collision", "height"):
            fresh_browser()
            BLOCK_ANALYSER = "/textures/tracks/cityscape/%s.png" % kind
            driver.get(base + "?quality=0&hud=1&laps=0&players=0")
            driver.execute_script(
                "document.getElementById('start').click();"
                "document.getElementById('step-2').click();"
            )
            WebDriverWait(driver, args.timeout).until(
                lambda d: d.execute_script(
                    "return document.getElementById('load-error').style.display==='block'"
                )
            )
            failure = driver.execute_script("""var g=window.hexGL,lib=g.track.lib;
              return {fatal:lib.progress.failed,failures:lib.progress.failures,
                loaded:lib.progress.loaded,total:lib.progress.total,
                gameVisible:document.getElementById('step-4').style.display,
                message:document.getElementById('load-error-detail').textContent,
                analyser:lib.get('analysers','track.cityscape.%s').loaded};""" % kind)
            assert failure["fatal"], failure
            assert failure["failures"] == ["track.cityscape.%s" % kind], failure
            assert failure["gameVisible"] != "block", failure
            assert not failure["analyser"], failure
            assert "已停止比赛" in failure["message"], failure
            WebDriverWait(driver, args.timeout).until(
                lambda d: d.execute_script(
                    "return window.hexGL.track.lib.progress.finished"
                )
            )
            other_errors = [msg for msg in errors() if not any(path in msg for path in (
                "cityscape/%s.png" % kind, "Error loading track.cityscape.%s." % kind))]
            assert not other_errors, other_errors
            BLOCK_ANALYSER = None
            # The retry action must actually reload a clean menu.
            driver.find_element("id", "load-retry").click()
            WebDriverWait(driver, args.timeout).until(
                lambda d: d.execute_script(
                    "return document.getElementById('start') !== null &&"
                    " document.getElementById('load-error').style.display==='none'"
                )
            )
            cases += 1
            print("PASS mandatory %s 404: visible fatal error, no unsafe race, retry" % kind)

        print("PASS %d headless WebGL smoke scenarios" % cases)
    finally:
        if driver:
            driver.quit()
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
