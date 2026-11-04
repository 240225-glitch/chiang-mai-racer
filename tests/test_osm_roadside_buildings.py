#!/usr/bin/env python3
"""Regression coverage for OSM-derived roadside buildings and merged r50 meshes."""
import hashlib
import json
import math
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
from build_moat_blockout import (
    DEFAULT_BUILDINGS, DEFAULT_GEOJSON, DEFAULT_GATES, DEFAULT_WATER,
    CENTER_LAT, CENTER_LON, TERRAIN_Y, import_geojson, load_historic_gates,
    load_water_polygons, load_roadside_buildings, align_gates_to_route,
    roadside_building_meshes, model, validate_geometry
)
from osm_roadside_buildings import extract, building_height


class RoadsideBuildingsTests(unittest.TestCase):
    def test_checked_in_osm_buildings_and_provenance(self):
        buildings,props=load_roadside_buildings(DEFAULT_BUILDINGS)
        self.assertEqual(props["source"],"© OpenStreetMap contributors")
        self.assertEqual(props["license"],"Open Database License (ODbL) 1.0")
        road=json.loads(DEFAULT_GEOJSON.read_text(encoding="utf-8"))["properties"]
        water=json.loads(DEFAULT_WATER.read_text(encoding="utf-8"))["properties"]
        gates=json.loads(DEFAULT_GATES.read_text(encoding="utf-8"))["properties"]
        self.assertEqual(props["snapshot_sha256"],road["snapshot_sha256"])
        self.assertEqual(props["snapshot_sha256"],water["snapshot_sha256"])
        self.assertEqual(props["snapshot_sha256"],gates["snapshot_sha256"])
        self.assertEqual(len(buildings),815)
        self.assertEqual(props["estimated_height_count"],776)
        self.assertTrue(all(2<=h<=30 for _,h in buildings))
        # Building facades must not obscure the mapped historical city gates.
        gates,_=load_historic_gates(DEFAULT_GATES)
        for polygon,_ in buildings:
            for x,z in polygon:
                self.assertTrue(all(math.hypot(x-g["x"],z-g["z"])>=26.99
                                    for g in gates))

    def test_merged_mesh_and_roof_winding(self):
        pts,_=import_geojson(DEFAULT_GEOJSON)
        gates,_=load_historic_gates(DEFAULT_GATES)
        pts=align_gates_to_route(pts,gates)
        buildings,_=load_roadside_buildings(DEFAULT_BUILDINGS)
        asset=model(pts,load_water_polygons(DEFAULT_WATER)[0],gates,buildings)
        self.assertEqual(len(asset["materials"]),16)
        self.assertTrue(validate_geometry(asset))
        names=[m["name"] for m in asset["meshes"]]
        for extra in ("illustrative-ground","street-tree-trunks",
                      "street-tree-canopies","street-lamp-posts",
                      "street-lamp-lanterns"):
            self.assertIn(extra,names)
        chunks=[m for m in asset["meshes"] if m["name"].startswith("osm-roadside-")]
        self.assertGreaterEqual(len(chunks),30)
        self.assertLessEqual(len(chunks),50)
        self.assertEqual(len(chunks)%2,0)
        walls=chunks[::2]
        roofs=chunks[1::2]
        self.assertTrue(all(m["name"].startswith("osm-roadside-facades-") for m in walls))
        self.assertTrue(all(m["name"].startswith("osm-roadside-roofs-") for m in roofs))
        self.assertEqual([m["name"].split("-")[-1] for m in walls],
                         [m["name"].split("-")[-1] for m in roofs])
        self.assertGreater(sum(len(m["indices"]) for m in walls),10000)
        self.assertGreater(sum(len(m["indices"]) for m in roofs),3000)
        self.assertLess(sum(len(m["indices"])//3 for m in asset["meshes"]),150000)
        self.assertLessEqual(max(max(m["positions"][1::3]) for m in roofs),30.06)
        self.assertGreaterEqual(min(min(m["positions"][1::3]) for m in walls),TERRAIN_Y)
        facade_material=asset["materials"][walls[0]["material"]]
        roof_material=asset["materials"][roofs[0]["material"]]
        self.assertEqual(facade_material["name"],"osm-building-facades")
        self.assertEqual(roof_material["name"],"osm-building-roofs")
        self.assertTrue(facade_material["vertexColors"])
        self.assertTrue(roof_material["vertexColors"])
        for m in walls+roofs:
            self.assertEqual(len(m["colors"]),len(m["positions"]),m["name"])
            self.assertTrue(all(0.0<=c<=1.0 for c in m["colors"]),m["name"])
        # r50 uses distance from LOCAL ORIGIN for bounding spheres. Merely
        # splitting globally-positioned geometry would NOT improve culling.
        for m in chunks:
            self.assertEqual(len(m["offset"]),3)
            p=m["positions"]
            radius=max(math.sqrt(p[i]**2+p[i+1]**2+p[i+2]**2)
                       for i in range(0,len(p),3))
            self.assertLess(radius,250,m["name"])
            self.assertLess(max(p[::3])-min(p[::3]),550,m["name"])
            self.assertLess(max(p[2::3])-min(p[2::3]),550,m["name"])
        # Rebase must preserve the exact world footprint and triangle count.
        old_walls,old_roofs=roadside_building_meshes(buildings)
        self.assertEqual(sum(len(m["indices"]) for m in walls),
                         len(old_walls["indices"]))
        self.assertEqual(sum(len(m["indices"]) for m in roofs),
                         len(old_roofs["indices"]))
        def bounds(meshes,axis):
            vals=[v+m["offset"][axis] for m in meshes
                  for v in m["positions"][axis::3]]
            return min(vals),max(vals)
        for axis in (0,2):
            for group,old in ((walls,old_walls),(roofs,old_roofs)):
                actual=bounds(group,axis)
                original=(min(old["positions"][axis::3]),
                          max(old["positions"][axis::3]))
                for a,b in zip(actual,original):
                    self.assertAlmostEqual(a,b,places=3)
        self.assertEqual(sum(len(m["indices"])//3 for m in asset["meshes"]),141204)
        # A simple square: facade normals face outward, roof normal faces +Y.
        walls,roofs=roadside_building_meshes([
            ([(0,0),(10,0),(10,10),(0,10)],6)
        ])
        a,b,c=walls["indices"][:3]
        p=walls["positions"]
        va=p[3*a:3*a+3];vb=p[3*b:3*b+3];vc=p[3*c:3*c+3]
        ux,uy=vb[0]-va[0],vb[1]-va[1]
        vx,vy=vc[0]-va[0],vc[1]-va[1]
        # First wall lies along +X; outward direction is -Z.
        self.assertLess(ux*vy-uy*vx,0)
        a,b,c=roofs["indices"][:3]
        p=roofs["positions"]
        # New roofs start with the downward-facing eave soffit. Scan all
        # triangles for the hipped upper faces and check they face upward
        # and away from the building centre.
        upward=0
        for i in range(0,len(roofs["indices"]),3):
            a,b,c=roofs["indices"][i:i+3]
            ax,ay,az=p[3*a:3*a+3]
            bx,by,bz=p[3*b:3*b+3]
            cx,cy,cz=p[3*c:3*c+3]
            ux,uy,uz=bx-ax,by-ay,bz-az
            vx,vy,vz=cx-ax,cy-ay,cz-az
            nx=uy*vz-uz*vy
            ny=uz*vx-ux*vz
            nz=ux*vy-uy*vx
            if ny<=1e-6:
                continue
            upward+=1
            mx,mz=(ax+bx+cx)/3-5.0,(az+bz+cz)/3-5.0
            self.assertGreater(nx*mx+nz*mz,0)
        self.assertEqual(upward,4)

    def test_extractor_rejects_snapshot_mismatch_and_road_overlap(self):
        import osm_roadside_buildings as ex
        route=json.loads((ROOT/"assets/tracks/chiangmai-moat/route.json").read_text(encoding="utf-8"))
        pts=route["points"]
        x,z=pts[80]
        dx=pts[81][0]-pts[79][0]
        dz=pts[81][1]-pts[79][1]
        length=math.hypot(dx,dz)
        nx,nz=-dz/length,dx/length
        earth=6371008.8
        def gps(px,pz):
            return (CENTER_LON+math.degrees(px/(earth*math.cos(math.radians(CENTER_LAT)))),
                    CENTER_LAT-math.degrees(pz/earth))
        def building(root,way_id,distance,levels):
            center=(x+nx*distance,z+nz*distance)
            offsets=[(-5,-5),(5,-5),(5,5),(-5,5)]
            refs=[]
            for j,(ox,oz) in enumerate(offsets):
                lon,lat=gps(center[0]+ox,center[1]+oz)
                ref=str(int(way_id)*10+j)
                ET.SubElement(root,"node",id=ref,lon=str(lon),lat=str(lat))
                refs.append(ref)
            way=ET.SubElement(root,"way",id=way_id)
            for ref in refs+[refs[0]]:
                ET.SubElement(way,"nd",ref=ref)
            ET.SubElement(way,"tag",k="building",v="yes")
            ET.SubElement(way,"tag",k="building:levels",v=str(levels))
        with tempfile.TemporaryDirectory() as d:
            xml=Path(d)/"osm.xml"; route_path=Path(d)/"route.json"
            root=ET.Element("osm")
            building(root,"12345",45,2)
            building(root,"12346",4,2)
            ET.ElementTree(root).write(xml)
            route["osm_snapshot_sha256"]=hashlib.sha256(xml.read_bytes()).hexdigest()
            route_path.write_text(json.dumps(route), encoding="utf-8")
            data=extract(xml,route_path)
            self.assertEqual(data["properties"]["building_count"],1)
            self.assertEqual(data["features"][0]["properties"]["osm_way_id"],"12345")
            self.assertEqual(data["features"][0]["properties"]["height_m"],6.4)
            route["osm_snapshot_sha256"]="0"*64
            route_path.write_text(json.dumps(route), encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"snapshot SHA-256"):
                extract(xml,route_path)

    def test_bad_footprint_height_and_provenance_rejected(self):
        raw=json.loads(DEFAULT_BUILDINGS.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/"buildings.geojson"
            raw["features"][0]["properties"]["height_m"]=-5
            f.write_text(json.dumps(raw), encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"height"):
                load_roadside_buildings(f)
            raw=json.loads(DEFAULT_BUILDINGS.read_text(encoding="utf-8"))
            raw["features"][0]["geometry"]["coordinates"][0][-1]=[0,0]
            f.write_text(json.dumps(raw), encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"explicitly closed"):
                load_roadside_buildings(f)
            raw=json.loads(DEFAULT_BUILDINGS.read_text(encoding="utf-8"))
            raw["properties"]["license"]="CC0"
            f.write_text(json.dumps(raw), encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"ODbL"):
                load_roadside_buildings(f)

    def test_height_estimates_are_stable_and_bounded(self):
        self.assertEqual(building_height({"height":"8.5 m"},"100"),(8.5,"osm:height"))
        self.assertEqual(building_height({"building:levels":"10"},"100"),
                         (30.0,"osm:building:levels"))
        self.assertEqual(building_height({"height":"not-a-height"},"100"),
                         building_height({},"100"))


if __name__=="__main__":
    unittest.main()
