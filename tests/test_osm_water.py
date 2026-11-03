#!/usr/bin/env python3
"""Offline OSM moat polygon extraction/triangulation tests."""
import importlib.util
import json
import math
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
from build_moat_blockout import (
    DEFAULT_WATER, load_water_polygons, triangulate_water_polygon,
    water_mesh, water_bank_meshes, is_water_polygon_end_cap, validate_geometry, model, build_points
)
from osm_moat_water import extract


def signed_area(points):
    return sum(points[i][0]*points[(i+1)%len(points)][1]-
               points[(i+1)%len(points)][0]*points[i][1]
               for i in range(len(points)))/2


class MoatWaterTests(unittest.TestCase):
    def test_real_osm_water_provenance_and_mesh(self):
        polygons,props=load_water_polygons(DEFAULT_WATER)
        self.assertEqual(len(polygons),19)
        self.assertEqual(props["license"],"Open Database License (ODbL) 1.0")
        self.assertEqual(len(props["snapshot_sha256"]),64)
        mesh=water_mesh(polygons)
        self.assertEqual(mesh["name"],"moat-water")
        self.assertGreater(len(mesh["indices"])//3,100)
        self.assertLess(len(mesh["indices"])//3,400)
        positions=mesh["positions"]
        area=0
        for i in range(0,len(mesh["indices"]),3):
            a,b,c=mesh["indices"][i:i+3]
            ax,az=positions[a*3],positions[a*3+2]
            bx,bz=positions[b*3],positions[b*3+2]
            cx,cz=positions[c*3],positions[c*3+2]
            normal_y=(bz-az)*(cx-ax)-(bx-ax)*(cz-az)
            self.assertGreater(normal_y,0,"all water faces must point up")
            area+=normal_y/2
        source_area=sum(abs(signed_area(p)) for p in polygons)
        self.assertAlmostEqual(area/source_area,1,places=3)
        self.assertTrue(validate_geometry(model(build_points(),polygons)))

    def test_shoreline_bank_is_local_visual_only_geometry(self):
        polygons, _ = load_water_polygons(DEFAULT_WATER)
        banks = water_bank_meshes(polygons, 12)
        self.assertEqual(len(banks), 19)
        self.assertEqual(sum(len(b["indices"])//3 for b in banks),
                         2*(sum(map(len, polygons))-12))
        for i, (polygon, bank) in enumerate(zip(polygons, banks)):
            self.assertEqual(bank["name"], "osm-moat-bank-%02d" % i)
            self.assertEqual(bank["material"], 12)
            self.assertEqual(len(bank["positions"]), 6*len(polygon))
            skipped=sum(is_water_polygon_end_cap(polygon,j)
                        for j in range(len(polygon)))
            self.assertEqual(len(bank["indices"]), 6*(len(polygon)-skipped))
            self.assertEqual(bank["offset"][1], 0)
            for j, (x,z) in enumerate(polygon):
                vertex = bank["positions"][j*6:j*6+6]
                self.assertAlmostEqual(vertex[0]+bank["offset"][0], x, places=3)
                self.assertAlmostEqual(vertex[2]+bank["offset"][2], z, places=3)
                self.assertEqual(vertex[1], -0.45)
                self.assertEqual(vertex[4], 0.18)
            radius=max(math.hypot(bank["positions"][k],
                                  bank["positions"][k+2])
                       for k in range(0,len(bank["positions"]),3))
            self.assertLess(radius,400)
        osm_model=model(build_points(),polygons)
        self.assertTrue(validate_geometry(osm_model))
        self.assertEqual(sum(m["name"].startswith("osm-moat-bank-")
                             for m in osm_model["meshes"]),19)
        self.assertFalse(any(m["name"].startswith("osm-moat-bank-")
                             for m in model(build_points())["meshes"]))
        self.assertEqual(osm_model["meshes"][-1]["name"],
                         "game-dashed-centreline")

    def test_bank_caps_omit_artificial_cross_water_walls(self):
        # 20 m wide, 120 m long water rectangle: only the long banks remain.
        rectangle=[(0,0),(20,0),(20,120),(0,120)]
        for ring in (rectangle,list(reversed(rectangle))):
            self.assertEqual(sum(is_water_polygon_end_cap(ring,i)
                                 for i in range(len(ring))),2)
            bank=water_bank_meshes([ring],3)[0]
            self.assertEqual(len(bank["indices"])//3,4)
        # Short corners and rounded shores are not automatically treated as caps.
        square=[(0,0),(20,0),(20,20),(0,20)]
        self.assertFalse(any(is_water_polygon_end_cap(square,i)
                             for i in range(len(square))))
        self.assertEqual(len(water_bank_meshes([square],3)[0]["indices"])//3,8)

        # A stepped/concave shoreline has a short perpendicular connector,
        # but both neighbouring edges travel in the SAME direction. It is
        # genuine shoreline, not a closure across the moat. The old rule
        # incorrectly removed this edge, leaving a visible gap in the bank.
        notch=[(0,-120),(0,0),(20,0),(20,120),(-30,120),(-30,-120)]
        for ring in (notch,list(reversed(notch))):
            self.assertFalse(any(is_water_polygon_end_cap(ring,i)
                                 for i in range(len(ring))))
            self.assertEqual(len(water_bank_meshes([ring],3)[0]["indices"])//3,
                             2*len(ring))

    def test_concave_and_reverse_order(self):
        # An L-shaped concave polygon, 7 unique points.
        points=[(0,0),(10,0),(10,3),(3,3),(3,10),(0,10)]
        for ring in (points,list(reversed(points))):
            pts,indices=triangulate_water_polygon(ring)
            self.assertEqual(len(indices)//3,len(pts)-2)
            area=0
            for i in range(0,len(indices),3):
                a,b,c=[pts[j] for j in indices[i:i+3]]
                normal_y=(b[1]-a[1])*(c[0]-a[0])-(b[0]-a[0])*(c[1]-a[1])
                self.assertGreater(normal_y,0)
                area+=normal_y/2
            self.assertAlmostEqual(area,51,places=5)

    def test_osm_extractor_rejects_unclosed_moat(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"water.osm"
            root=ET.Element("osm")
            for i,(lat,lon) in enumerate(((18.79,98.98),(18.79,98.99),
                                           (18.78,98.99),(18.78,98.98)),1):
                ET.SubElement(root,"node",id=str(i),lat=str(lat),lon=str(lon))
            w=ET.SubElement(root,"way",id="123")
            for ref in ("1","2","3","4"):
                ET.SubElement(w,"nd",ref=ref)
            ET.SubElement(w,"tag",k="natural",v="water")
            ET.SubElement(w,"tag",k="water",v="moat")
            ET.ElementTree(root).write(p)
            with self.assertRaisesRegex(ValueError,"not closed"):
                extract(p)
            ET.SubElement(w,"nd",ref="1")
            ET.ElementTree(root).write(p)
            result=extract(p)
            self.assertEqual(len(result["features"]),1)
            self.assertEqual(result["features"][0]["properties"]["osm_way_id"],"123")


if __name__=="__main__":
    unittest.main()
