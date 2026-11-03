#!/usr/bin/env python3
"""Extract four OSM-mapped Chiang Mai historic city gates from one OSM XML.

The OSM node positions are factual map data; the generated gate models are
stylised placeholders, NOT historical architectural reconstructions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path

from osm_outer_ring import LICENSE, OSM_API_URL, SOURCE

# Explicit node IDs prevent an arbitrary tourist business containing "gate"
# in its name from being mistaken for an actual historic city gate.
GATES = (
    ("tha-phae", "Tha Phae Gate", "east", "1017379824"),
    ("chiang-mai", "Chiang Mai Gate", "south", "6107975995"),
    ("suan-dok", "Suan Dok Gate", "west", "6717438786"),
    ("chang-phueak", "Chang Phueak Gate", "north", "11229077788"),
)


def extract(path):
    source=Path(path)
    root=ET.parse(source).getroot()
    if root.tag!="osm":
        raise ValueError("expected OSM XML")
    nodes={node.attrib["id"]:node for node in root.findall("node")}
    features=[]
    for slug,name,side,node_id in GATES:
        node=nodes.get(node_id)
        if node is None:
            raise ValueError("missing OSM historic city gate node: "+node_id)
        tags={tag.attrib["k"]:tag.attrib["v"] for tag in node.findall("tag")}
        if tags.get("historic")!="city_gate":
            raise ValueError("OSM node is no longer tagged historic=city_gate: "+node_id)
        lon=float(node.attrib["lon"]);lat=float(node.attrib["lat"])
        if not (98.97<lon<99.00 and 18.77<lat<18.80 and
                math.isfinite(lon) and math.isfinite(lat)):
            raise ValueError("historic gate outside old-city vicinity: "+node_id)
        features.append({
            "type":"Feature",
            "properties":{"osm_node_id":node_id,"id":slug,"name":name,
                          "side":side,"name:th":tags.get("name:th",tags.get("name",""))},
            "geometry":{"type":"Point","coordinates":[lon,lat]}
        })
    return {
        "type":"FeatureCollection",
        "properties":{"source":SOURCE,"license":LICENSE,
                      "source_url":"https://www.openstreetmap.org/copyright",
                      "source_api_url":OSM_API_URL,
                      "snapshot_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),
                      "review_status":"OSM historic city gate points; on-site review pending",
                      "architecture_status":"procedural stylised blockouts, NOT historical reconstructions"},
        "features":features
    }


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--osm-xml",required=True,type=Path)
    parser.add_argument("--out",required=True,type=Path)
    parser.add_argument("--snapshot-date")
    args=parser.parse_args()
    data=extract(args.osm_xml)
    if args.snapshot_date:
        import datetime
        datetime.date.fromisoformat(args.snapshot_date)
        data["properties"]["snapshot_date_utc"]=args.snapshot_date
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",
                        encoding="utf-8")
    print("Extracted %d OSM historic city gate nodes" % len(data["features"]))


if __name__=="__main__":
    main()
