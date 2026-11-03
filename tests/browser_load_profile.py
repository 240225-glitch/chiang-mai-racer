#!/usr/bin/env python3
"""Repeatable local Chrome loading profile for Cityscape and OSM Chiang Mai.

No deployment, no external network, no GPU claim. Reports Chrome's Navigation
Timing / Resource Timing and JS heap after the actual game-ready screen.
Use --samples 3 for medians. SwiftShader measures CPU software WebGL only.
"""
from __future__ import annotations

import argparse
import http.server
import json
import os
from pathlib import Path
import shutil
import statistics
import threading

ROOT = Path(__file__).resolve().parents[1]


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, *args):
        pass


def median(values):
    return round(statistics.median(values), 2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--out", type=Path, help="optional JSON report path")
    args = parser.parse_args()
    if not 1 <= args.samples <= 10:
        parser.error("--samples must be between 1 and 10")
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.support.ui import WebDriverWait

    binary = shutil.which("google-chrome") or shutil.which("chromium")
    if not binary:
        raise SystemExit("Chrome or Chromium not installed")
    os.environ["NO_PROXY"] = "localhost,127.0.0.1"
    os.environ["no_proxy"] = "localhost,127.0.0.1"
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = "http://127.0.0.1:%d/" % server.server_address[1]
    options = Options()
    options.binary_location = binary
    for flag in ("--headless=new", "--no-sandbox", "--disable-dev-shm-usage",
                 "--enable-unsafe-swiftshader", "--use-gl=angle",
                 "--use-angle=swiftshader", "--window-size=1280,800",
                 "--enable-precise-memory-info",
                 "--autoplay-policy=no-user-gesture-required"):
        options.add_argument(flag)
    options.set_capability("goog:loggingPrefs", {"browser": "ALL"})
    report = {"renderer": "Chrome headless SwiftShader (software WebGL)",
              "method": "fresh page, HTTP cache disabled, localhost static server",
              "samples_per_track": args.samples, "tracks": {}}
    driver = None
    try:
        for name, query in (("moat", "?track=moat&quality=0&hud=1&laps=0&players=0"),
                            ("cityscape", "?quality=0&hud=1&laps=0&players=0")):
            results = []
            for i in range(args.samples):
                # Fresh Chrome process for every sample: otherwise the JS heap
                # grows across navigations and track comparisons are invalid.
                driver = webdriver.Chrome(options=options)
                report["browser_version"] = driver.capabilities.get("browserVersion")
                driver.execute_cdp_cmd("Network.enable", {})
                driver.execute_cdp_cmd("Network.setCacheDisabled", {"cacheDisabled": True})
                driver.set_page_load_timeout(args.timeout)
                driver.get(base + query)
                # The game-ready screen appears only after assets are loaded.
                driver.execute_script(
                    "document.getElementById('start').click();"
                    "document.getElementById('step-2').click();"
                )
                WebDriverWait(driver, args.timeout).until(
                    lambda d: d.execute_script(
                        "return document.getElementById('step-4').style.display==='block'"
                    )
                )
                sample = driver.execute_script("""
                    var entries=performance.getEntriesByType('resource');
                    var nav=performance.getEntriesByType('navigation')[0];
                    return {
                        ready_ms: performance.now(),
                        navigation_load_ms: nav ? nav.loadEventEnd-nav.startTime : null,
                        resource_count: entries.length,
                        resource_transfer_bytes: entries.reduce(function(s,e){
                            return s+(e.transferSize||0);
                        },0),
                        resource_encoded_bytes: entries.reduce(function(s,e){
                            return s+(e.encodedBodySize||0);
                        },0),
                        js_heap_bytes: performance.memory ? performance.memory.usedJSHeapSize : null,
                        moat: !!(window.hexGL && window.hexGL.track.moatMode),
                        road: !!(window.hexGL && window.hexGL.track.roadModel)
                    };
                """)
                assert sample["ready_ms"] > 0 and sample["resource_count"] > 0, sample
                assert sample["moat"] == (name == "moat"), sample
                if name == "moat":
                    assert sample["road"], sample
                severe = [x["message"] for x in driver.get_log("browser")
                          if x["level"] == "SEVERE" and "/favicon.ico" not in x["message"]]
                if severe:
                    raise AssertionError("browser console error: " + str(severe[:3]))
                results.append(sample)
                print("%s sample %d: ready %.0f ms, %d resources, %.1f MiB transfer, %.1f MiB JS heap" %
                      (name, i+1, sample["ready_ms"], sample["resource_count"],
                       sample["resource_transfer_bytes"]/1048576,
                       (sample["js_heap_bytes"] or 0)/1048576), flush=True)
                driver.quit()
                driver = None
            report["tracks"][name] = {
                "samples": results,
                "median": {key: median([r[key] for r in results])
                           for key in ("ready_ms", "resource_count",
                                       "resource_transfer_bytes", "resource_encoded_bytes",
                                       "js_heap_bytes")}
            }
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False)+"\n",
                                encoding="utf-8")
        print("MEDIANS:", json.dumps({k:v["median"] for k,v in report["tracks"].items()}))
    finally:
        if driver is not None:
            driver.quit()
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
