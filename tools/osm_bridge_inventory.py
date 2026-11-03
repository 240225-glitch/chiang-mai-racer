#!/usr/bin/env python3
"""Inventory OSM bridge=yes ways near mapped moat water; no 3D claims.

Proximity is a candidate filter, NOT proof that a bridge spans the moat.
Uses the exact same OSM snapshot as the checked-in water source.
"""
from __future__ import annotations

import argparse
from collections import deque
import hashlib
import json
import math
import re
from pathlib import Path
import xml.etree.ElementTree as ET

from build_moat_blockout import (project_lonlat, load_water_polygons,
                                 is_water_polygon_end_cap, DEFAULT_GEOJSON)

SOURCE = "© OpenStreetMap contributors"
LICENSE = "Open Database License (ODbL) 1.0"
MAX_WATER_DISTANCE_M = 12.0
# Only a manual-review flag: OSM water polygons frequently stop at bridges.
MAX_END_CAP_DISTANCE_M = 16.0
MOTOR_ROADS = frozenset((
    "motorway", "motorway_link", "trunk", "trunk_link", "primary", "primary_link",
    "secondary", "secondary_link", "tertiary", "tertiary_link", "residential",
    "unclassified", "service", "living_street", "road"
))


def distance_segment(x, z, a, b):
    dx = b[0] - a[0]
    dz = b[1] - a[1]
    length2 = dx * dx + dz * dz
    t = max(0.0, min(1.0, ((x-a[0])*dx + (z-a[1])*dz) / length2)) if length2 else 0
    return math.hypot(x-a[0]-t*dx, z-a[1]-t*dz)


def point_polygon_distance(point, polygon):
    x, z = point
    inside = False
    for i, a in enumerate(polygon):
        b = polygon[(i+1) % len(polygon)]
        if (a[1] > z) != (b[1] > z) and x < (b[0]-a[0])*(z-a[1])/(b[1]-a[1])+a[0]:
            inside = not inside
    if inside:
        return 0.0
    return min(distance_segment(x,z,polygon[i],polygon[(i+1)%len(polygon)])
               for i in range(len(polygon)))


def _inside_water(point, polygon):
    """Strict polygon interior; a line along a bank is not a water span."""
    x, z = point
    if min(distance_segment(x, z, polygon[i], polygon[(i+1) % len(polygon)])
           for i in range(len(polygon))) < 1e-7:
        return False
    inside = False
    for i, a in enumerate(polygon):
        b = polygon[(i+1) % len(polygon)]
        if (a[1] > z) != (b[1] > z) and x < (b[0]-a[0])*(z-a[1])/(b[1]-a[1])+a[0]:
            inside = not inside
    return inside


def _intersection_parameter(a, b, c, d):
    """Proper segment-edge intersection parameter, or None for parallel edges."""
    rx, rz = b[0]-a[0], b[1]-a[1]
    sx, sz = d[0]-c[0], d[1]-c[1]
    det = rx*sz-rz*sx
    if abs(det) < 1e-10:
        return None
    qx, qz = c[0]-a[0], c[1]-a[1]
    t = (qx*sz-qz*sx)/det
    u = (qx*rz-qz*rx)/det
    if -1e-8 <= t <= 1+1e-8 and -1e-8 <= u <= 1+1e-8:
        return max(0.0, min(1.0, t))
    return None


def segment_segment_distance(a, b, c, d):
    """Minimum distance between two closed planar segments in metres.

    Unlike sampling endpoints/midpoints, this detects short water crossings
    anywhere along a long OSM way segment.
    """
    if _intersection_parameter(a, b, c, d) is not None:
        return 0.0
    return min(distance_segment(*a, c, d),
               distance_segment(*b, c, d),
               distance_segment(*c, a, b),
               distance_segment(*d, a, b))


def polyline_water_distance(line, polygons):
    """Exact segment-to-boundary distance (zero inside or intersecting)."""
    if len(line) < 2 or not polygons:
        raise ValueError("nonempty line and water polygons required")
    best = float("inf")
    for poly in polygons:
        if any(_inside_water(p, poly) for p in line):
            return 0.0
        for a, b in zip(line, line[1:]):
            for i, c in enumerate(poly):
                best = min(best, segment_segment_distance(
                    a, b, c, poly[(i + 1) % len(poly)]))
                if best == 0.0:
                    return 0.0
    return best


