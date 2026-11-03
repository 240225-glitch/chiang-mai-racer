#!/usr/bin/env python3
"""OSM historic gate provenance, positioning and checkpoint regression tests."""
import json
import math
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
from osm_city_gates import extract, GATES
from build_moat_blockout import (
    DEFAULT_GATES, DEFAULT_GEOJSON, DEFAULT_WATER,
    load_historic_gates, align_gates_to_route, import_geojson,
    load_water_polygons, model, metadata, build_points, nearest_road_index
)


class HistoricGateTests(unittest.TestCase):
    def test_four_gates_are_osm_mapped_and_share_snapshot(self):
        gates,props=load_historic_gates(DEFAULT_GATES)
        roads=json.loads(DEFAULT_GEOJSON.read_text(encoding="utf-8"))["properties"]
        water=json.loads(DEFAULT_WATER.read_text(encoding="utf-8"))["properties"]
        self.assertEqual(props["snapshot_sha256"],roads["snapshot_sha256"])
        self.assertEqual(props["snapshot_sha256"],water["snapshot_sha256"])
        self.assertEqual(props["license"],"Open Database License (ODbL) 1.0")
        self.assertEqual([g["id"] for g in gates],[g[0] for g in GATES])
        self.assertEqual([g["osm_node_id"] for g in gates],[g[3] for g in GATES])

    def test_checkpoint_road_projection_and_mesh_match(self):
        pts,_=import_geojson(DEFAULT_GEOJSON)
        gates,_=load_historic_gates(DEFAULT_GATES)
        pts=align_gates_to_route(pts,gates)
        route=metadata(pts,gates)
        asset=model(pts,load_water_polygons(DEFAULT_WATER)[0],gates)
        self.assertEqual(len(asset["meshes"]),28)
        self.assertEqual(len(asset["materials"]),9)
        self.assertEqual(asset["meshes"][5]["name"],"historic-gates-blockout")
        self.assertEqual(asset["meshes"][-1]["name"],"game-dashed-centreline")
        self.assertEqual([g["point_index"] for g in gates],
                         [0,119,320,488])
        for cp,gate in zip(route["checkpoints"],gates):
            self.assertEqual(cp["point_index"],gate["point_index"])
            self.assertEqual(cp["osm_gate_node_id"],gate["osm_node_id"])
            self.assertLess(gate["distance_to_road_m"],60)
            self.assertGreater(gate["distance_to_road_m"],20)
            self.assertLess(math.dist((cp["x"],cp["z"]),
                                      pts[cp["point_index"]]),.01)
        # The *visible* golden checkpoint arches must use the same OSM
        # gate-projected positions as the gameplay analyser, not quarter-laps.
        arches=asset["meshes"][4]["positions"]
        for gate_idx,cp in enumerate(route["checkpoints"]):
            start=gate_idx*24+16  # 3rd cuboid is the crossbar
            verts=[arches[i*3:i*3+3] for i in range(start,start+8)]
            cx=sum(v[0] for v in verts)/8
            cz=sum(v[2] for v in verts)/8
            self.assertAlmostEqual(cx,cp["x"],places=2)
            self.assertAlmostEqual(cz,cp["z"],places=2)
        # The four mapped facades are not painted directly on the race lane.
        facades=asset["meshes"][5]["positions"]
        for gate_idx,gate in enumerate(gates):
            start=gate_idx*40  # 5 cuboids * 8 vertices
            vertices=[facades[i*3:i*3+3] for i in range(start,start+40)]
            cx=sum(v[0] for v in vertices)/40
            cz=sum(v[2] for v in vertices)/40
            self.assertAlmostEqual(cx,gate["x"],places=2)
            self.assertAlmostEqual(cz,gate["z"],places=2)

    def test_schematic_does_not_invent_osm_landmarks(self):
        points=build_points()
        self.assertEqual(len(model(points)["meshes"]),6)
        self.assertNotIn("historic_gates",metadata(points))

    def test_extractor_rejects_missing_or_untagged_gate(self):
        with tempfile.TemporaryDirectory() as d:
            file=Path(d)/"osm.xml"
            root=ET.Element("osm")
            for i,(_,name,_,node_id) in enumerate(GATES):
                n=ET.SubElement(root,"node",id=node_id,
                                lat=str(18.787-i*.001),lon="98.985")
                ET.SubElement(n,"tag",k="historic",v="city_gate")
                ET.SubElement(n,"tag",k="name:en",v=name)
            ET.ElementTree(root).write(file)
            self.assertEqual(len(extract(file)["features"]),4)
            root.remove(root[0])
            ET.ElementTree(root).write(file)
            with self.assertRaisesRegex(ValueError,"missing OSM historic"):
                extract(file)
            root.insert(0,ET.Element("node",id=GATES[0][3],lat="18.787",lon="98.985"))
            ET.ElementTree(root).write(file)
            with self.assertRaisesRegex(ValueError,"no longer tagged"):
                extract(file)

    def test_reject_tampered_gate_coordinates_and_order(self):
        raw=json.loads(DEFAULT_GATES.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as d:
            file=Path(d)/"gates.json"
            raw["features"][0]["geometry"]["coordinates"]=[0,0]
            file.write_text(json.dumps(raw), encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"outside old city"):
                load_historic_gates(file)
            raw=json.loads(DEFAULT_GATES.read_text(encoding="utf-8"))
            raw["features"].reverse()
            file.write_text(json.dumps(raw), encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"order/identity"):
                load_historic_gates(file)


if __name__=="__main__":
    unittest.main()
