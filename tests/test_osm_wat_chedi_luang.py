#!/usr/bin/env python3
"""OSM provenance and procedural Wat Chedi Luang landmark mesh regressions."""
import hashlib
import json
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
from osm_wat_chedi_luang import extract, FEATURES
from build_moat_blockout import (
    DEFAULT_GEOJSON, DEFAULT_LANDMARKS, DEFAULT_WATER, DEFAULT_GATES,
    DEFAULT_BUILDINGS, import_geojson, load_water_polygons, load_historic_gates,
    load_roadside_buildings, load_wat_chedi_luang, align_gates_to_route,
    model, validate_geometry
)


class WatChediLuangTests(unittest.TestCase):
    def test_checked_in_footprints_share_official_osm_snapshot(self):
        raw=json.loads(DEFAULT_LANDMARKS.read_text(encoding="utf-8"))
        props=raw["properties"]
        road=json.loads(DEFAULT_GEOJSON.read_text(encoding="utf-8"))["properties"]
        water=json.loads(DEFAULT_WATER.read_text(encoding="utf-8"))["properties"]
        gates=json.loads(DEFAULT_GATES.read_text(encoding="utf-8"))["properties"]
        buildings=json.loads(DEFAULT_BUILDINGS.read_text(encoding="utf-8"))["properties"]
        self.assertEqual(props["source"],"© OpenStreetMap contributors")
        self.assertEqual(props["license"],"Open Database License (ODbL) 1.0")
        self.assertEqual(props["snapshot_sha256"],road["snapshot_sha256"])
        self.assertEqual(props["snapshot_sha256"],water["snapshot_sha256"])
        self.assertEqual(props["snapshot_sha256"],gates["snapshot_sha256"])
        self.assertEqual(props["snapshot_sha256"],buildings["snapshot_sha256"])
        self.assertIn("not an architectural reconstruction",props["model_status"])
        features,loaded=load_wat_chedi_luang(DEFAULT_LANDMARKS)
        self.assertEqual(set(features),{"compound","stupa","viharn","city-pillar-shrine"})
        self.assertEqual(loaded["snapshot_sha256"],props["snapshot_sha256"])
        self.assertEqual(
            [features[k][1]["osm_way_id"] for k in
             ("compound","stupa","viharn","city-pillar-shrine")],
            ["243018795","93413945","93413944","441418807"]
        )

    def test_landmark_meshes_are_merged_bounded_and_non_degenerate(self):
        points,_=import_geojson(DEFAULT_GEOJSON)
        gates,_=load_historic_gates(DEFAULT_GATES)
        points=align_gates_to_route(points,gates)
        water,_=load_water_polygons(DEFAULT_WATER)
        buildings,_=load_roadside_buildings(DEFAULT_BUILDINGS)
        landmarks,_=load_wat_chedi_luang(DEFAULT_LANDMARKS)
        asset=model(points,water,gates,buildings,landmarks)
        self.assertTrue(validate_geometry(asset))
        self.assertGreater(len(asset["meshes"]),40)
        self.assertEqual(len(asset["materials"]),15)
        names=[mesh["name"] for mesh in asset["meshes"]]
        for name in (
            "wat-chedi-luang-stupa",
            "wat-chedi-luang-stupa-buttresses",
            "wat-chedi-luang-viharn-and-shrine",
            "wat-chedi-luang-roofs"
        ):
            self.assertIn(name,names)
        total=sum(len(mesh["indices"])//3 for mesh in asset["meshes"])
        self.assertGreater(total,16000)
        self.assertLess(total,17000)
        by_name={mesh["name"]:mesh for mesh in asset["meshes"]}
        stupa=by_name["wat-chedi-luang-stupa"]
        self.assertAlmostEqual(min(stupa["positions"][1::3]),0,places=3)
        self.assertGreater(max(stupa["positions"][1::3]),38)
        self.assertLess(max(stupa["positions"][1::3]),39)
        # No degenerate triangles: the legacy r50 renderer uses FrontSide.
        for name,mesh in by_name.items():
            if not name.startswith("wat-"):
                continue
            pos=mesh["positions"]
            for i in range(0,len(mesh["indices"]),3):
                a,b,c=(mesh["indices"][i:i+3])
                ax,ay,az=pos[3*a:3*a+3]
                bx,by,bz=pos[3*b:3*b+3]
                cx,cy,cz=pos[3*c:3*c+3]
                ux,uy,uz=bx-ax,by-ay,bz-az
                vx,vy,vz=cx-ax,cy-ay,cz-az
                area2=((uy*vz-uz*vy)**2+
                       (uz*vx-ux*vz)**2+
                       (ux*vy-uy*vx)**2)**0.5
                self.assertGreater(area2,1e-5,(name,i))

    def test_landmark_material_ids_do_not_depend_on_optional_buildings(self):
        points,_=import_geojson(DEFAULT_GEOJSON)
        landmarks,_=load_wat_chedi_luang(DEFAULT_LANDMARKS)
        # A custom route may intentionally omit the optional roadside layer.
        asset=model(points,landmarks=landmarks)
        self.assertTrue(validate_geometry(asset))
        self.assertEqual(len(asset["materials"]),11)
        for mesh in asset["meshes"]:
            self.assertLess(mesh["material"],len(asset["materials"]))

    def test_extractor_requires_same_snapshot_and_tagged_ways(self):
        with tempfile.TemporaryDirectory() as d:
            xml=Path(d)/"osm.xml"
            route=Path(d)/"route.json"
            root=ET.Element("osm")
            next_node=1
            def add_way(way_id,coords,tags):
                nonlocal next_node
                way=ET.SubElement(root,"way",id=way_id)
                refs=[]
                for lon,lat in coords:
                    ref=str(next_node);next_node+=1;refs.append(ref)
                    ET.SubElement(root,"node",id=ref,lon=str(lon),lat=str(lat))
                    ET.SubElement(way,"nd",ref=ref)
                ET.SubElement(way,"nd",ref=refs[0])
                for key,value in tags.items():
                    ET.SubElement(way,"tag",k=key,v=value)
            add_way("243018795",[
                (98.985,18.785),(98.988,18.785),(98.988,18.788),
                (98.985,18.788)
            ],{"amenity":"place_of_worship","name:en":"Wat Chedi Luang"})
            add_way("93413945",[
                (98.986,18.786),(98.987,18.786),(98.987,18.787),
                (98.986,18.787)
            ],{"man_made":"stupa","historic":"ruins","tourism":"attraction"})
            add_way("93413944",[
                (98.9865,18.7865),(98.9875,18.7865),(98.9875,18.787),
                (98.9865,18.787)
            ],{"building":"yes","historic":"yes"})
            add_way("441418807",[
                (98.987,18.7858),(98.9872,18.7858),(98.9872,18.786),
                (98.987,18.786)
            ],{"amenity":"place_of_worship","building":"yes"})
            ET.ElementTree(root).write(xml,encoding="utf-8",xml_declaration=True)
            route.write_text(json.dumps({
                "osm_snapshot_sha256":hashlib.sha256(xml.read_bytes()).hexdigest()
            }), encoding="utf-8")
            data=extract(xml,route)
            self.assertEqual(len(data["features"]),4)
            self.assertEqual(data["features"][1]["properties"]["role"],"stupa")
            route.write_text(json.dumps({"osm_snapshot_sha256":"0"*64}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"snapshot SHA-256"):
                extract(xml,route)

    def test_loader_rejects_tampered_provenance_identity_and_open_ring(self):
        raw=json.loads(DEFAULT_LANDMARKS.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as d:
            file=Path(d)/"landmarks.geojson"
            raw["properties"]["license"]="CC0"
            file.write_text(json.dumps(raw), encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"ODbL"):
                load_wat_chedi_luang(file)
            raw=json.loads(DEFAULT_LANDMARKS.read_text(encoding="utf-8"))
            raw["features"][0]["properties"]["osm_way_id"]="999"
            file.write_text(json.dumps(raw), encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"identity"):
                load_wat_chedi_luang(file)
            raw=json.loads(DEFAULT_LANDMARKS.read_text(encoding="utf-8"))
            raw["features"][1]["geometry"]["coordinates"][0][-1]=[0,0]
            file.write_text(json.dumps(raw), encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"explicitly closed"):
                load_wat_chedi_luang(file)


if __name__=="__main__":
    unittest.main()