def water_overlap_metrics(line, polygons):
    """Measure actual line length inside mapped water, not just proximity.

    Polygon-edge intersection parameters partition each segment into intervals.
    Midpoints are tested against the UNION of water polygons, so touching
    adjacent OSM water polygons cannot double-count overlap. Pure tangencies
    and boundary-aligned lines do not count as crossings.
    """
    overlap = 0.0
    crossings = 0
    for a, b in zip(line, line[1:]):
        length = math.dist(a, b)
        if length < 1e-8:
            continue
        ts = [0.0, 1.0]
        for polygon in polygons:
            for i, c in enumerate(polygon):
                t = _intersection_parameter(a, b, c, polygon[(i+1) % len(polygon)])
                if t is not None:
                    ts.append(t)
        ts.sort()
        unique = []
        for t in ts:
            if not unique or t-unique[-1] > 1e-8:
                unique.append(t)
        states = []
        for t0, t1 in zip(unique, unique[1:]):
            t = (t0+t1)/2
            mid = (a[0]+(b[0]-a[0])*t, a[1]+(b[1]-a[1])*t)
            wet = any(_inside_water(mid, polygon) for polygon in polygons)
            states.append(wet)
            if wet:
                overlap += length*(t1-t0)
        # Count changes from dry to wet and back, including segment endpoints.
        before = any(_inside_water(a, polygon) for polygon in polygons)
        for wet in states:
            if wet != before:
                crossings += 1
            before = wet
        after = any(_inside_water(b, polygon) for polygon in polygons)
        if before != after:
            crossings += 1
    return overlap, crossings


def water_end_cap_centres(polygons):
    """Midpoints of likely OSM water polygon cut ends (not surveyed bridges)."""
    return [((ring[i][0] + ring[(i+1) % len(ring)][0]) / 2,
             (ring[i][1] + ring[(i+1) % len(ring)][1]) / 2)
            for ring in polygons for i in range(len(ring))
            if is_water_polygon_end_cap(ring, i)]


def bridge_topology_status(highway, overlap, crossings, dry_ends, cap_distance):
    if overlap >= 1.0 and crossings >= 2 and dry_ends:
        return "geometric_water_crossing_candidate"
    # A bridge=yes motor road may span a gap *between* separately mapped
    # water polygons. Absence of polygon overlap is not proof of no bridge.
    # Never promote footways, or claim a physically verified vehicle bridge.
    if (highway in MOTOR_ROADS and overlap <= 1e-7 and dry_ends and
            cap_distance <= MAX_END_CAP_DISTANCE_M):
        return "mapped_water_gap_motor_bridge_candidate"
    return "nearby_unconfirmed"


def motor_endpoint_connections(refs, own_way_id, motor_incidence):
    """Shared OSM nodes at both ends, not proof of legal/physical access."""
    neighbours = []
    for ref in (refs[0], refs[-1]):
        neighbours.append(sorted((wid for wid in motor_incidence.get(ref, ())
                                  if wid != own_way_id), key=int))
    return neighbours


def motor_access_status(tags):
    """Conservative *tag-only* motorcar access audit, not legal permission.

    OSM's more-specific motorcar/motor_vehicle/vehicle tags override access.
    Limited access is excluded from the public-route reachability graph.
    Missing tags are unknown in reality, not proof of public access.
    """
    for key in ("motorcar", "motor_vehicle", "vehicle", "access"):
        value = (tags.get(key) or "").strip().lower()
        if not value:
            continue
        if value in ("no", "private", "permit", "agricultural", "forestry",
                     "emergency"):
            return "restricted", key, value
        if value in ("destination", "delivery", "customers", "official"):
            return "limited", key, value
        if value in ("yes", "designated", "permissive"):
            return "tag_allows", key, value
        return "unresolved", key, value
    return "untagged", None, None


def restriction_relations_near_ways(relations, way_refs):
    """Return restriction relation IDs touching candidate way nodes/segments.

    This is a review inventory, NOT a turn-aware routing implementation.
    """
    results = {wid: [] for wid in way_refs}
    for relation in relations:
        tags = {t.get("k"): t.get("v") for t in relation.findall("tag")}
        if tags.get("type") != "restriction":
            continue
        members = relation.findall("member")
        related_ways = {m.get("ref") for m in members if m.get("type") == "way"}
        via_nodes = {m.get("ref") for m in members
                     if m.get("type") == "node" and m.get("role") == "via"}
        for wid, refs in way_refs.items():
            if wid in related_ways or via_nodes.intersection(refs):
                results[wid].append(relation.get("id"))
    return {wid: sorted(ids, key=int) for wid, ids in results.items()}


