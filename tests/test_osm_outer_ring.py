#!/usr/bin/env python3
"""OSM one-way graph and attribution regression tests (no network required)."""
import importlib.util
import json
import math
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("osm_outer_ring",ROOT/"tools/osm_outer_ring.py")
import sys
sys.path.insert(0,str(ROOT/"tools"))
osm=importlib.util.module_from_spec(spec)
spec.loader.exec_module(osm)


def fixture_xml(path, missing_connector=False, wrong_way=False):
    """Create a clockwise outer square of 5 named OSM carriageways."""
    coordinates=[
        (850,0),(850,800),(0,800),(-810,800),
        (-810,0),(-810,-835),(0,-835),(850,-835)
    ]
    root=ET.Element("osm",version="0.6")
    for i,(x,z) in enumerate(coordinates,1):
        ET.SubElement(root,"node",id=str(i),
                      lat=str(osm.CENTER_LAT-z/osm.LAT_SCALE),
                      lon=str(osm.CENTER_LON+x/osm.LON_SCALE))
    roads=[
        ("Kotchasarn Road",[1,2]),
        ("Chang Lo Road",[2,3,4]),
        ("Bun Rueang Rit Road",[4,5,6]),
        ("Mani Noppharat Road",[6,7,8]),
        ("Chayiaphoom Road",[8,1])
    ]
    for i,(name,refs) in enumerate(roads,100):
        if missing_connector and name=="Chayiaphoom Road":
            continue
        way=ET.SubElement(root,"way",id=str(i))
        for ref in refs:
            ET.SubElement(way,"nd",ref=str(ref))
        ET.SubElement(way,"tag",k="highway",v="secondary")
        ET.SubElement(way,"tag",k="name:en",v=name)
        ET.SubElement(way,"tag",k="oneway",
                      v="-1" if wrong_way and name=="Chang Lo Road" else "yes")
    ET.ElementTree(root).write(path,encoding="utf-8",xml_declaration=True)


class OSMOuterRingTests(unittest.TestCase):
    def test_stitches_oneway_shared_nodes_and_records_provenance(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"osm.xml"
            fixture_xml(p)
            feature=osm.extract(p)
            self.assertEqual(feature["type"],"Feature")
            self.assertEqual(feature["properties"]["source"],"© OpenStreetMap contributors")
            self.assertEqual(feature["properties"]["license"],osm.LICENSE)
            self.assertEqual(len(feature["properties"]["osm_way_ids"]),5)
            self.assertEqual(len(feature["geometry"]["coordinates"]),9)
            self.assertEqual(feature["geometry"]["coordinates"][0],
                             feature["geometry"]["coordinates"][-1])
            self.assertTrue(6540*.97 <= feature["properties"]["length_m_before_resampling"] <= 6540*1.03)
            self.assertEqual(feature,osm.extract(p),"candidate must be deterministic")

    def test_refuses_missing_topology_and_wrong_way(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"osm.xml"
            fixture_xml(p,missing_connector=True)
            with self.assertRaisesRegex(ValueError,"no connected"):
                osm.extract(p)
            fixture_xml(p,wrong_way=True)
            with self.assertRaisesRegex(ValueError,"no connected"):
                osm.extract(p)

    def test_rejects_untagged_oneway_shortcut(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"osm.xml"
            fixture_xml(p)
            tree=ET.parse(p)
            root=tree.getroot()
            way=ET.SubElement(root,"way",id="999")
            ET.SubElement(way,"nd",ref="1")
            ET.SubElement(way,"nd",ref="3")
            ET.SubElement(way,"tag",k="highway",v="secondary")
            ET.SubElement(way,"tag",k="name:en",v="Kotchasarn Road")
            # No oneway tag -> not part of eligible directed graph.
            tree.write(p)
            result=osm.extract(p)
            self.assertNotIn("999",result["properties"]["osm_way_ids"])


if __name__=="__main__":
    unittest.main()
