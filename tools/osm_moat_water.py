#!/usr/bin/env python3
"""Extract closed OSM natural=water, water=moat polygons for Chiang Mai.

Input: official OSM API XML snapshot. Output: attributed GeoJSON features.
No third-party dependencies and no invented moat geometry.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path

from osm_outer_ring import LICENSE, OSM_API_URL, SOURCE


def extract(path):
    root = ET.parse(path).getroot()
    if root.tag != "osm":
        raise ValueError("expected OSM XML")
    nodes = {
        n.attrib["id"]: [float(n.attrib["lon"]), float(n.attrib["lat"])]
        for n in root.findall("node")
    }
    features = []
    for way in root.findall("way"):
        tags = {t.attrib["k"]: t.attrib["v"] for t in way.findall("tag")}
        if tags.get("natural") != "water" or tags.get("water") != "moat":
            continue
        refs = [n.attrib["ref"] for n in way.findall("nd")]
        if len(refs) < 4 or refs[0] != refs[-1]:
            raise ValueError("OSM moat polygon is not closed: " + way.attrib["id"])
        if any(ref not in nodes for ref in refs):
            raise ValueError("missing OSM water node: " + way.attrib["id"])
        ring = [nodes[ref] for ref in refs]
        features.append({
            "type": "Feature",
            "properties": {"osm_way_id": way.attrib["id"], "water": "moat"},
            "geometry": {"type": "Polygon", "coordinates": [ring]}
        })
    if not features:
        raise ValueError("no OSM water=moat polygons found")
    features.sort(key=lambda f: int(f["properties"]["osm_way_id"]))
    return {
        "type": "FeatureCollection",
        "properties": {
            "source": SOURCE,
            "license": LICENSE,
            "source_url": "https://www.openstreetmap.org/copyright",
            "source_api_url": OSM_API_URL,
            "snapshot_sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest(),
            "review_status": "OSM-derived water polygons; field review pending"
        },
        "features": features
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--osm-xml", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--snapshot-date")
    args = parser.parse_args()
    result = extract(args.osm_xml)
    if args.snapshot_date:
        import datetime
        datetime.date.fromisoformat(args.snapshot_date)
        result["properties"]["snapshot_date_utc"] = args.snapshot_date
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
    print("Extracted %d OSM moat water polygons" % len(result["features"]))


if __name__ == "__main__":
    main()