def parse_conditional_turn(value, local_time):
    """Evaluate ONLY plain daily HH:MM intervals in a known local clock.

    No weekday, holiday, vehicle or date semantics are inferred. An unknown
    conditional expression returns None and must remain explicitly unhandled.
    The end of an interval is exclusive; overnight windows are supported.
    """
    if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", local_time):
        raise ValueError("audit time must be local HH:MM (00:00-23:59)")
    match = re.fullmatch(
        r"\s*(no_[a-z_]+|only_[a-z_]+)\s*@\s*\(([^()]*)\)\s*", value)
    if not match:
        return None
    active = _daily_windows_active(match.group(2), local_time)
    return (match.group(1), active) if active is not None else None


def _daily_windows_active(expression, local_time):
    """Evaluate simple local-clock windows, rejecting unsupported qualifiers."""
    windows = []
    for part in expression.split(","):
        window = re.fullmatch(
            r"\s*((?:[01]\d|2[0-3]):[0-5]\d)\s*-\s*"
            r"((?:[01]\d|2[0-3]):[0-5]\d)\s*", part)
        if not window or window.group(1) == window.group(2):
            return None
        windows.append((window.group(1), window.group(2)))
    if not windows:
        return None
    return any((start <= local_time < end if start < end
                else local_time >= start or local_time < end)
               for start, end in windows)


def parse_conditional_oneway(value, local_time):
    """Supported daily oneway:conditional values; None means unresolved."""
    if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", local_time):
        raise ValueError("audit time must be local HH:MM (00:00-23:59)")
    match = re.fullmatch(r"\s*(yes|no|-1)\s*@\s*\(([^()]*)\)\s*", value)
    if not match:
        return None
    active = _daily_windows_active(match.group(2), local_time)
    return (match.group(1), active) if active is not None else None


def motor_oneway_direction(tags, audit_time=None):
    """Return +1/-1/0, or None when driving direction cannot be audited.

    Conditional one-way tags must never be silently treated as bidirectional.
    Outside their active window, the unconditional oneway tag still applies.
    """
    conditional = tags.get("oneway:conditional")
    if conditional is not None:
        if audit_time is None:
            return None
        parsed = parse_conditional_oneway(conditional, audit_time)
        if parsed is None:
            return None
        value, active = parsed
        if active:
            return {"yes": 1, "no": 0, "-1": -1}[value]
    value = (tags.get("oneway") or "").strip().lower()
    if value in ("yes", "true", "1"):
        return 1
    if value == "-1":
        return -1
    if value in ("no", "false", "0"):
        return 0
    if not value:
        if tags.get("junction") in ("roundabout", "circular") or tags.get(
                "highway") in ("motorway", "motorway_link"):
            return 1
        return 0
    return None


def turn_restriction_rules(relations, audit_time=None, ways=None):
    """Index supported via-node turns, optionally at a stated local time.

    With no time supplied, conditional rules remain unhandled. Only plain
    daily HH:MM ranges can be evaluated; inactive ones are reported separately.
    Other conditional syntax remains unhandled, never silently permitted.
    """
    if audit_time is not None and not re.fullmatch(
            r"(?:[01]\d|2[0-3]):[0-5]\d", audit_time):
        raise ValueError("audit time must be local HH:MM (00:00-23:59)")
    # A malformed via-node relation must not forbid a legal movement.
    # Both named roads must actually contain the mapped junction node.
    way_nodes = ({way.get("id"): {nd.get("ref") for nd in way.findall("nd")}
                  for way in ways} if ways is not None else None)
    rules = {}
    applied, unhandled, inactive = [], [], []
    for relation in relations:
        tags = {t.get("k"): t.get("v") for t in relation.findall("tag")}
        if tags.get("type") != "restriction":
            continue
        members = relation.findall("member")
        from_ways = [m.get("ref") for m in members
                     if m.get("type") == "way" and m.get("role") == "from"]
        to_ways = [m.get("ref") for m in members
                   if m.get("type") == "way" and m.get("role") == "to"]
        via_nodes = [m.get("ref") for m in members
                     if m.get("type") == "node" and m.get("role") == "via"]
        restriction = tags.get("restriction", "")
        conditional = tags.get("restriction:conditional")
        # Mixed unconditional + conditional semantics are not assumed.
        if conditional is not None and audit_time is not None and not restriction:
            parsed = parse_conditional_turn(conditional, audit_time)
            if parsed is not None:
                restriction, is_active = parsed
            else:
                is_active = None
        else:
            is_active = None
        except_modes = set((tags.get("except") or "").replace(",", ";").split(";"))
        except_modes = {mode.strip() for mode in except_modes}
        supported = (len(from_ways) == len(to_ways) == len(via_nodes) == 1
                     and len(members) == 3
                     and (restriction.startswith("no_") or restriction.startswith("only_"))
                     and (conditional is None or is_active is not None)
                     and not (except_modes & {"motorcar", "motor_vehicle", "vehicle"})
                     and (from_ways != to_ways or restriction in (
                         "no_u_turn", "only_straight_on")))
        if supported and way_nodes is not None:
            via = via_nodes[0]
            supported = (via in way_nodes.get(from_ways[0], set()) and
                         via in way_nodes.get(to_ways[0], set()))
        if not supported:
            unhandled.append(relation.get("id"))
            continue
        if is_active is False:
            inactive.append(relation.get("id"))
            continue
        key = (via_nodes[0], from_ways[0])
        kind = "only" if restriction.startswith("only_") else "no"
        rules.setdefault(key, {"no": set(), "only": set()})[kind].add(to_ways[0])
        applied.append(relation.get("id"))
    return (rules, sorted(applied, key=int), sorted(unhandled, key=int),
            sorted(inactive, key=int))



