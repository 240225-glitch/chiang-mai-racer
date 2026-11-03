#!/usr/bin/env python3
"""Extract OSM footprints for the Wat Chedi Luang landmark blockout.

The checked-in geometry is ODbL map data. The game meshes generated from it
are procedural visual approximations, not scans or surveyed architecture.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path

from osm_outer_ring import LICENSE, OSM_API_URL, SOURCE

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROUTE = ROOT / "assets/tracks/chiangmai-moat/route.json"
# Stable OSM way IDs from the same official API snapshot as the race route.
FEATURES = (
    ("compound", "243018795", "Wat Chedi Luang temple grounds",
     {"amenity": "place_of_worship", "name:en": "Wat Chedi Luang"}),
    ("stupa", "93413945", "Wat Chedi Luang Stupa",
     {"man_made": "stupa", "historic": "ruins", "tourism": "attraction"}),
    ("viharn", "93413944", "Pra Wihan Luang",
     {"building": "yes", "historic": "yes"}),
    ("city-pillar-shrine", "441418807", "Ho Inthakhin City Pillar Shrine",
     {"amenity": "place_of_worship", "building": "yes"}),
)


def _project(lon, lat):
    earth = 6371008.8
    center_lat = math.radians(18.7883)
    return (
        earth * math.cos(center_lat) * math.radians(lon - 98.9855),
        -earth * math.radians(lat - 18.7883),
    )


def _inside(point, polygon):
    x, z = point
    inside = False
    for i, a in enumerate(polygon):
        b = polygon[(i + 1) % len(polygon)]
        if ((a[1] > z) != (b[1] > z)) and (
            x < (b[0] - a[0]) * (z - a[1]) / (b[1] - a[1]) + a[0]
        ):
            inside = not inside
    return inside


def extract(osm_path, route_path=DEFAULT_ROUTE):
    osm_path = Path(osm_path)
    route_path = Path(route_path)
    route = json.loads(route_path.read_text(encoding="utf-8"))
    actual_sha = hashlib.sha256(osm_path.read_bytes()).hexdigest()
    if route.get("osm_snapshot_sha256") != actual_sha:
        raise ValueError("OSM XML does not match checked-in route snapshot SHA-256")

    root = ET.parse(osm_path).getroot()
    if root.tag != "osm":
        raise ValueError("expected OSM XML")
    nodes = {
        node.attrib["id"]: (float(node.attrib["lon"]), float(node.attrib["lat"]))
        for node in root.findall("node")
    }
    ways = {way.attrib["id"]: way for way in root.findall("way")}

    extracted = []
    local_polygons = {}
    for role, way_id, fallback_name, required in FEATURES:
        way = ways.get(way_id)
        if way is None:
            raise ValueError("missing OSM landmark way: " + way_id)
        tags = {tag.attrib["k"]: tag.attrib["v"] for tag in way.findall("tag")}
        if any(tags.get(key) != value for key, value in required.items()):
            raise ValueError("OSM landmark identity/tags changed: " + way_id)

        refs = [nd.attrib["ref"] for nd in way.findall("nd")]
        if len(refs) < 5 or refs[0] != refs[-1] or any(ref not in nodes for ref in refs):
            raise ValueError("landmark way must be a closed polygon: " + way_id)
        coords = [nodes[ref] for ref in refs]
        local = [_project(lon, lat) for lon, lat in coords[:-1]]
        if len(set(local)) < 4 or any(
            math.dist(local[i], local[(i + 1) % len(local)]) < 0.15
            for i in range(len(local))
        ):
            raise ValueError("degenerate OSM landmark polygon: " + way_id)
        if any(abs(x) > 500 or abs(z) > 500 for x, z in local):
            raise ValueError("landmark polygon outside Wat Chedi Luang vicinity")

        # Reject self-crossing rings before writing a source asset.
        area = sum(
            local[i][0] * local[(i + 1) % len(local)][1]
            - local[(i + 1) % len(local)][0] * local[i][1]
            for i in range(len(local))
        )
        if abs(area) < 4:
            raise ValueError("collapsed OSM landmark polygon: " + way_id)

        name = tags.get("name:en") or tags.get("name") or fallback_name
        feature = {
            "type": "Feature",
            "properties": {
                "role": role,
                "osm_way_id": way_id,
                "name": name,
                "name:en": tags.get("name:en", fallback_name),
                "osm_tags": {
                    key: tags[key] for key in (
                        "amenity", "building", "building:levels", "height",
                        "historic", "man_made", "tourism", "religion",
                    ) if key in tags
                },
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [round(lon, 8), round(lat, 8)] for lon, lat in coords
                ]],
            },
        }
        extracted.append(feature)
        local_polygons[role] = local

    compound = local_polygons["compound"]
    for role, polygon in local_polygons.items():
        if role == "compound":
            continue
        center = (
            sum(x for x, _ in polygon) / len(polygon),
            sum(z for _, z in polygon) / len(polygon),
        )
        if not _inside(center, compound):
            raise ValueError("landmark centroid falls outside temple compound: " + role)

    return {
        "type": "FeatureCollection",
        "properties": {
            "source": SOURCE,
            "license": LICENSE,
            "source_url": "https://www.openstreetmap.org/copyright",
            "source_api_url": OSM_API_URL,
            "snapshot_sha256": actual_sha,
            "selection": "four explicitly tagged OSM ways inside Wat Chedi Luang compound",
            "geometry_status": "OSM footprints only; no OSM 3D model or surveyed height",
            "model_status": "procedural low-poly visual blockout; not an architectural reconstruction",
            "feature_count": len(extracted),
        },
        "features": extracted,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--osm-xml", required=True, type=Path)
    parser.add_argument("--route", default=DEFAULT_ROUTE, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--snapshot-date")
    args = parser.parse_args()

    data = extract(args.osm_xml, args.route)
    if args.snapshot_date:
        datetime.date.fromisoformat(args.snapshot_date)
        data["properties"]["snapshot_date_utc"] = args.snapshot_date
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    print("Extracted %d OSM Wat Chedi Luang footprints" % len(data["features"]))


if __name__ == "__main__":
    main()
