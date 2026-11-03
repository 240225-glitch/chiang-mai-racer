#!/usr/bin/env python3
"""Extract lightweight OSM roadside building footprints from a saved OSM XML.

Geometry/way IDs are OSM-derived (ODbL). Building heights are either OSM
tags or visibly marked game estimates. Only the 80 m roadside band is
retained; no huge 10k-building import or runtime XML parser is needed.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path

from build_moat_blockout import (
    CENTER_LAT, CENTER_LON, DEFAULT_GATES, project_lonlat,
    triangulate_water_polygon, load_historic_gates,
)
from osm_outer_ring import LICENSE, OSM_API_URL, SOURCE

MAX_BUILDINGS = 900
MAX_PER_50M = 10
MAX_DISTANCE_M = 80
MIN_VERTEX_DISTANCE_M = 12
MAX_VERTICES = 35
GATE_CLEARANCE_M = 27


def nearest_segment(points, x, z):
    """Return (distance², nearest route vertex index) in world metres."""
    best=math.inf
    best_i=0
    for i,a in enumerate(points):
        b=points[(i+1)%len(points)]
        vx=b[0]-a[0];vz=b[1]-a[1]
        length2=vx*vx+vz*vz
        if length2<=1e-10:
            continue
        t=max(0,min(1,((x-a[0])*vx+(z-a[1])*vz)/length2))
        d=(x-a[0]-t*vx)**2+(z-a[1]-t*vz)**2
        if d<best:
            best=d
            best_i=i
    return best,best_i


def building_height(tags, osm_id):
    """OSM explicit height/levels first, deterministic estimated fallback."""
    try:
        if "height" in tags:
            raw=tags["height"].strip().lower()
            if raw.endswith(" m"):
                raw=raw[:-2].strip()
            h=float(raw)
            if math.isfinite(h) and 2<=h<=30:
                return round(h,2),"osm:height"
        if "building:levels" in tags:
            levels=float(tags["building:levels"])
            if math.isfinite(levels) and 1<=levels<=10:
                return round(min(30.0,levels*3.2),2),"osm:building:levels"
    except ValueError:
        pass
    # 6.5–10m; stable across runs, clearly labelled estimated.
    return 6.5+(int(osm_id)%8)*0.5,"estimated:game-blockout"


def extract(osm_path, route_path, gates_path=None):
    osm_path=Path(osm_path)
    route_path=Path(route_path)
    route=json.loads(route_path.read_text(encoding="utf-8"))
    expected=route.get("osm_snapshot_sha256")
    actual=hashlib.sha256(osm_path.read_bytes()).hexdigest()
    if expected!=actual:
        raise ValueError("OSM XML does not match checked-in route snapshot SHA-256")
    if route.get("source")!=SOURCE:
        raise ValueError("route lacks OSM source attribution")
    points=route.get("points",[])
    if len(points)<100:
        raise ValueError("missing valid resampled road route")
    historic_gates=[]
    if gates_path is not None:
        historic_gates,gate_props=load_historic_gates(gates_path)
        if gate_props.get("snapshot_sha256")!=actual:
            raise ValueError("roadside building gate source snapshot mismatch")
    root=ET.parse(osm_path).getroot()
    if root.tag!="osm":
        raise ValueError("expected OSM XML")
    nodes={n.attrib["id"]:(float(n.attrib["lon"]),float(n.attrib["lat"]))
           for n in root.findall("node")}
    candidates=[]
    skipped=collections.Counter()
    for way in root.findall("way"):
        tags={t.attrib["k"]:t.attrib["v"] for t in way.findall("tag")}
        if tags.get("building") in (None,"no","roof","construction"):
            continue
        refs=[nd.attrib["ref"] for nd in way.findall("nd")]
        if (len(refs)<4 or refs[0]!=refs[-1] or
            len(refs)-1>MAX_VERTICES or
            any(ref not in nodes for ref in refs)):
            skipped["invalid-footprint"]+=1
            continue
        coords=[nodes[ref] for ref in refs[:-1]]
        poly=[project_lonlat(lon,lat) for lon,lat in coords]
        if any(not all(math.isfinite(c) for c in p) for p in poly):
            skipped["invalid-coordinate"]+=1
            continue
        x=sum(p[0] for p in poly)/len(poly)
        z=sum(p[1] for p in poly)/len(poly)
        distance2,route_index=nearest_segment(points,x,z)
        if distance2>MAX_DISTANCE_M**2:
            continue
        if any(nearest_segment(points,px,pz)[0]<MIN_VERTEX_DISTANCE_M**2
               for px,pz in poly):
            skipped["road-overlap"]+=1
            continue
        if any((px-gate["x"])**2+(pz-gate["z"])**2<GATE_CLEARANCE_M**2
               for px,pz in poly for gate in historic_gates):
            skipped["gate-clearance"]+=1
            continue
        try:
            roof_points,roof_triangles=triangulate_water_polygon(poly)
        except ValueError:
            skipped["non-simple"]+=1
            continue
        area=abs(sum(poly[i][0]*poly[(i+1)%len(poly)][1]-
                     poly[(i+1)%len(poly)][0]*poly[i][1]
                     for i in range(len(poly)))/2)
        if not 10<=area<=2000:
            skipped["implausible-area"]+=1
            continue
        way_id=way.attrib["id"]
        height,height_source=building_height(tags,way_id)
        candidates.append((distance2,int(way_id),route_index,{
            "type":"Feature",
            "properties":{
                "osm_way_id":way_id,
                "building":tags["building"],
                "height_m":height,
                "height_source":height_source,
                "distance_to_route_m":round(math.sqrt(distance2),2)
            },
            "geometry":{"type":"Polygon","coordinates":[
                [[round(lon,8),round(lat,8)] for lon,lat in coords]+
                [[round(coords[0][0],8),round(coords[0][1],8)]]
            ]}
        }))
    candidates.sort(key=lambda row:(row[0],row[1]))
    bins=collections.Counter()
    selected=[]
    for _,_,index,feature in candidates:
        bin_id=index//5  # roughly 50 metres along the track
        if bins[bin_id]>=MAX_PER_50M:
            continue
        selected.append(feature)
        bins[bin_id]+=1
        if len(selected)>=MAX_BUILDINGS:
            break
    # Keep output stable and easy to diff between OSM snapshots.
    selected.sort(key=lambda feature:int(feature["properties"]["osm_way_id"]))
    return {
        "type":"FeatureCollection",
        "properties":{
            "source":SOURCE,"license":LICENSE,
            "source_url":"https://www.openstreetmap.org/copyright",
            "source_api_url":OSM_API_URL,
            "snapshot_sha256":actual,
            "selection":"centroid <=80m from race route; footprint vertices >=12m from centreline and >=27m from historic gates; max 10 per 50m, 900 total",
            "height_policy":"OSM height/levels when present; otherwise deterministic visual estimate, not surveyed",
            "building_count":len(selected),
            "estimated_height_count":sum(
                f["properties"]["height_source"].startswith("estimated")
                for f in selected),
            "skipped_invalid_count":sum(skipped.values())
        },
        "features":selected
    }


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--osm-xml",required=True,type=Path)
    parser.add_argument("--route",default="assets/tracks/chiangmai-moat/route.json",
                        type=Path)
    parser.add_argument("--out",required=True,type=Path)
    parser.add_argument("--gates",default=DEFAULT_GATES,type=Path)
    args=parser.parse_args()
    data=extract(args.osm_xml,args.route,args.gates)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(data,ensure_ascii=False,
                                   separators=(",",":"))+"\n",encoding="utf-8")
    print("OSM roadside buildings: %d selected, %d estimated heights, %d invalid/skipped" %
          (data["properties"]["building_count"],
           data["properties"]["estimated_height_count"],
           data["properties"]["skipped_invalid_count"]))


if __name__=="__main__":
    main()