def via_way_turn_rules(relations, ways):
    """Validate single-via-way unconditional turns against shared OSM nodes.

    Only unambiguous from->via->to sequences with distinct entry/exit
    junctions are enforced. Ambiguous topology stays in the review list.
    """
    by_id = {way.get("id"): [nd.get("ref") for nd in way.findall("nd")]
             for way in ways}
    rules = {}
    applied, unhandled = [], []
    for relation in relations:
        tags = {t.get("k"): t.get("v") for t in relation.findall("tag")}
        if tags.get("type") != "restriction":
            continue
        members = relation.findall("member")
        via = [m.get("ref") for m in members
               if m.get("type") == "way" and m.get("role") == "via"]
        if not via:
            continue
        frm = [m.get("ref") for m in members if m.get("role") == "from"
               and m.get("type") == "way"]
        to = [m.get("ref") for m in members if m.get("role") == "to"
              and m.get("type") == "way"]
        kind = tags.get("restriction", "")
        exceptions = {mode.strip() for mode in
                      (tags.get("except") or "").replace(",", ";").split(";")}
        valid = (len(members) == 3 and len(frm) == len(via) == len(to) == 1
                 and (kind.startswith("no_") or kind.startswith("only_"))
                 and "restriction:conditional" not in tags
                 and not exceptions.intersection({"motorcar", "motor_vehicle", "vehicle"})
                 and all(wid in by_id for wid in (frm[0], via[0], to[0])))
        if valid:
            entry = set(by_id[frm[0]]) & set(by_id[via[0]])
            exit_nodes = set(by_id[via[0]]) & set(by_id[to[0]])
            valid = (len(entry) == len(exit_nodes) == 1 and entry != exit_nodes)
        if not valid:
            unhandled.append(relation.get("id"))
            continue
        entry_node, exit_node = next(iter(entry)), next(iter(exit_nodes))
        rule = (relation.get("id"), exit_node, to[0],
                "only" if kind.startswith("only_") else "no")
        rules.setdefault((entry_node, frm[0], via[0]), []).append(rule)
        applied.append(relation.get("id"))
    return rules, sorted(applied, key=int), sorted(unhandled, key=int)

