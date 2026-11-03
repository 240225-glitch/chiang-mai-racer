#!/usr/bin/env python3
"""Focused Chrome 148 SwiftShader test for silent/stalled optional image requests.

Serves the local repository only; no external requests or production changes.
"""
import os
import shutil
import threading
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
import browser_smoke as smoke

STALLED = {"/textures/hud/hex.jpg", "/textures/hud/hud-bg.png"}

class StallHandler(smoke.Handler):
    def do_GET(self):
        if self.path.split("?")[0] in STALLED:
            # Deliberately never return before the 15s Loader watchdog.
            time.sleep(45)
            return
        return super().do_GET()

def main():
    os.environ["NO_PROXY"] = "localhost,127.0.0.1"
    os.environ["no_proxy"] = "localhost,127.0.0.1"
    browser = shutil.which("google-chrome") or shutil.which("chromium")
    if not browser:
        raise SystemExit("Chrome/Chromium not installed")
    server = smoke.http.server.ThreadingHTTPServer(("127.0.0.1", 0), StallHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    opts = Options()
    opts.binary_location = browser
    for flag in ("--headless=new", "--no-sandbox", "--disable-dev-shm-usage",
                 "--enable-unsafe-swiftshader", "--use-gl=angle", "--use-angle=swiftshader",
                 "--window-size=1280,800", "--autoplay-policy=no-user-gesture-required"):
        opts.add_argument(flag)
    driver = None
    try:
        driver = webdriver.Chrome(options=opts)
        driver.get("http://127.0.0.1:%d/?track=moat&quality=0&hud=1&laps=0" % server.server_address[1])
        driver.execute_script("document.getElementById('start').click();document.getElementById('step-2').click();")
        WebDriverWait(driver, 60).until(lambda d: d.execute_script(
            "return document.getElementById('step-4').style.display==='block'"))
        state = driver.execute_script("""var g=window.hexGL,lib=g.track.lib;
          var tex=lib.get('textures','hex'),hud=lib.get('images','hud.bg');
          g.restartRace();
          return {moat:!!g.track.moatMode,loaded:lib.progress.loaded,
            total:lib.progress.total,finished:lib.progress.finished,
            texture:!!tex.image&&tex.image.tagName==='CANVAS',
            hud:hud.tagName==='CANVAS',ratio:hud.width/hud.height,
            gameplay:!!g.gameplay};""")
        assert state['moat'] and state['finished'] and state['gameplay'], state
        assert state['loaded'] == state['total'], state
        assert state['texture'] and state['hud'], state
        assert abs(state['ratio'] - 1920/250) < 0.001, state
        print('PASS Chrome WebGL: stalled texture and HUD requests time out safely; restart works', flush=True)
    finally:
        if driver is not None:
            driver.quit()
        server.shutdown()
        server.server_close()

if __name__ == '__main__':
    main()
