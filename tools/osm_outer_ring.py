#!/usr/bin/env python3
"""Extract a reproducible, directed Chiang Mai outer-moat loop from OSM XML.

Input is a saved OpenStreetMap API 0.6 /map XML snapshot (not live Overpass).
Only tagged one-way secondary roads around the moat are eligible. We walk
actual shared OSM node IDs; no invented joins or straight-line gaps.

The route is a candidate for visual/traffic-direction review, not a claim
that OSM data has been independently surveyed on site.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import heapq
import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path

from build_moat_blockout import (
    CENTER_LAT, CENTER_LON, import_geojson, perimeter, validate_simple_loop,
)

EARTH_RADIUS = 6371008.8
LAT_SCALE = EARTH_RADIUS * math.pi / 180
LON_SCALE = LAT_SCALE * math.cos(math.radians(CENTER_LAT))
# The actual clockwise outer carriageways; inner lanes run the other way.
OUTER_ROADS = (
    "Kotchasarn Road", "Chang Lo Road", "Bun Rueang Rit Road",
    "Mani Noppharat Road", "Chayiaphoom Road",
)
ANCHORS = (
    ("Kotchasarn Road", (850, 0)),      # east, southbound
    ("Chang Lo Road", (0, 800)),        # south, westbound
    ("Bun Rueang Rit Road", (-810, 0)), # west, northbound
    ("Mani Noppharat Road", (0, -830)), # north, eastbound
)
SOURCE = "© OpenStreetMap contributors"
LICENSE = "Open Database License (ODbL) 1.0"
OSM_API_URL = "https://www.openstreetmap.org/api/0.6/map?bbox=98.977,18.780,98.994,18.797"


def world(lat, lon):
    return ((lon - CENTER_LON) * LON_SCALE, (CENTER_LAT - lat) * LAT_SCALE)


def parse_osm(path):
    root = ET.parse(path).getroot()
    if root.tag != "osm":
        raise ValueError("expected OSM XML <osm> root")
    nodes = {}
    for element in root.findall("node"):
        try:
            node_id = element.attrib["id"]
            nodes[node_id] = (float(element.attrib["lat"]),
                              float(element.attrib["lon"]))
        except (KeyError, ValueError) as exc:
            raise ValueError("invalid OSM node") from exc

    graph = collections.defaultdict(list)
    names = collections.defaultdict(set)
    for way in root.findall("way"):
        tags = {tag.attrib["k"]: tag.attrib["v"] for tag in way.findall("tag")}
        name = tags.get("name:en")
        if tags.get("highway") != "secondary" or name not in OUTER_ROADS:
            continue
        if tags.get("access") in ("private", "no") or tags.get("motor_vehicle") in ("private", "no"):
            continue
        if tags.get("oneway") not in ("yes", "true", "1", "-1"):
            # Never assume an untagged street is a legal one-way connector.
            continue
        way_id = way.attrib["id"]
        refs = [nd.attrib["ref"] for nd in way.findall("nd")]
        if len(refs) < 2:
            raise ValueError("OSM way has <2 nodes: " + way_id)
        if any(ref not in nodes for ref in refs):
            raise ValueError("snapshot missing nodes in selected way " + way_id)
        if tags["oneway"] == "-1":
            refs.reverse()
        for a, b in zip(refs, refs[1:]):
            ax, az = world(*nodes[a])
            bx, bz = world(*nodes[b])
            length = math.hypot(ax - bx, az - bz)
            if length < 0.01:
                continue
            mx, mz = (ax + bx) / 2, (az + bz) / 2
            # Penalize leaving the expected moat corridor, but always
            # follow the directed OSM graph (no artificial connections).
            distance = min(abs(mx - 850), abs(mx + 810),
                           abs(mz - 800), abs(mz + 835))
            weight = length * (1 + (distance / 70) ** 2)
            graph[a].append((b, weight, length, way_id, name))
            names[name].add(a)
            names[name].add(b)
    if any(not names[name] for name, _ in ANCHORS):
        raise ValueError("snapshot lacks one or more anchor carriageways")
    return nodes, graph, names


def find_anchors(nodes, names):
    anchors = []
    for road, (tx, tz) in ANCHORS:
        chosen = min(names[road],
                     key=lambda n: (world(*nodes[n])[0] - tx) ** 2 +
                                   (world(*nodes[n])[1] - tz) ** 2)
        if math.dist(world(*nodes[chosen]), (tx, tz)) > 150:
            raise ValueError("anchor road too far from expected moat: " + road)
        anchors.append(chosen)
    if len(set(anchors)) != len(anchors):
        raise ValueError("anchor nodes not distinct")
    return anchors


def shortest_path(graph, start, end):
    distances = {start: 0.0}
    previous = {}
    queue = [(0.0, start)]
    while queue:
        cost, node = heapq.heappop(queue)
        if cost != distances[node]:
            continue
        if node == end:
            break
        for dest, weight, length, way_id, name in graph[node]:
            updated = cost + weight
            if updated < distances.get(dest, math.inf):
                distances[dest] = updated
                previous[dest] = (node, length, way_id, name)
                heapq.heappush(queue, (updated, dest))
    if end not in distances:
        raise ValueError("no connected one-way route between anchors")
    nodes = [end]
    edges = []
    while nodes[-1] != start:
        prev, length, way_id, name = previous[nodes[-1]]
        edges.append((way_id, name, length))
        nodes.append(prev)
    nodes.reverse()
    edges.reverse()
    return nodes, edges


def extract(path):
    nodes, graph, names = parse_osm(path)
    anchors = find_anchors(nodes, names)
    route = []
    edges = []
    for a, b in zip(anchors, anchors[1:] + anchors[:1]):
        leg, segments = shortest_path(graph, a, b)
        route.extend(leg[:-1])
        edges.extend(segments)
    if len(route) != len(set(route)):
        raise ValueError("outer loop revisits a node; topology is not a simple ring")
    points = [world(*nodes[n]) for n in route]
    validate_simple_loop(points)
    distance = perimeter(points)
    if not 6540 * .97 <= distance <= 6540 * 1.03:
        raise ValueError("OSM route length outside ±3%: %.1f m" % distance)
    area = sum(points[i][0] * points[(i + 1) % len(points)][1] -
               points[(i + 1) % len(points)][0] * points[i][1]
               for i in range(len(points)))
    if area <= 0:
        raise ValueError("OSM outer loop does not follow clockwise direction")
    way_ids = list(dict.fromkeys(way_id for way_id, _, _ in edges))
    coordinates = [[round(nodes[n][1], 8), round(nodes[n][0], 8)]
                   for n in route]
    coordinates.append(coordinates[0][:])
    return {
        "type": "Feature",
        "properties": {
            "name": "Chiang Mai outer moat clockwise (OSM candidate)",
            "source": SOURCE,
            "license": LICENSE,
            "source_url": "https://www.openstreetmap.org/copyright",
            "source_api_url": OSM_API_URL,
            "snapshot_sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest(),
            "osm_way_ids": way_ids,
            "road_names": list(dict.fromkeys(name for _, name, _ in edges)),
            "length_m_before_resampling": round(distance, 3),
            "road_direction": "clockwise; each edge follows oneway OSM tags",
            "review_status": "OSM-derived; field geometry/traffic review pending",
        },
        "geometry": {"type": "LineString", "coordinates": coordinates},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--osm-xml", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--snapshot-date",help="UTC download date YYYY-MM-DD")
    args = parser.parse_args()
    feature = extract(args.osm_xml)
    if args.snapshot_date:
        import datetime
        datetime.date.fromisoformat(args.snapshot_date)
        feature["properties"]["snapshot_date_utc"] = args.snapshot_date
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(feature, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
    points, sha = import_geojson(args.out)
    print("OSM-derived clockwise candidate: %d source nodes, %d OSM ways,"
          " %.1f m source, %.1f m after resampling, SHA256 %s" %
          (len(feature["geometry"]["coordinates"]) - 1,
           len(feature["properties"]["osm_way_ids"]),
           feature["properties"]["length_m_before_resampling"],
           perimeter(points), sha))


if __name__ == "__main__":
    main()