def directed_motor_route_hops(ways, route_way_ids, relations=(), audit_time=None):
    """Minimum directed node hops, with supported OSM via-node turn rules.

    Route nodes are unheaded starting/ending points, not proven legal turns
    onto the racing line. Conditional turns require an explicit audit_time;
    only plain daily intervals are supported. Multi-via-way rules remain excluded.
    """
    by_id = {way.get("id"): way for way in ways}
    if not route_way_ids or any(wid not in by_id for wid in route_way_ids):
        raise ValueError("route OSM way IDs missing from source snapshot")
    route_nodes = set()
    for wid in route_way_ids:
        route_nodes.update(nd.get("ref") for nd in by_id[wid].findall("nd"))
    rules, _, _, _ = turn_restriction_rules(relations, audit_time, ways)
    via_rules, _, _ = via_way_turn_rules(relations, ways)
    # A forward only_* rule constrains FROM -> VIA -> (any TO except
    # the named one). In reverse, we must reject the FROM entry only
    # when the previously traversed exit way is NOT the allowed TO.
    # Simply reversing "only" would incorrectly forbid unrelated FROM
    # roads after the allowed TO and permit forbidden TO -> FROM paths.
    reverse_via_rules = {}
    reverse_only_via_rules = {}
    for (entry, frm, via), items in via_rules.items():
        for rid, exit_node, to, kind in items:
            if kind == "only":
                reverse_only_via_rules.setdefault((exit_node, via), []).append(
                    (rid, entry, frm, to))
            else:
                reverse_via_rules.setdefault((exit_node, to, via), []).append(
                    (rid, entry, frm, kind))
    forward, backward = {}, {}
    for way in ways:
        tags = {t.get("k"): t.get("v") for t in way.findall("tag")}
        if tags.get("highway") not in MOTOR_ROADS:
            continue
        if motor_access_status(tags)[0] in ("restricted", "limited", "unresolved"):
            continue
        direction = motor_oneway_direction(tags, audit_time)
        if direction is None:
            # Unknown/conditional direction is NOT evidence of a legal path.
            continue
        refs = [nd.get("ref") for nd in way.findall("nd")]
        wid = way.get("id")
        for a, b in zip(refs, refs[1:]):
            if direction >= 0:
                forward.setdefault(a, set()).add((b, wid))
                backward.setdefault(b, set()).add((a, wid))
            if direction <= 0:
                forward.setdefault(b, set()).add((a, wid))
                backward.setdefault(a, set()).add((b, wid))

    def allowed(via, incoming_way, outgoing_way, previous_node, next_node):
        if incoming_way is None or outgoing_way is None:
            # The race-route start/end has no known approach/departure.
            return True
        rule = rules.get((via, incoming_way))
        if rule is None:
            return True
        if incoming_way == outgoing_way:
            # Continuing straight through a via node on the same OSM way
            # is NOT exempt from an only_* turn: only_right_turn can ban
            # straight-ahead travel even when the way was not split here.
            # A same-way no_u_turn forbids *reversing direction* at the
            # via node, not continuing through on that same OSM way.
            # Keep the prior node in BFS state so reverse routing agrees.
            if (previous_node == next_node and
                    outgoing_way in rule["no"]):
                return False
            return not rule["only"] or outgoing_way in rule["only"]
        return (outgoing_way not in rule["no"] and
                (not rule["only"] or outgoing_way in rule["only"]))

    def hops_from_sources(edges, reverse=False):
        # A node-only BFS loses the incoming way and can illegally turn.
        # State keeps the preceding way AND node (next in reverse search)
        # so a same-way U-turn cannot masquerade as straight travel.
        initial = {(node, None, (), None) for node in route_nodes}
        hops = {state: 0 for state in initial}
        queue = deque(initial)
        minimum = {node: 0 for node in route_nodes}
        via_index = reverse_via_rules if reverse else via_rules
        while queue:
            node, other_way, active, previous_node = queue.popleft()
            for neighbour, edge_way in edges.get(node, ()):
                if reverse:
                    permitted = allowed(node, edge_way, other_way,
                                        previous_node, neighbour)
                else:
                    permitted = allowed(node, other_way, edge_way,
                                        previous_node, neighbour)
                if not permitted:
                    continue
                # A via-way rule is activated at its mapped entry junction,
                # carried across its segments, and checked at its exit.
                if edge_way == other_way:
                    next_active = active
                else:
                    blocked = False
                    for rid, exit_node, target_way, kind in active:
                        if node == exit_node and (
                                (kind == "no" and edge_way == target_way) or
                                (kind == "only" and edge_way != target_way)):
                            blocked = True
                            break
                    if blocked:
                        continue
                    next_active = tuple(via_index.get(
                        (node, other_way, edge_way), ()))
                    if reverse:
                        next_active += tuple(
                            (rid, entry, frm, "no")
                            for rid, entry, frm, allowed_to in
                            reverse_only_via_rules.get((node, edge_way), ())
                            # A route endpoint has no known following TO.
                            if other_way is not None and other_way != allowed_to)
                state = (neighbour, edge_way, next_active, node)
                if state in hops:
                    continue
                count = hops[(node, other_way, active, previous_node)] + 1
                hops[state] = count
                minimum[neighbour] = min(minimum.get(neighbour, count), count)
                queue.append(state)
        return minimum

    return hops_from_sources(forward), hops_from_sources(backward, reverse=True)


def line_midpoint_direction(line):
    """Arc-length midpoint and unit endpoint direction of a projected way."""
    total = sum(math.dist(a, b) for a, b in zip(line, line[1:]))
    dx, dz = line[-1][0]-line[0][0], line[-1][1]-line[0][1]
    magnitude = math.hypot(dx, dz)
    direction = (dx/magnitude, dz/magnitude) if magnitude > 1e-8 else (0.0, 0.0)
    distance = total/2
    for a, b in zip(line, line[1:]):
        length = math.dist(a, b)
        if distance <= length and length > 0:
            t = distance/length
            return ((a[0]+t*(b[0]-a[0]), a[1]+t*(b[1]-a[1])), direction)
        distance -= length
    return line[-1], direction


