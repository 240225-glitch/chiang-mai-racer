#!/usr/bin/env python3
"""Bridge inventory is provenance-checked candidate data, not verified 3D."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from osm_bridge_inventory import (extract, point_polygon_distance,
                                  polyline_water_distance, segment_segment_distance,
                                  water_overlap_metrics, bridge_topology_status, water_end_cap_centres,
                                  motor_endpoint_connections, motor_bridge_review_clusters,
                                  route_centerline_metrics, load_route_for_bridge_audit,
                                  directed_motor_route_hops, motor_access_status,
                                  restriction_relations_near_ways, turn_restriction_rules,
                                  via_way_turn_rules, parse_conditional_turn,
                                  parse_conditional_oneway, motor_oneway_direction)

SOURCE = ROOT / "assets/tracks/chiangmai-moat/source-bridges-osm.geojson"
WATER = ROOT / "assets/tracks/chiangmai-moat/source-water-osm.geojson"


class OSMBridgeTests(unittest.TestCase):
    def test_checked_in_inventory_matches_water_snapshot(self):
        data = json.loads(SOURCE.read_text(encoding="utf-8"))
        water = json.loads(WATER.read_text(encoding="utf-8"))
        self.assertEqual(data["properties"]["snapshot_sha256"],
                         water["properties"]["snapshot_sha256"])
        self.assertEqual(data["properties"]["license"],
                         "Open Database License (ODbL) 1.0")
        self.assertEqual(data["properties"]["model_status"],
                         "no bridge 3D geometry generated")
        self.assertIn("full-way segment", data["properties"]["proximity_method"])
        self.assertIn("NOT proof of traffic access",
                      data["properties"]["route_relation_method"])
        self.assertEqual(len(data["features"]), 13)
        motors = {f["properties"]["osm_way_id"]: f["properties"]
                  for f in data["features"]
                  if f["properties"]["motor_bridge_review_site"]}
        self.assertEqual(set(motors), {"26765842", "696726366",
                                      "698115427", "698115429"})
        self.assertTrue(all(p["route_centerline_intersections"] == 0
                            for p in motors.values()))
        self.assertTrue(all(7 <= p["route_centerline_distance_m"] <= 12
                            for p in motors.values()))
        self.assertTrue(all(p["route_alignment_abs_dot"] < 0.06
                            for p in motors.values()))
        self.assertEqual({wid: (p["directed_route_to_bridge_entry_hops"],
                                p["directed_bridge_exit_to_route_hops"])
                          for wid, p in motors.items()},
                         {"26765842": (2, 20), "696726366": (29, 2),
                          "698115427": (3, 29), "698115429": (19, 3)})
        self.assertIn("excludes unresolved conditional/multi-via-way restrictions",
                      data["properties"]["directed_route_connectivity_method"])
        self.assertEqual(data["properties"]["motor_oneway_unresolved_way_ids"],
                         ["19977738", "695727399", "695727400"])
        self.assertEqual(data["properties"]["turn_restriction_relation_count"], 13)
        self.assertEqual(len(data["properties"]["turn_restrictions_applied_relation_ids"]), 9)
        self.assertEqual(len(data["properties"]["turn_restrictions_unhandled_relation_ids"]), 4)
        self.assertIsNone(data["properties"]["turn_restriction_audit_local_time"])
        self.assertEqual(data["properties"]["turn_restrictions_inactive_relation_ids"], [])
        self.assertIn("motorcar > motor_vehicle",
                      data["properties"]["motor_access_audit_method"])
        self.assertTrue(all(p["motor_access_tag_status"] == "untagged"
                            for p in motors.values()))
        self.assertTrue(all(f["properties"]["motor_access_tag_status"] == "not_motor_road"
                            for f in data["features"]
                            if f["properties"]["highway"] == "footway"))
        self.assertTrue(all(isinstance(p["nearby_turn_restriction_relation_ids"], list)
                            for p in motors.values()))
        self.assertEqual(data["properties"]["motor_bridge_review_sites"], 2)
        self.assertIn("NOT confirmed physical bridges",
                      data["properties"]["motor_bridge_review_site_method"])
        ids = [int(f["properties"]["osm_way_id"]) for f in data["features"]]
        self.assertEqual(ids, sorted(set(ids)))
        for feature in data["features"]:
            props = feature["properties"]
            self.assertEqual(props["bridge"], "yes")
            self.assertIsInstance(props["route_centerline_distance_m"], float)
            self.assertGreaterEqual(props["route_centerline_distance_m"], 0)
            self.assertIsInstance(props["route_nearest_segment_index"], int)
            self.assertIsInstance(props["route_centerline_intersections"], int)
            self.assertGreaterEqual(props["route_alignment_abs_dot"], 0)
            self.assertLessEqual(props["route_alignment_abs_dot"], 1)
            self.assertLessEqual(props["water_proximity_m"], 12)
            self.assertGreaterEqual(len(feature["geometry"]["coordinates"]), 2)
            self.assertEqual(feature["geometry"]["type"], "LineString")

    def test_route_centerline_relation_geometry(self):
        # Near-parallel bridge is not a crossing; perpendicular true
        # intersection is distinct from a near miss.
        route = [(0, 0), (20, 0), (20, 20), (0, 20), (0, 0)]
        near = [(7, 5), (13, 5)]
        self.assertEqual(route_centerline_metrics(near, route),
                         (5.0, 0, 0, 1.0))
        crossing = [(10, -5), (10, 5)]
        self.assertEqual(route_centerline_metrics(crossing, route),
                         (0.0, 1, 0, 0.0))
        self.assertEqual(route_centerline_metrics([(20, -5), (20, 5)], route)[1], 1)
        with self.assertRaises(ValueError):
            route_centerline_metrics([(0, 0)], route)

    def test_route_source_must_match_snapshot_and_be_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "route.geojson"
            doc = {"type": "Feature", "properties": {"snapshot_sha256": "abc"},
                   "geometry": {"type": "LineString", "coordinates": [
                       [98.985, 18.788], [98.986, 18.788],
                       [98.986, 18.789], [98.985, 18.788]]}}
            path.write_text(json.dumps(doc), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "snapshot hashes differ"):
                load_route_for_bridge_audit(path, "other")
            self.assertEqual(len(load_route_for_bridge_audit(path, "abc")), 4)
            doc["geometry"]["coordinates"].pop()
            path.write_text(json.dumps(doc), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "closed LineString"):
                load_route_for_bridge_audit(path, "abc")

    def test_polygon_distance_inside_and_outside(self):
        poly = [(0,0),(10,0),(10,10),(0,10)]
        self.assertEqual(point_polygon_distance((5,5),poly),0)
        self.assertAlmostEqual(point_polygon_distance((15,5),poly),5)

    def test_exact_proximity_catches_unsampled_short_crossings(self):
        water = [(29, 4), (31, 4), (31, 6), (29, 6)]
        long_way = [(-100, 5), (100, 5)]
        # Old endpoints+midpoint sampling missed the 2m-wide water crossing.
        self.assertGreater(min(point_polygon_distance(p, water)
                               for p in [long_way[0], (0, 5), long_way[1]]), 12)
        self.assertEqual(polyline_water_distance(long_way, [water]), 0)
        self.assertAlmostEqual(water_overlap_metrics(long_way, [water])[0], 2)
        self.assertEqual(water_overlap_metrics(long_way, [water])[1], 2)
        self.assertAlmostEqual(polyline_water_distance([(-100, 8), (100, 8)],
                                                        [water]), 2)
        self.assertAlmostEqual(segment_segment_distance((0, 0), (10, 0),
                                                         (5, 3), (5, 7)), 3)
        self.assertEqual(segment_segment_distance((0, 0), (10, 0),
                                                  (5, -3), (5, 7)), 0)
        with self.assertRaises(ValueError):
            polyline_water_distance([(0, 0)], [water])

    def test_mapped_water_clipping_handles_crossings_and_tangencies(self):
        square = [(0,0),(10,0),(10,10),(0,10)]
        self.assertAlmostEqual(water_overlap_metrics([(-5,5),(15,5)], [square])[0],10)
        self.assertEqual(water_overlap_metrics([(-5,5),(15,5)], [square])[1],2)
        self.assertEqual(water_overlap_metrics([(-5,0),(15,0)], [square]),(0,0))
        self.assertEqual(water_overlap_metrics([(-5,-5),(0,0)], [square]),(0,0))
        self.assertEqual(water_overlap_metrics([(-5,15),(15,15)], [square]),(0,0))
        self.assertAlmostEqual(water_overlap_metrics([(-5,5),(5,5),(15,5)],
                                                      [square])[0],10)
        other = [(10,0),(20,0),(20,10),(10,10)]
        length, crossings = water_overlap_metrics([(-5,5),(25,5)], [square,other])
        self.assertAlmostEqual(length,20)
        self.assertEqual(crossings,2)

    def test_motor_road_near_water_polygon_cut_is_review_candidate(self):
        # OSM water can end at a bridge, so no water overlap is not proof
        # that a mapped bridge=yes motor road does not cross the moat.
        water = [[(0, 0), (20, 0), (20, 120), (0, 120)]]
        caps = water_end_cap_centres(water)
        self.assertEqual(len(caps), 2)
        self.assertEqual(bridge_topology_status("secondary_link", 0, 0, True, 5),
                         "mapped_water_gap_motor_bridge_candidate")
        self.assertEqual(bridge_topology_status("footway", 0, 0, True, 5),
                         "nearby_unconfirmed")
        self.assertEqual(bridge_topology_status("secondary_link", 0, 0, True, 17),
                         "nearby_unconfirmed")
        self.assertEqual(bridge_topology_status("secondary_link", 0.5, 1, True, 5),
                         "nearby_unconfirmed")
        self.assertEqual(bridge_topology_status("secondary_link", 0, 0, False, 5),
                         "nearby_unconfirmed")
        self.assertEqual(bridge_topology_status("secondary_link", 12, 2, True, 5),
                         "geometric_water_crossing_candidate")

    def test_checked_in_inventory_distinguishes_nearby_from_crossing(self):
        data = json.loads(SOURCE.read_text(encoding="utf-8"))
        groups = {}
        for feature in data["features"]:
            props = feature["properties"]
            groups.setdefault(props["topology_status"], []).append(props)
            self.assertGreaterEqual(props["mapped_water_overlap_m"],0)
            self.assertGreaterEqual(props["mapped_water_boundary_crossings"],0)
        self.assertEqual(len(groups["geometric_water_crossing_candidate"]),7)
        self.assertEqual(len(groups["mapped_water_gap_motor_bridge_candidate"]),4)
        self.assertEqual(len(groups["nearby_unconfirmed"]),2)
        self.assertEqual({p["osm_way_id"] for p in
                          groups["mapped_water_gap_motor_bridge_candidate"]},
                         {"26765842", "696726366", "698115427", "698115429"})
        motor = groups["mapped_water_gap_motor_bridge_candidate"]
        self.assertTrue(all(p["highway"] == "secondary_link" and
                            p["mapped_water_overlap_m"] == 0 and
                            p["mapped_water_end_cap_proximity_m"] <= 16
                            for p in motor))
        # Four OSM one-way segments represent two nearby parallel review
        # locations, NOT four verified separate bridge structures.
        sites = {p["osm_way_id"]: p["motor_bridge_review_site"] for p in motor}
        self.assertEqual(sites, {"26765842": "review-site-01",
                                 "696726366": "review-site-01",
                                 "698115427": "review-site-02",
                                 "698115429": "review-site-02"})
        self.assertTrue(all(p["oneway"] == "yes" and p["lanes"] == "1"
                            and p["surface"] == "asphalt"
                            and p["motor_road_connected_ends"] == 2
                            and all(len(n) >= 1 for n in p["motor_road_endpoint_neighbors"])
                            for p in motor))
        self.assertTrue(all(p["highway"]=="footway" for p in
                            groups["geometric_water_crossing_candidate"]))
        self.assertTrue(all(p["motor_road_connected_ends"] == 0 for p in
                            groups["geometric_water_crossing_candidate"]))
        self.assertTrue(all(p["mapped_water_overlap_m"]>=1 for p in
                            groups["geometric_water_crossing_candidate"]))
        self.assertTrue(all(p["mapped_water_overlap_m"]==0 for p in
                            groups["nearby_unconfirmed"]))

    def test_directed_route_hops_obey_oneway_and_roundabout(self):
        def make_way(wid, refs, **tags):
            way = ET.Element("way", id=wid)
            for ref in refs:
                ET.SubElement(way, "nd", ref=ref)
            for key, value in {"highway": "secondary", **tags}.items():
                ET.SubElement(way, "tag", k=key, v=value)
            return way

        ways = [
            make_way("1", ["r0", "r1"]),
            make_way("2", ["r1", "a"], oneway="yes"),
            make_way("3", ["a", "b"], oneway="yes"),
            make_way("4", ["b", "r0"], oneway="yes"),
            make_way("5", ["r0", "c"], oneway="-1"),
            make_way("6", ["r1", "d"], junction="roundabout"),
            make_way("7", ["r0", "e"], highway="footway"),
        ]
        outgoing, incoming = directed_motor_route_hops(ways, ["1"])
        self.assertEqual((outgoing["a"], incoming["a"]), (1, 2))
        self.assertEqual((outgoing["b"], incoming["b"]), (2, 1))
        self.assertNotIn("c", outgoing)
        self.assertEqual(incoming["c"], 1)
        self.assertEqual(outgoing["d"], 1)
        self.assertNotIn("d", incoming)
        self.assertNotIn("e", outgoing)
        with self.assertRaisesRegex(ValueError, "missing from source"):
            directed_motor_route_hops(ways, ["nonexistent"])

    def test_motor_access_precedence_and_limited_road_exclusion(self):
        self.assertEqual(motor_access_status({}), ("untagged", None, None))
        self.assertEqual(motor_access_status({"access": "private"}),
                         ("restricted", "access", "private"))
        self.assertEqual(motor_access_status({"access": "private",
                                              "motor_vehicle": "yes"}),
                         ("tag_allows", "motor_vehicle", "yes"))
        self.assertEqual(motor_access_status({"motor_vehicle": "yes",
                                              "motorcar": "no"}),
                         ("restricted", "motorcar", "no"))
        self.assertEqual(motor_access_status({"access": "destination"})[0], "limited")
        self.assertEqual(motor_access_status({"access": "unknown_value"})[0], "unresolved")
        self.assertEqual(motor_access_status({"access": "official"})[0], "limited")
        self.assertEqual(motor_access_status({"access": "emergency"})[0], "restricted")

        def way(wid, refs, **tags):
            element = ET.Element("way", id=wid)
            for ref in refs:
                ET.SubElement(element, "nd", ref=ref)
            for key, value in {"highway": "secondary", **tags}.items():
                ET.SubElement(element, "tag", k=key, v=value)
            return element

        ways = [way("1", ["a", "b"]),
                way("2", ["b", "c"], access="private"),
                way("3", ["b", "d"], access="destination"),
                way("4", ["b", "e"], motor_vehicle="no"),
                way("5", ["b", "f"], access="private", motorcar="yes"),
                way("6", ["b", "g"], access="unexpected")]
        forward, backward = directed_motor_route_hops(ways, ["1"])
        for node in ("c", "d", "e", "g"):
            self.assertNotIn(node, forward)
            self.assertNotIn(node, backward)
        self.assertEqual(forward["f"], 1)
        self.assertEqual(backward["f"], 1)

    def test_turn_aware_bfs_blocks_no_and_only_via_node_turns(self):
        def way(wid, refs):
            item = ET.Element("way", id=wid)
            for ref in refs:
                ET.SubElement(item, "nd", ref=ref)
            ET.SubElement(item, "tag", k="highway", v="secondary")
            ET.SubElement(item, "tag", k="oneway", v="yes")
            return item

        def restriction(rid, kind, from_id, via, to_id):
            item = ET.Element("relation", id=rid)
            ET.SubElement(item, "tag", k="type", v="restriction")
            ET.SubElement(item, "tag", k="restriction", v=kind)
            for typ, ref, role in (("way", from_id, "from"),
                                   ("node", via, "via"),
                                   ("way", to_id, "to")):
                ET.SubElement(item, "member", type=typ, ref=ref, role=role)
            return item

        ways = [way("1", ["r0", "r1"]), way("2", ["r1", "a"]),
                way("3", ["a", "b"]), way("4", ["b", "r0"]),
                way("5", ["a", "d"]), way("6", ["d", "r0"])]
        outgoing, incoming = directed_motor_route_hops(ways, ["1"])
        self.assertEqual(outgoing["b"], 2)
        self.assertEqual(outgoing["d"], 2)
        self.assertEqual(incoming["a"], 2)
        blocked = restriction("10", "no_left_turn", "2", "a", "3")
        outgoing, incoming = directed_motor_route_hops(ways, ["1"], [blocked])
        self.assertNotIn("b", outgoing)
        self.assertEqual(outgoing["d"], 2)
        self.assertEqual(incoming["a"], 2)
        # A different incoming way at the SAME node may legally turn.
        alternate = ways + [way("7", ["r0", "a"])]
        outgoing_alt, _ = directed_motor_route_hops(alternate, ["1"], [blocked])
        self.assertEqual(outgoing_alt["b"], 2)
        only = restriction("11", "only_right_turn", "2", "a", "3")
        outgoing, incoming = directed_motor_route_hops(ways, ["1"], [only])
        self.assertEqual(outgoing["b"], 2)
        self.assertNotIn("d", outgoing)

        # Reverse search must remember the *outgoing* way at each node.
        reverse_block = restriction("12", "no_right_turn", "3", "b", "4")
        one_path = ways[:4]
        outgoing, incoming = directed_motor_route_hops(
            one_path, ["1"], [reverse_block])
        self.assertEqual(outgoing["b"], 2)
        self.assertEqual(incoming["b"], 1)  # starts at b, no incoming turn
        self.assertNotIn("a", incoming)  # a->b->r0 violates restriction
        self.assertEqual(incoming["r1"], 0)

    def test_single_via_way_restrictions_forward_reverse_and_alternate_entry(self):
        def way(wid, refs):
            item = ET.Element("way", id=wid)
            for ref in refs:
                ET.SubElement(item, "nd", ref=ref)
            ET.SubElement(item, "tag", k="highway", v="secondary")
            ET.SubElement(item, "tag", k="oneway", v="yes")
            return item

        def relation(rid, kind, from_id="2", via_id="3", to_id="4"):
            item = ET.Element("relation", id=rid)
            ET.SubElement(item, "tag", k="type", v="restriction")
            ET.SubElement(item, "tag", k="restriction", v=kind)
            for wid, role in ((from_id, "from"), (via_id, "via"), (to_id, "to")):
                ET.SubElement(item, "member", type="way", ref=wid, role=role)
            return item

        # r1 -> a -> mid -> b -> c -> r0, with an alternate exit b -> d
        # and another entry r0 -> a. Only from-way 2 triggers the rule.
        ways = [way("1", ["r0", "r1"]), way("2", ["r1", "a"]),
                way("3", ["a", "mid", "b"]), way("4", ["b", "c"]),
                way("5", ["c", "r0"]), way("6", ["b", "d"]),
                way("7", ["d", "r0"])]
        no = relation("10", "no_right_turn")
        out, back = directed_motor_route_hops(ways, ["1"], [no])
        self.assertNotIn("c", out)
        self.assertEqual(out["d"], 4)
        self.assertEqual(back["a"], 4)  # alternate b->d->r0 is legal
        self.assertEqual(back["mid"], 3)
        # With no alternate exit, reverse search must reject the entire
        # from->via->to sequence, not just the final junction transition.
        reverse_ways = ways[:5]
        reverse_ways[1] = way("2", ["r1", "p", "a"])
        _, reverse_hops = directed_motor_route_hops(reverse_ways, ["1"], [no])
        self.assertNotIn("p", reverse_hops)
        only = relation("11", "only_straight_on")
        out, back = directed_motor_route_hops(ways, ["1"], [only])
        self.assertEqual(out["c"], 4)
        self.assertNotIn("d", out)
        # Other entry onto the via-way is not constrained by this relation.
        alternate = ways + [way("8", ["r0", "a"])]
        out, _ = directed_motor_route_hops(alternate, ["1"], [no])
        self.assertEqual(out["c"], 4)

        rules, applied, unhandled = via_way_turn_rules([no], ways)
        self.assertEqual((applied, unhandled), (["10"], []))
        self.assertEqual(rules[("a", "2", "3")][0][1:], ("b", "4", "no"))
        # Ambiguous shared junctions must not be silently enforced.
        ambiguous = [way("1", ["r0", "r1"]), way("2", ["r1", "a", "b"]),
                     way("3", ["a", "mid", "b"]), way("4", ["b", "c"])]
        self.assertEqual(via_way_turn_rules([no], ambiguous)[2], ["10"])
        conditional = relation("12", "no_right_turn")
        ET.SubElement(conditional, "tag", k="restriction:conditional",
                      v="no_right_turn @ (07:00-09:00)")
        self.assertEqual(via_way_turn_rules([conditional], ways)[2], ["12"])

    def test_reverse_via_way_only_turn_respects_from_way_and_to_way(self):
        # only_* limits turns FROM way 2 through via way 3 to way 4.
        # It does not ban way 8 -> via 3 -> way 4, and it must ban
        # way 2 -> via 3 -> way 6 when reversing a path search.
        def way(wid, refs):
            item = ET.Element("way", id=wid)
            for ref in refs:
                ET.SubElement(item, "nd", ref=ref)
            ET.SubElement(item, "tag", k="highway", v="secondary")
            ET.SubElement(item, "tag", k="oneway", v="yes")
            return item

        relation = ET.Element("relation", id="80")
        ET.SubElement(relation, "tag", k="type", v="restriction")
        ET.SubElement(relation, "tag", k="restriction", v="only_straight_on")
        for wid, role in (("2", "from"), ("3", "via"), ("4", "to")):
            ET.SubElement(relation, "member", type="way", ref=wid, role=role)
        base = [way("1", ["r0", "r1"]), way("2", ["p", "a"]),
                way("3", ["a", "mid", "b"]), way("4", ["b", "good"]),
                way("6", ["b", "bad"]), way("8", ["q", "a"])]
        # The allowed exit leads back to the race route: both p and q
        # have a legal forward route, regardless of the only restriction.
        _, back = directed_motor_route_hops(
            base + [way("5", ["good", "r0"])], ["1"], [relation])
        self.assertEqual(back["p"], 5)
        self.assertEqual(back["q"], 5)
        # Only the forbidden exit reaches the route. The restricted
        # from-way p must be unreachable, but unrelated entry q is legal.
        _, back = directed_motor_route_hops(
            base + [way("7", ["bad", "r0"])], ["1"], [relation])
        self.assertNotIn("p", back)
        self.assertEqual(back["q"], 5)
        # A race-route node at the via-way exit is a valid endpoint:
        # without a known following TO way, only_* cannot constrain it.
        _, back = directed_motor_route_hops(
            base + [way("9", ["r0", "b"])], ["9"], [relation])
        self.assertEqual(back["p"], 3)

    def test_only_turn_bans_same_way_straight_continuation(self):
        # OSM may keep a through-road as ONE way across the via node.
        # An only_right_turn from that way must forbid continuing straight,
        # even though the incoming and outgoing way IDs are identical.
        def way(wid, refs):
            item = ET.Element("way", id=wid)
            for ref in refs:
                ET.SubElement(item, "nd", ref=ref)
            ET.SubElement(item, "tag", k="highway", v="secondary")
            ET.SubElement(item, "tag", k="oneway", v="yes")
            return item

        def relation(kind, to="3"):
            item = ET.Element("relation", id="99")
            ET.SubElement(item, "tag", k="type", v="restriction")
            ET.SubElement(item, "tag", k="restriction", v=kind)
            for typ, ref, role in (("way", "2", "from"),
                                   ("node", "a", "via"),
                                   ("way", to, "to")):
                ET.SubElement(item, "member", type=typ, ref=ref, role=role)
            return item

        forward = [way("1", ["r0", "r1"]),
                   way("2", ["r1", "a", "straight"]),
                   way("3", ["a", "allowed"])]
        out, _ = directed_motor_route_hops(forward, ["1"])
        self.assertEqual(out["straight"], 2)  # regression reproducer
        out, _ = directed_motor_route_hops(
            forward, ["1"], [relation("only_right_turn")])
        self.assertEqual(out["allowed"], 2)
        self.assertNotIn("straight", out)
        # A no_right_turn towards a different way does not ban going
        # straight along the same way.
        out, _ = directed_motor_route_hops(
            forward, ["1"], [relation("no_right_turn")])
        self.assertEqual(out["straight"], 2)
        # The reverse search must enforce the same constraint when a
        # through-road leads INTO a route node after the via junction.
        reverse = [way("1", ["r0", "r1"]),
                   way("2", ["p", "a", "r0"]),
                   way("3", ["a", "allowed"])]
        self.assertEqual(directed_motor_route_hops(
            reverse, ["1"])[1]["p"], 2)
        _, back = directed_motor_route_hops(
            reverse, ["1"], [relation("only_right_turn")])
        self.assertNotIn("p", back)
        # A same-way only_straight_on relation explicitly naming the
        # same way still allows continuing on it.
        out, _ = directed_motor_route_hops(
            forward, ["1"], [relation("only_straight_on", "2")])
        self.assertEqual(out["straight"], 2)

    def test_same_way_no_u_turn_requires_reversing_at_via_node(self):
        # A route can reach the branch only by going to a dead end and
        # reversing along the same two-way OSM way. A no_u_turn at that
        # dead end must prohibit that manoeuvre, but not ordinary straight
        # travel or turns from unrelated incoming ways.
        def way(wid, refs, oneway=None):
            item = ET.Element("way", id=wid)
            for ref in refs:
                ET.SubElement(item, "nd", ref=ref)
            ET.SubElement(item, "tag", k="highway", v="secondary")
            if oneway:
                ET.SubElement(item, "tag", k="oneway", v=oneway)
            return item

        def restriction(rid, kind, frm, via, to):
            item = ET.Element("relation", id=rid)
            ET.SubElement(item, "tag", k="type", v="restriction")
            ET.SubElement(item, "tag", k="restriction", v=kind)
            for typ, ref, role in (("way", frm, "from"),
                                   ("node", via, "via"),
                                   ("way", to, "to")):
                ET.SubElement(item, "member", type=typ, ref=ref, role=role)
            return item

        ways = [way("1", ["r0", "r1"], "yes"),
                way("2", ["r1", "p"], "yes"),
                way("3", ["p", "a"]),
                way("4", ["p", "goal"], "yes")]
        only = restriction("90", "only_right_turn", "2", "p", "3")
        uturn = restriction("91", "no_u_turn", "3", "a", "3")
        # Without a U-turn restriction, this is the only route to goal.
        self.assertEqual(directed_motor_route_hops(
            ways, ["1"], [only])[0]["goal"], 4)
        rules, applied, unhandled, _ = turn_restriction_rules([uturn])
        self.assertEqual((applied, unhandled), (["91"], []))
        self.assertEqual(rules[("a", "3")]["no"], {"3"})
        out, _ = directed_motor_route_hops(ways, ["1"], [only, uturn])
        self.assertNotIn("goal", out)
        self.assertEqual(out["a"], 2)
        # A no_u_turn does not prohibit travelling onward on the same way.
        through = [way("3", ["p", "a", "b"])]
        self.assertEqual(directed_motor_route_hops(
            ways[:2] + through + ways[3:], ["1"], [only, uturn]
        )[0]["b"], 3)
        # Reverse search must also reject a route requiring the same U-turn.
        reverse_ways = [way("1", ["r0", "r1"]),
                        way("2", ["p", "r0"], "yes"),
                        way("3", ["p", "a"]),
                        way("4", ["goal", "p"], "yes")]
        reverse_only = restriction("92", "only_right_turn", "4", "p", "3")
        # Reverse search starts from route and traverses the reversed edges.
        # An alternate path goal->p->a->p->r0 is not allowed to U-turn at a.
        self.assertEqual(directed_motor_route_hops(
            reverse_ways, ["1"], [reverse_only])[1]["goal"], 4)
        self.assertNotIn("goal", directed_motor_route_hops(
            reverse_ways, ["1"], [reverse_only, uturn])[1])

    def test_via_node_restriction_requires_shared_road_topology(self):
        # A malformed only_* relation naming a disconnected TO way used
        # to forbid valid through traffic along the FROM way.
        def way(wid, refs):
            item = ET.Element("way", id=wid)
            for ref in refs:
                ET.SubElement(item, "nd", ref=ref)
            ET.SubElement(item, "tag", k="highway", v="secondary")
            ET.SubElement(item, "tag", k="oneway", v="yes")
            return item

        relation = ET.Element("relation", id="99")
        ET.SubElement(relation, "tag", k="type", v="restriction")
        ET.SubElement(relation, "tag", k="restriction", v="only_right_turn")
        for typ, ref, role in (("way", "2", "from"),
                               ("node", "a", "via"),
                               ("way", "3", "to")):
            ET.SubElement(relation, "member", type=typ, ref=ref, role=role)
        base = [way("1", ["r0", "r1"]),
                way("2", ["r1", "a", "straight"]),
                way("3", ["far", "other"])]
        rules, applied, unhandled, _ = turn_restriction_rules(
            [relation], ways=base)
        self.assertEqual((rules, applied, unhandled), ({}, [], ["99"]))
        out, _ = directed_motor_route_hops(base, ["1"], [relation])
        self.assertEqual(out["straight"], 2)
        reverse = [way("1", ["r0", "r1"]),
                   way("2", ["p", "a", "r0"]),
                   way("3", ["far", "other"])]
        self.assertEqual(directed_motor_route_hops(
            reverse, ["1"], [relation])[1]["p"], 2)
        # A valid junction must still enforce the restriction.
        connected = base[:2] + [way("3", ["a", "allowed"])]
        rules, applied, unhandled, _ = turn_restriction_rules(
            [relation], ways=connected)
        self.assertEqual((applied, unhandled), (["99"], []))
        self.assertIn(("a", "2"), rules)
        out, _ = directed_motor_route_hops(connected, ["1"], [relation])
        self.assertNotIn("straight", out)
        self.assertEqual(out["allowed"], 2)

    def test_turn_rules_report_unsupported_relations(self):
        def relation(rid, kind="no_left_turn", via_type="node", conditional=False):
            item = ET.Element("relation", id=rid)
            ET.SubElement(item, "tag", k="type", v="restriction")
            ET.SubElement(item, "tag", k=("restriction:conditional" if conditional
                                          else "restriction"), v=kind)
            for typ, ref, role in (("way", "2", "from"),
                                   (via_type, "a", "via"),
                                   ("way", "3", "to")):
                ET.SubElement(item, "member", type=typ, ref=ref, role=role)
            return item
        rules, applied, unhandled, inactive = turn_restriction_rules([
            relation("1"), relation("2", via_type="way"),
            relation("3", conditional=True), relation("4", kind="unknown")])
        self.assertEqual(applied, ["1"])
        self.assertEqual(unhandled, ["2", "3", "4"])
        self.assertEqual(inactive, [])
        self.assertEqual(rules[("a", "2")]["no"], {"3"})

    def test_daily_conditional_turn_windows_and_strict_syntax(self):
        self.assertEqual(parse_conditional_turn(
            "no_right_turn @ (06:00-09:00,15:00-18:00)", "08:30"),
            ("no_right_turn", True))
        self.assertEqual(parse_conditional_turn(
            "no_right_turn @ (06:00-09:00,15:00-18:00)", "12:00"),
            ("no_right_turn", False))
        self.assertEqual(parse_conditional_turn(
            "no_right_turn @ (06:00-09:00,15:00-18:00)", "18:00"),
            ("no_right_turn", False))
        self.assertEqual(parse_conditional_turn(
            "only_right_turn @ (22:00-02:00)", "01:00"),
            ("only_right_turn", True))
        self.assertEqual(parse_conditional_turn(
            "only_right_turn @ (22:00-02:00)", "12:00"),
            ("only_right_turn", False))
        for unsupported in ("no_left_turn @ (Mo-Fr 07:00-09:00)",
                            "no_left_turn @ (25:00-27:00)",
                            "no_left_turn @ (07:00-07:00)",
                            "no_left_turn @ (07:00-09:00); no_right_turn @ (12:00-13:00)"):
            self.assertIsNone(parse_conditional_turn(unsupported, "08:00"))
        for bad_time in ("8:00", "24:00", "08:60"):
            with self.assertRaisesRegex(ValueError, "HH:MM"):
                parse_conditional_turn("no_left_turn @ (07:00-09:00)", bad_time)

    def test_conditional_oneway_never_creates_optimistic_reverse_paths(self):
        def way(wid, refs, **tags):
            item = ET.Element("way", id=wid)
            for ref in refs:
                ET.SubElement(item, "nd", ref=ref)
            for key, value in {"highway": "secondary", **tags}.items():
                ET.SubElement(item, "tag", k=key, v=value)
            return item

        ways = [way("1", ["r0", "r1"]),
                way("2", ["r1", "a"], **{
                    "oneway:conditional": "yes @ (06:00-09:00,15:00-18:00)"})]
        # Without an audit time, this conditional segment must not be
        # counted as an unrestricted two-way connector.
        out, back = directed_motor_route_hops(ways, ["1"])
        self.assertNotIn("a", out)
        self.assertNotIn("a", back)
        self.assertEqual(directed_motor_route_hops(
            ways, ["1"], audit_time="08:00")[0]["a"], 1)
        self.assertNotIn("a", directed_motor_route_hops(
            ways, ["1"], audit_time="08:00")[1])
        self.assertEqual(directed_motor_route_hops(
            ways, ["1"], audit_time="12:00")[1]["a"], 1)
        self.assertEqual(parse_conditional_oneway(
            "-1 @ (22:00-02:00)", "01:00"), ("-1", True))
        self.assertEqual(parse_conditional_oneway(
            "no @ (22:00-02:00)", "12:00"), ("no", False))
        self.assertIsNone(parse_conditional_oneway(
            "yes @ (Mo-Fr 06:00-09:00)", "08:00"))
        self.assertIsNone(motor_oneway_direction(
            {"oneway": "alternating"}))
        self.assertIsNone(motor_oneway_direction(
            {"oneway:conditional": "yes @ (Mo-Fr 06:00-09:00)"}, "08:00"))
        self.assertEqual(motor_oneway_direction({"highway": "motorway"}), 1)
        self.assertEqual(motor_oneway_direction({"junction": "circular"}), 1)
        self.assertEqual(motor_oneway_direction({
            "highway": "motorway", "oneway": "no"}), 0)
        self.assertEqual(motor_oneway_direction({
            "oneway": "yes", "oneway:conditional": "no @ (06:00-09:00)"
        }, "08:00"), 0)
        self.assertEqual(motor_oneway_direction({
            "oneway": "yes", "oneway:conditional": "no @ (06:00-09:00)"
        }, "12:00"), 1)

    def test_conditional_via_node_enforced_only_at_explicit_local_time(self):
        def way(wid, refs):
            item = ET.Element("way", id=wid)
            for ref in refs:
                ET.SubElement(item, "nd", ref=ref)
            ET.SubElement(item, "tag", k="highway", v="secondary")
            ET.SubElement(item, "tag", k="oneway", v="yes")
            return item
        ways = [way("1", ["r0", "r1"]), way("2", ["r1", "a"]),
                way("3", ["a", "b"]), way("4", ["b", "r0"])]
        rel = ET.Element("relation", id="101")
        ET.SubElement(rel, "tag", k="type", v="restriction")
        ET.SubElement(rel, "tag", k="restriction:conditional",
                      v="no_right_turn @ (06:00-09:00, 15:00-18:00)")
        for typ, ref, role in (("way", "2", "from"),
                               ("node", "a", "via"),
                               ("way", "3", "to")):
            ET.SubElement(rel, "member", type=typ, ref=ref, role=role)
        self.assertEqual(directed_motor_route_hops(ways, ["1"], [rel])[0]["b"], 2)
        self.assertNotIn("b", directed_motor_route_hops(
            ways, ["1"], [rel], audit_time="08:00")[0])
        self.assertEqual(directed_motor_route_hops(
            ways, ["1"], [rel], audit_time="12:00")[0]["b"], 2)
        self.assertNotIn("b", directed_motor_route_hops(
            ways, ["1"], [rel], audit_time="16:00")[0])
        self.assertEqual(directed_motor_route_hops(
            ways, ["1"], [rel], audit_time="18:00")[0]["b"], 2)
        self.assertEqual(turn_restriction_rules([rel])[2], ["101"])
        self.assertEqual(turn_restriction_rules([rel], "08:00")[1], ["101"])
        self.assertEqual(turn_restriction_rules([rel], "12:00")[3], ["101"])
        with self.assertRaisesRegex(ValueError, "HH:MM"):
            directed_motor_route_hops(ways, ["1"], [rel], audit_time="bad")
        # Day-of-week expressions and motorcar exemptions must not be
        # silently evaluated as an unconditional ban.
        unsupported = ET.fromstring(ET.tostring(rel))
        unsupported.find("tag[@k='restriction:conditional']").set(
            "v", "no_right_turn @ (Mo-Fr 06:00-09:00)")
        self.assertEqual(turn_restriction_rules([unsupported], "08:00")[2], ["101"])
        exempt = ET.fromstring(ET.tostring(rel))
        ET.SubElement(exempt, "tag", k="except", v="motorcar")
        self.assertEqual(turn_restriction_rules([exempt], "08:00")[2], ["101"])
        mixed = ET.fromstring(ET.tostring(rel))
        ET.SubElement(mixed, "tag", k="restriction", v="no_left_turn")
        self.assertEqual(turn_restriction_rules([mixed], "08:00")[2], ["101"])

    def test_restriction_relation_review_detects_via_node_and_via_way(self):
        def relation(rid, members):
            r = ET.Element("relation", id=rid)
            ET.SubElement(r, "tag", k="type", v="restriction")
            ET.SubElement(r, "tag", k="restriction", v="no_left_turn")
            for typ, ref, role in members:
                ET.SubElement(r, "member", type=typ, ref=ref, role=role)
            return r
        relations = [
            relation("2", [("way", "99", "from"), ("node", "b", "via"),
                           ("way", "100", "to")]),
            relation("1", [("way", "11", "via"), ("way", "200", "to")]),
            relation("3", [("way", "99", "from"), ("node", "z", "via")])]
        self.assertEqual(restriction_relations_near_ways(
            relations, {"11": ["a", "b"], "12": ["x", "y"]}),
            {"11": ["1", "2"], "12": []})

    def test_motor_endpoint_connections_require_shared_node(self):
        incidence = {"start": {"42", "43"}, "end": {"42", "44"},
                     "isolated": {"42"}}
        self.assertEqual(motor_endpoint_connections(["start", "mid", "end"],
                                                     "42", incidence),
                         [["43"], ["44"]])
        self.assertEqual(motor_endpoint_connections(["isolated", "mid", "end"],
                                                     "42", incidence),
                         [[], ["44"]])

    def test_review_clustering_is_proximity_and_parallel_not_bridge_count(self):
        lines = {"10": [(0, 0), (0, 20)],
                 "11": [(5, 20), (5, 0)],  # reversed parallel carriageway
                 "12": [(-10, 10), (10, 10)],  # crossing, not parallel
                 "13": [(100, 0), (100, 20)]}
        self.assertEqual(motor_bridge_review_clusters(lines),
                         {"10": "review-site-01", "11": "review-site-01",
                          "12": "review-site-02", "13": "review-site-03"})
        self.assertEqual(motor_bridge_review_clusters({"10": lines["10"],
                                                         "11": lines["11"]},
                                                        max_separation_m=2),
                         {"10": "review-site-01", "11": "review-site-02"})

    def test_extract_detects_crossing_between_all_old_sample_points(self):
        # Long way crosses a very narrow water polygon near neither endpoint
        # nor the midpoint; the former sampled-distance filter missed it.
        with tempfile.TemporaryDirectory() as d:
            osm = Path(d) / "long.xml"
            water = Path(d) / "water.geojson"
            root = ET.Element("osm")
            for ref, lon in (("1", 98.9840), ("2", 98.9880)):
                ET.SubElement(root, "node", id=ref, lon=str(lon), lat="18.7883")
            way = ET.SubElement(root, "way", id="555")
            for ref in ("1", "2"):
                ET.SubElement(way, "nd", ref=ref)
            ET.SubElement(way, "tag", k="highway", v="footway")
            ET.SubElement(way, "tag", k="bridge", v="yes")
            ET.ElementTree(root).write(osm, encoding="utf-8")
            polygon = [[98.98579, 18.7882], [98.98581, 18.7882],
                       [98.98581, 18.7884], [98.98579, 18.7884],
                       [98.98579, 18.7882]]
            water.write_text(json.dumps({
                "type": "FeatureCollection",
                "properties": {"source": "© OpenStreetMap contributors",
                               "license": "Open Database License (ODbL) 1.0",
                               "snapshot_sha256": hashlib.sha256(osm.read_bytes()).hexdigest()},
                "features": [{"type": "Feature", "geometry": {
                    "type": "Polygon", "coordinates": [polygon]}}]
            }), encoding="utf-8")
            found = extract(osm, water)["features"]
            self.assertEqual(len(found), 1)
            self.assertEqual(found[0]["properties"]["osm_way_id"], "555")
            self.assertEqual(found[0]["properties"]["water_proximity_m"], 0)
            self.assertEqual(found[0]["properties"]["topology_status"],
                             "geometric_water_crossing_candidate")

    def test_extract_requires_same_snapshot_and_filters_nonbridges(self):
        with tempfile.TemporaryDirectory() as d:
            osm = Path(d)/"map.xml"
            water = Path(d)/"water.geojson"
            root = ET.Element("osm")
            coords = {
                "1": (98.9854,18.7883), "2": (98.9856,18.7883),
                "3": (98.9880,18.7883), "4": (98.9881,18.7883)
            }
            for id_, (lon,lat) in coords.items():
                ET.SubElement(root,"node",id=id_,lon=str(lon),lat=str(lat))
            for id_, refs, is_bridge in (
                ("100",("1","2"),True),
                ("101",("1","2"),False),
                ("102",("3","4"),True)
            ):
                way = ET.SubElement(root,"way",id=id_)
                for ref in refs:
                    ET.SubElement(way,"nd",ref=ref)
                ET.SubElement(way,"tag",k="highway",v="footway")
                if is_bridge:
                    ET.SubElement(way,"tag",k="bridge",v="yes")
            ET.ElementTree(root).write(osm,encoding="utf-8")
            sha = hashlib.sha256(osm.read_bytes()).hexdigest()
            polygon = [[98.98545,18.7884],[98.98555,18.7884],
                       [98.98555,18.7882],[98.98545,18.7882],
                       [98.98545,18.7884]]
            source = {
                "type":"FeatureCollection",
                "properties":{"source":"© OpenStreetMap contributors",
                              "license":"Open Database License (ODbL) 1.0",
                              "snapshot_sha256":sha},
                "features":[{"type":"Feature","geometry":{
                    "type":"Polygon","coordinates":[polygon]}}]
            }
            water.write_text(json.dumps(source), encoding="utf-8")
            data = extract(osm,water)
            self.assertEqual([f["properties"]["osm_way_id"]
                              for f in data["features"]],["100"])
            source["properties"]["snapshot_sha256"] = "0"*64
            water.write_text(json.dumps(source), encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"snapshot hashes differ"):
                extract(osm,water)


if __name__ == "__main__":
    unittest.main()
