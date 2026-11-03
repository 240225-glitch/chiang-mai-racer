#!/usr/bin/env python3
"""Chrome WebGL: a silent OSM road request must recover to Cityscape.

Local-only HTTP stall; does not touch the production website.
"""
import os
import shutil
import threading
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
import browser_smoke as smoke

class StallRoadHandler(smoke.Handler):
    def do_GET(self):
        if self.path.split('?')[0] == '/assets/tracks/chiangmai-moat/road.json':
            time.sleep(45)
            return
        return super().do_GET()

def main():
    os.environ['NO_PROXY'] = 'localhost,127.0.0.1'
    os.environ['no_proxy'] = 'localhost,127.0.0.1'
    chrome = shutil.which('google-chrome') or shutil.which('chromium')
    if not chrome:
        raise SystemExit('Chrome/Chromium not installed')
    server = smoke.http.server.ThreadingHTTPServer(('127.0.0.1', 0), StallRoadHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    opts = Options()
    opts.binary_location = chrome
    for flag in ('--headless=new', '--no-sandbox', '--disable-dev-shm-usage',
                 '--enable-unsafe-swiftshader', '--use-gl=angle',
                 '--use-angle=swiftshader', '--window-size=1280,800',
                 '--autoplay-policy=no-user-gesture-required'):
        opts.add_argument(flag)
    driver = None
    try:
        driver = webdriver.Chrome(options=opts)
        driver.get('http://127.0.0.1:%d/?track=moat&quality=0&hud=1&laps=0' % server.server_address[1])
        started = time.monotonic()
        driver.execute_script("document.getElementById('start').click();document.getElementById('step-2').click();")
        WebDriverWait(driver, 70).until(lambda d: d.execute_script(
            "return document.getElementById('step-4').style.display==='block'"))
        elapsed = time.monotonic() - started
        state = driver.execute_script("""var g=window.hexGL,lib=g.track.lib;
          g.restartRace();
          return {track:g.track.name,moat:!!g.track.moatMode,
            loaded:lib.progress.loaded,total:lib.progress.total,
            failed:lib.progress.failed,road:!!lib.get('geometries','track.cityscape'),
            gameplay:!!g.gameplay};""")
        assert not state['moat'] and state['track']=='Cityscape', state
        assert state['loaded']==state['total'] and not state['failed'], state
        assert state['road'] and state['gameplay'], state
        assert elapsed < 44, (elapsed, state)
        print('PASS Chrome WebGL: silent OSM road request recovered to playable Cityscape in %.1fs' % elapsed, flush=True)
    finally:
        if driver is not None:
            driver.quit()
        server.shutdown()
        server.server_close()

if __name__ == '__main__':
    main()