def motor_bridge_review_clusters(lines, max_separation_m=30.0):
    """Group close, parallel motor bridge *ways* for map review only.

    Two carriageways at one crossing should not automatically be reported
    as two verified physical bridges. Grouping is an approximate location,
    not a determination that structures or legal access are shared.
    """
    groups = []
    for wid in sorted(lines, key=int):
        mid, direction = line_midpoint_direction(lines[wid])
        for group in groups:
            anchor_mid, anchor_direction = group["anchor"]
            parallel = abs(sum(a*b for a, b in zip(direction, anchor_direction)))
            if math.dist(mid, anchor_mid) <= max_separation_m and parallel >= 0.85:
                group["ids"].append(wid)
                break
        else:
            groups.append({"anchor": (mid, direction), "ids": [wid]})
    return {wid: "review-site-%02d" % (i+1)
            for i, group in enumerate(groups) for wid in group["ids"]}



def route_centerline_metrics(bridge_line, route_line):
    """Planar crossing and proximity to the *mapped* race route centreline.

    A near miss is not a traversable junction; only shared OSM nodes and
    traffic/access tags could establish connectivity. Route is a closed line.
    """
    if len(bridge_line) < 2 or len(route_line) < 2:
        raise ValueError("bridge and route need at least two coordinates")
    best_distance = float("inf")
    best_segment = None
    best_alignment = None
    intersections = set()
    for i, (a, b) in enumerate(zip(bridge_line, bridge_line[1:])):
        bdx, bdz = b[0]-a[0], b[1]-a[1]
        blen = math.hypot(bdx, bdz)
        for j, (c, d) in enumerate(zip(route_line, route_line[1:])):
            rdx, rdz = d[0]-c[0], d[1]-c[1]
            rlen = math.hypot(rdx, rdz)
            if blen < 1e-8 or rlen < 1e-8:
                continue
            distance = segment_segment_distance(a, b, c, d)
            if distance < best_distance:
                best_distance, best_segment = distance, j
                best_alignment = abs((bdx*rdx+bdz*rdz)/(blen*rlen))
            t = _intersection_parameter(a, b, c, d)
            if t is not None:
                # A shared route vertex belongs to two segments but is one
                # geometric intersection (and not necessarily a junction).
                intersections.add((round(a[0]+t*bdx, 6),
                                   round(a[1]+t*bdz, 6)))
    if best_segment is None:
        raise ValueError("bridge and route require nondegenerate segments")
    return round(best_distance, 2), len(intersections), best_segment, round(best_alignment, 3)


def load_route_for_bridge_audit(route_path, expected_sha):
    """Require the same OSM snapshot as bridge and water inputs."""
    route = json.loads(Path(route_path).read_text(encoding="utf-8"))
    if route.get("properties", {}).get("snapshot_sha256") != expected_sha:
        raise ValueError("bridge/route OSM snapshot hashes differ")
    geometry = route.get("geometry", {})
    coords = geometry.get("coordinates", [])
    if (geometry.get("type") != "LineString" or len(coords) < 4 or
            coords[0] != coords[-1]):
        raise ValueError("bridge audit route must be a closed LineString")
    return [project_lonlat(*point) for point in coords]


