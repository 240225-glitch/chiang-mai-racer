#!/usr/bin/env python3
"""Focused Chrome WebGL regression for mandatory Cityscape physics images.

Run from repository root: python3 tests/browser_analyser_failures.py
Uses a local HTTP server and never touches deployed sites.
"""
import os
import shutil
import threading

import browser_smoke as smoke
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait


def main():
    os.environ["NO_PROXY"] = "localhost,127.0.0.1"
    os.environ["no_proxy"] = "localhost,127.0.0.1"
    server = smoke.http.server.ThreadingHTTPServer(("127.0.0.1", 0), smoke.Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = "http://127.0.0.1:%d/" % server.server_address[1]
    options = Options()
    options.binary_location = shutil.which("google-chrome") or shutil.which("chromium")
    if not options.binary_location:
        raise SystemExit("Chrome/Chromium not installed")
    for flag in ("--headless=new", "--no-sandbox", "--disable-dev-shm-usage",
                 "--enable-unsafe-swiftshader", "--use-gl=angle",
                 "--use-angle=swiftshader", "--window-size=1280,800",
                 "--autoplay-policy=no-user-gesture-required"):
        options.add_argument(flag)
    driver = None
    try:
        for kind in ("collision", "height"):
            if driver is not None:
                driver.quit()
            driver = webdriver.Chrome(options=options)
            driver.execute_cdp_cmd("Network.enable", {})
            driver.execute_cdp_cmd("Network.setCacheDisabled", {"cacheDisabled": True})
            smoke.BLOCK_ANALYSER = "/textures/tracks/cityscape/%s.png" % kind
            driver.get(base + "?quality=0&hud=1&laps=0&players=0")
            driver.execute_script(
                "document.getElementById('start').click();"
                "document.getElementById('step-2').click();"
            )
            WebDriverWait(driver, 60).until(
                lambda d: d.execute_script(
                    "return document.getElementById('load-error').style.display==='block'"
                )
            )
            WebDriverWait(driver, 60).until(
                lambda d: d.execute_script(
                    "return window.hexGL.track.lib.progress.finished"
                )
            )
            state = driver.execute_script("""var g=window.hexGL,lib=g.track.lib;
                return {failed:lib.progress.failed,failures:lib.progress.failures,
                  loaded:lib.progress.loaded,total:lib.progress.total,
                  game:document.getElementById('step-4').style.display,
                  imageLoaded:lib.get('analysers','track.cityscape.%s').loaded,
                  message:document.getElementById('load-error-detail').textContent};""" % kind)
            assert state["failed"] and state["loaded"] == state["total"], state
            assert state["failures"] == ["track.cityscape.%s" % kind], state
            assert state["game"] != "block" and not state["imageLoaded"], state
            assert "已停止比赛" in state["message"], state
            smoke.BLOCK_ANALYSER = None
            driver.find_element("id", "load-retry").click()
            WebDriverWait(driver, 60).until(
                lambda d: d.execute_script(
                    "return document.getElementById('load-error').style.display==='none'"
                )
            )
            # A retry is only useful if the restored assets actually allow
            # the original Cityscape race to start with valid physics maps.
            driver.execute_script(
                "document.getElementById('start').click();"
                "document.getElementById('step-2').click();"
            )
            WebDriverWait(driver, 60).until(
                lambda d: d.execute_script(
                    "return document.getElementById('step-4').style.display==='block'"
                )
            )
            restored = driver.execute_script("""var lib=window.hexGL.track.lib;
                return {failed:lib.progress.failed,
                  collision:lib.get('analysers','track.cityscape.collision').loaded,
                  height:lib.get('analysers','track.cityscape.height').loaded};""")
            assert not restored["failed"] and restored["collision"] and restored["height"], restored
            print("PASS mandatory %s image 404: fatal UI, physics safety, retry and recovery" % kind,
                  flush=True)
        print("PASS 2/2 focused Chrome WebGL analyser regressions", flush=True)
    finally:
        smoke.BLOCK_ANALYSER = None
        if driver:
            driver.quit()
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