def extract(osm_path, water_path, route_path=None, audit_time=None):
    if audit_time is not None and not re.fullmatch(
            r"(?:[01]\d|2[0-3]):[0-5]\d", audit_time):
        raise ValueError("audit time must be local HH:MM (00:00-23:59)")
    source = Path(osm_path)
    sha = hashlib.sha256(source.read_bytes()).hexdigest()
    water = json.loads(Path(water_path).read_text(encoding="utf-8"))
    props = water.get("properties", {})
    if props.get("snapshot_sha256") != sha:
        raise ValueError("bridge/water OSM snapshot hashes differ")
    polygons, _ = load_water_polygons(water_path)
    route_line = (load_route_for_bridge_audit(route_path, sha)
                  if route_path is not None else None)
    end_caps = water_end_cap_centres(polygons)
    root = ET.parse(source).getroot()
    if root.tag != "osm":
        raise ValueError("expected OSM XML")
    ways = root.findall("way")
    relations = root.findall("relation")
    unresolved_oneway_ids = []
    for way in ways:
        tags = {t.get("k"): t.get("v") for t in way.findall("tag")}
        if (tags.get("highway") in MOTOR_ROADS and
                motor_access_status(tags)[0] not in
                ("restricted", "limited", "unresolved") and
                motor_oneway_direction(tags, audit_time) is None):
            unresolved_oneway_ids.append(way.get("id"))
    unresolved_oneway_ids.sort(key=int)
    if route_path is not None:
        route_way_ids = json.loads(Path(route_path).read_text(
            encoding="utf-8")).get("properties", {}).get("osm_way_ids")
        if not isinstance(route_way_ids, list):
            raise ValueError("bridge route needs OSM way IDs for directed audit")
        from_route, to_route = directed_motor_route_hops(
            ways, route_way_ids, relations, audit_time)
    else:
        from_route, to_route = {}, {}
    nodes = {node.get("id"): (float(node.get("lon")), float(node.get("lat")))
             for node in root.findall("node")}
    # Build shared-node evidence from *all* OSM motor roads in the snapshot,
    # not just bridge=yes ways. This does not verify traffic direction or access.
    motor_incidence = {}
    for way in ways:
        tags = {t.get("k"): t.get("v") for t in way.findall("tag")}
        if tags.get("highway") not in MOTOR_ROADS:
            continue
        for nd in way.findall("nd"):
            motor_incidence.setdefault(nd.get("ref"), set()).add(way.get("id"))
    bridge_way_refs = {
        way.get("id"): [nd.get("ref") for nd in way.findall("nd")]
        for way in ways
        if any(t.get("k") == "bridge" and t.get("v") == "yes"
               for t in way.findall("tag"))
    }
    restriction_neighbours = restriction_relations_near_ways(
        relations, bridge_way_refs)
    _, node_applied, node_unhandled, node_inactive = turn_restriction_rules(
        relations, audit_time, ways)
    _, via_applied, via_unhandled = via_way_turn_rules(relations, ways)
    applied_turns = sorted(set(node_applied + via_applied), key=int)
    unhandled_turns = sorted((set(node_unhandled + via_unhandled) -
                              set(applied_turns)), key=int)
    features = []
    review_lines = {}
    for way in sorted(ways, key=lambda w: int(w.get("id"))):
        tags = {t.get("k"): t.get("v") for t in way.findall("tag")}
        if tags.get("bridge") != "yes" or not tags.get("highway"):
            continue
        refs = [nd.get("ref") for nd in way.findall("nd")]
        if len(refs) < 2 or any(ref not in nodes for ref in refs):
            continue
        coords = [nodes[ref] for ref in refs]
        if not all(98.97 < lon < 99.0 and 18.77 < lat < 18.8
                   for lon,lat in coords):
            continue
        projected = [project_lonlat(lon, lat) for lon,lat in coords]
        # Check every full segment against water edges: midpoint sampling
        # misses narrow moat spans near one end of a long OSM way segment.
        distance = polyline_water_distance(projected, polygons)
        if distance > MAX_WATER_DISTANCE_M:
            continue
        overlap, crossings = water_overlap_metrics(projected, polygons)
        dry_ends = all(not any(_inside_water(p, poly) for poly in polygons)
                       for p in (projected[0], projected[-1]))
        cap_distance = min((min(distance_segment(*cap, a, b)
                                for a, b in zip(projected, projected[1:]))
                            for cap in end_caps), default=float("inf"))
        status = bridge_topology_status(tags["highway"], overlap, crossings,
                                        dry_ends, cap_distance)
        access_status, access_key, access_value = motor_access_status(tags)
        if tags["highway"] not in MOTOR_ROADS:
            access_status = "not_motor_road"
        connected = (motor_endpoint_connections(refs, way.get("id"), motor_incidence)
                     if tags["highway"] in MOTOR_ROADS else [[], []])
        if status == "mapped_water_gap_motor_bridge_candidate":
            review_lines[way.get("id")] = projected
        route_metrics = (route_centerline_metrics(projected, route_line)
                         if route_line is not None else None)
        # For one-way candidates, first/last OSM nodes are entry/exit.
        # Counts are graph connectivity evidence, NOT permission to drive.
        entry_ref, exit_ref = refs[0], refs[-1]
        if tags.get("oneway") == "-1":
            entry_ref, exit_ref = exit_ref, entry_ref
        route_entry_hops = (from_route.get(entry_ref)
                            if route_path is not None and tags["highway"] in MOTOR_ROADS
                            else None)
        route_exit_hops = (to_route.get(exit_ref)
                           if route_path is not None and tags["highway"] in MOTOR_ROADS
                           else None)
        features.append({
            "type": "Feature",
            "properties": {
                "osm_way_id": way.get("id"), "bridge": "yes",
                "highway": tags["highway"],
                "name": tags.get("name", ""),
                "oneway": tags.get("oneway"),
                "lanes": tags.get("lanes"),
                "surface": tags.get("surface"),
                "motor_access_tag_status": access_status,
                "motor_access_decisive_tag": ({"key": access_key, "value": access_value}
                                              if access_key else None),
                "nearby_turn_restriction_relation_ids": restriction_neighbours.get(
                    way.get("id"), []),
                "motor_road_connected_ends": sum(bool(n) for n in connected),
                "motor_road_endpoint_neighbors": connected,
                "route_centerline_distance_m": route_metrics[0] if route_metrics else None,
                "route_centerline_intersections": route_metrics[1] if route_metrics else None,
                "route_nearest_segment_index": route_metrics[2] if route_metrics else None,
                "route_alignment_abs_dot": route_metrics[3] if route_metrics else None,
                "directed_route_to_bridge_entry_hops": route_entry_hops,
                "directed_bridge_exit_to_route_hops": route_exit_hops,
                "water_proximity_m": round(distance, 2),
                "mapped_water_overlap_m": round(overlap, 2),
                "mapped_water_boundary_crossings": crossings,
                "mapped_water_end_cap_proximity_m": (round(cap_distance, 2)
                                                     if math.isfinite(cap_distance)
                                                     else None),
                "topology_status": status,
                "review_status": "OSM mapped-water geometry only; physical bridge/width not verified"
            },
            "geometry": {"type": "LineString",
                         "coordinates": [[lon,lat] for lon,lat in coords]}
        })
    clusters = motor_bridge_review_clusters(review_lines)
    for feature in features:
        feature["properties"]["motor_bridge_review_site"] = clusters.get(
            feature["properties"]["osm_way_id"])
    return {
        "type": "FeatureCollection",
        "properties": {
            "source": SOURCE, "license": LICENSE,
            "source_url": "https://www.openstreetmap.org/copyright",
            "snapshot_sha256": sha,
            "water_proximity_threshold_m": MAX_WATER_DISTANCE_M,
            "mapped_water_end_cap_review_threshold_m": MAX_END_CAP_DISTANCE_M,
            "end_cap_review_method": "motor bridge=yes road near geometrically inferred water polygon cut end; NOT confirmed vehicle passage",
            "review_status": "OSM bridge=yes candidate inventory, NOT verified moat spans",
            "model_status": "no bridge 3D geometry generated",
            "motor_bridge_review_sites": len(set(clusters.values())),
            "motor_bridge_review_site_method": "within 30m and parallel (abs dot >= 0.85); groups OSM ways for review, NOT confirmed physical bridges",
            "motor_connection_method": "shared endpoint OSM node with other motor highway way; NOT proof of driving legality or physical access",
            "route_relation_method": "minimum full-segment distance to same-snapshot OSM race route centreline; intersections and direction alignment are geometric only, NOT proof of traffic access",
            "directed_route_connectivity_method": "minimum directed OSM node-edge hops with incoming/outgoing way and previous-node state (same-way no_u_turn enforced), honoring known oneway, conditional oneway at audit time, roundabout, access exclusions, unconditional via-node and unambiguous single-via-way no_*/only_* restrictions; excludes unresolved conditional/multi-via-way restrictions, lane transitions and actual driving legality",
            "motor_oneway_unresolved_way_ids": unresolved_oneway_ids,
            "motor_oneway_audit_method": "oneway:conditional only evaluated for simple daily windows with explicit local HH:MM; otherwise affected ways excluded from graph; unknown oneway values excluded; motorway and roundabout default one-way",
            "motor_access_audit_method": "motorcar > motor_vehicle > vehicle > access tag precedence; restricted/limited/unresolved ways excluded from directed graph; missing tags are NOT verified permission",
            "turn_restriction_relation_count": sum(
                any(t.get("k") == "type" and t.get("v") == "restriction"
                    for t in rel.findall("tag")) for rel in relations),
            "turn_restriction_audit_method": "unconditional via-node and unambiguous single-via-way no_*/only_* restrictions enforced; with explicit local HH:MM, plain daily via-node conditional windows also evaluated (end exclusive); other conditional/ambiguous/unsupported rules enumerated; NOT legal access proof",
            "turn_restriction_audit_local_time": audit_time,
            "turn_restrictions_inactive_relation_ids": node_inactive,
            "turn_restrictions_applied_relation_ids": applied_turns,
            "turn_restrictions_unhandled_relation_ids": unhandled_turns,
            "topology_method": "line segments clipped against union of OSM water polygons; no field verification",
            "proximity_method": "minimum full-way segment to water polygon distance (not endpoint sampling)"
        },
        "features": features
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--osm-xml", required=True, type=Path)
    parser.add_argument("--water-geojson", required=True, type=Path)
    parser.add_argument("--route-geojson", default=DEFAULT_GEOJSON, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--audit-time", default=None, metavar="HH:MM",
                        help="optional local clock time for plain daily conditional turns")
    args = parser.parse_args()
    result = extract(args.osm_xml, args.water_geojson, args.route_geojson,
                     args.audit_time)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n",
                        encoding="utf-8")
    print("OSM bridge=yes candidates near mapped water:", len(result["features"]))


if __name__ == "__main__":
    main()
