#!/usr/bin/env python3
"""Offline regression checks for the M2 track schematic / mesh generator."""
import importlib.util
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "build_moat_blockout.py"
spec = importlib.util.spec_from_file_location("moat_blockout", SCRIPT)
blockout = importlib.util.module_from_spec(spec)
spec.loader.exec_module(blockout)


class MoatBlockoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.points = blockout.build_points()
        cls.route = blockout.metadata(cls.points)
        cls.model = blockout.model(cls.points)

    def test_track_closed_perimeter_and_clockwise(self):
        p = self.points
        self.assertGreater(len(p), 500)
        self.assertAlmostEqual(p[0][0], blockout.HALF_WIDTH)
        self.assertAlmostEqual(p[0][1], 0)
        self.assertLessEqual(blockout.perimeter(p) - 6540, 6540*.03)
        self.assertGreater(blockout.perimeter(p), 6540*.97)
        # In screen-style axes (+X east, +Z south), clockwise area is +.
        signed_area = sum(p[i][0]*p[(i+1)%len(p)][1] -
                          p[(i+1)%len(p)][0]*p[i][1] for i in range(len(p)))
        self.assertGreater(signed_area, 0)
        self.assertLess(math.dist(p[0],p[-1]), 12)

    def test_no_degenerate_polyline_sections(self):
        pts=self.points
        for i,p in enumerate(pts):
            d=math.dist(p,pts[(i+1)%len(pts)])
            self.assertGreater(d,1e-5)
            self.assertLess(d,11)

    def test_four_checkpoints_in_expected_order(self):
        cps=self.route["checkpoints"]
        self.assertEqual([c["id"] for c in cps],[0,1,2,3])
        self.assertEqual(len(set(c["point_index"] for c in cps)),4)
        self.assertGreater(cps[0]["x"], 800)
        self.assertGreater(cps[1]["z"], 800)
        self.assertLess(cps[2]["x"], -800)
        self.assertLess(cps[3]["z"], -800)

    def test_materials_and_mesh_indices(self):
        self.assertEqual(len(self.model["meshes"]),6)
        self.assertEqual(len(self.model["materials"]),5)
        self.assertTrue(blockout.validate_geometry(self.model))
        for mesh in self.model["meshes"]:
            self.assertGreater(len(mesh["indices"]),0)
            self.assertEqual(len(mesh["indices"])%3,0)

    def test_road_and_water_face_upwards(self):
        for mesh in self.model["meshes"][:4]:
            p=mesh["positions"]
            ids=mesh["indices"]
            a,b,c=ids[:3]
            ax,az=p[3*a],p[3*a+2]
            bx,bz=p[3*b],p[3*b+2]
            cx,cz=p[3*c],p[3*c+2]
            # y component of (B-A) x (C-A) in X/Z ground plane.
            normal_y=(bz-az)*(cx-ax)-(bx-ax)*(cz-az)
            self.assertGreater(normal_y,0,mesh["name"])

    def test_stylised_dashes_are_narrow_upward_and_noncolliding(self):
        marking=self.model["meshes"][-1]
        self.assertEqual(marking["name"],"game-dashed-centreline")
        self.assertEqual(len(marking["indices"])%6,0)
        self.assertGreater(len(marking["indices"]),500)
        p=marking["positions"]
        for i in range(0,len(p),12):
            corners=[p[i+j:i+j+3] for j in (0,3,6,9)]
            self.assertTrue(all(abs(v[1]-.103)<1e-6 for v in corners))
            self.assertAlmostEqual(math.dist(corners[0],corners[1]),.24,places=2)
            self.assertLessEqual(math.dist(corners[0],corners[2]),5.01)
            a,b,c=corners[:3]
            normal_y=(b[2]-a[2])*(c[0]-a[0])-(b[0]-a[0])*(c[2]-a[2])
            self.assertGreater(normal_y,0)

    def test_import_geojson_clockwise_and_reject_gaps(self):
        earth=6371008.8
        lat0=math.radians(blockout.CENTER_LAT)
        def gps(x,z):
            return [blockout.CENTER_LON+math.degrees(x/(earth*math.cos(lat0))),
                    blockout.CENTER_LAT-math.degrees(z/earth)]
        coords=[gps(x,z) for x,z in reversed(self.points)]
        coords.append(coords[0])
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/"route.geojson"
            f.write_text(json.dumps({"type":"LineString","coordinates":coords}), encoding="utf-8")
            points,sha=blockout.import_geojson(f)
            self.assertEqual(len(sha),64)
            self.assertGreater(len(points),600)
            self.assertTrue(6540*.97 <= blockout.perimeter(points) <= 6540*1.03)
            area=sum(points[i][0]*points[(i+1)%len(points)][1]-
                     points[(i+1)%len(points)][0]*points[i][1]
                     for i in range(len(points)))
            self.assertGreater(area,0)
            self.assertGreater(points[0][0],790)
            # A disconnected road must not be silently closed.
            coords[-1]=[99.1,18.9]
            f.write_text(json.dumps({"type":"LineString","coordinates":coords}), encoding="utf-8")
            with self.assertRaises(ValueError):
                blockout.import_geojson(f)

    def test_reject_self_crossings_and_bad_geojson(self):
        with self.assertRaisesRegex(ValueError,"self-intersection"):
            blockout.validate_simple_loop([
                (-800,-800),(800,800),(-800,800),(800,-800)])
        earth=6371008.8
        lat0=math.radians(blockout.CENTER_LAT)
        def gps(x,z):
            return [blockout.CENTER_LON+math.degrees(x/(earth*math.cos(lat0))),
                    blockout.CENTER_LAT-math.degrees(z/earth)]
        coords=[gps(x,z) for x,z in self.points]
        coords.append(coords[0])
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/"route.geojson"
            def write(c):
                f.write_text(json.dumps({"type":"LineString","coordinates":c}), encoding="utf-8")
            # The previous importer silently joined up to 20 m of missing
            # OSM road with an imaginary straight segment.
            gap=[list(c) for c in coords]
            gap[-1][1]+=0.00009  # ~10 metres at this latitude
            write(gap)
            with self.assertRaisesRegex(ValueError,"not explicitly closed"):
                blockout.import_geojson(f)
            # Reject faraway routes even if their perimeter matches.
            shifted=[[lon+1,lat] for lon,lat in coords]
            write(shifted)
            with self.assertRaisesRegex(ValueError,"old-city vicinity"):
                blockout.import_geojson(f)
            # Invalid coordinates must fail before projecting.
            invalid=[list(c) for c in coords]
            invalid[1]=[190,18.79]
            write(invalid)
            with self.assertRaisesRegex(ValueError,"out of range"):
                blockout.import_geojson(f)

    def test_import_rotated_route_has_tangent_aligned_spawn(self):
        # Rotating the schematic loop 45 degrees forces an oblique start
        # tangent and checks that cars won't always face world +Z.
        theta=math.pi/4
        rotated=[(x*math.cos(theta)-z*math.sin(theta),
                  x*math.sin(theta)+z*math.cos(theta))
                 for x,z in self.points]
        earth=6371008.8
        lat0=math.radians(blockout.CENTER_LAT)
        def gps(x,z):
            return [blockout.CENTER_LON+math.degrees(x/(earth*math.cos(lat0))),
                    blockout.CENTER_LAT-math.degrees(z/earth)]
        coords=[gps(x,z) for x,z in rotated]
        coords.append(coords[0])
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/"route.geojson"
            f.write_text(json.dumps({"type":"LineString","coordinates":coords}), encoding="utf-8")
            points,_=blockout.import_geojson(f)
        route=blockout.metadata(points)
        yaw=route["spawn"]["yaw_rad"]
        q=route["spawn"]["quaternion"]
        self.assertGreater(abs(yaw),0.3)
        self.assertAlmostEqual(sum(v*v for v in q),1,places=6)
        dx=points[1][0]-points[-1][0]
        dz=points[1][1]-points[-1][1]
        length=math.hypot(dx,dz)
        # Rotating the car's local forward (0,0,1) by its yaw.
        self.assertAlmostEqual(math.sin(yaw),dx/length,places=6)
        self.assertAlmostEqual(math.cos(yaw),dz/length,places=6)
        self.assertAlmostEqual(2*math.atan2(q[1],q[3]),yaw,places=6)

    def test_checkpoint_gate_columns_follow_road_normal(self):
        # A rotated ring must get diagonally oriented gates, not old
        # world-X/world-Z axis-aligned blocks.
        angle=math.pi/4
        points=[(x*math.cos(angle)-z*math.sin(angle),
                 x*math.sin(angle)+z*math.cos(angle))
                for x,z in self.points]
        gate=blockout.gate_mesh(points)
        positions=gate["positions"]
        def center(vertex_start):
            vertices=[positions[3*i:3*i+3]
                      for i in range(vertex_start,vertex_start+8)]
            return (sum(v[0] for v in vertices)/8,
                    sum(v[2] for v in vertices)/8)
        for gate_id in range(4):
            index=[0,len(points)//4,len(points)//2,3*len(points)//4][gate_id]
            nx,nz=blockout.normal(points,index)
            a=center(gate_id*24)
            b=center(gate_id*24+8)
            dx=b[0]-a[0];dz=b[1]-a[1]
            self.assertAlmostEqual(math.hypot(dx,dz),18.4,places=2)
            self.assertAlmostEqual((dx*nx+dz*nz)/18.4,1,places=3)
            self.assertAlmostEqual(dx*nz-dz*nx,0,places=2)

    def test_game_turn_warning_signs_are_sparse_and_outside_road(self):
        # The rounded schematic has no 28-degree point turns.
        self.assertEqual(blockout.sharp_turn_candidates(self.points),[])
        self.assertEqual(blockout.sharp_turn_warning_meshes(self.points),[])
        osm_points,_=blockout.import_geojson(blockout.DEFAULT_GEOJSON)
        turns=blockout.sharp_turn_candidates(osm_points)
        self.assertEqual(len(turns),2)
        self.assertEqual([1 if a>0 else -1 for _,a in turns],[1,1])
        signs=blockout.sharp_turn_warning_meshes(osm_points)
        self.assertEqual([m["name"] for m in signs],
                         ["game-sharp-turn-signs","game-sharp-turn-arrows"])
        self.assertEqual(len(signs[0]["indices"]),2*2*12*3)
        self.assertEqual(len(signs[1]["indices"]),2*9)
        for i,_ in turns:
            self.assertGreater(abs(_),28)
        # Each board centre is 10.4m off the lane centre, not in the
        # 7m driveable road. They do not enter the collision model.
        board=signs[0]["positions"]
        for k in range(2):
            offset=k*2*8*3
            v=[board[offset+j:offset+j+3] for j in range(0,48,3)]
            cx=sum(p[0] for p in v)/16
            cz=sum(p[2] for p in v)/16
            self.assertGreater(min(math.dist((cx,cz),pt) for pt in osm_points),8.7)
        asset=blockout.model(osm_points)
        self.assertTrue(blockout.validate_geometry(asset))
        self.assertEqual(sum(m["name"]=="game-sharp-turn-signs"
                             for m in asset["meshes"]),1)
        self.assertEqual(asset["meshes"][-1]["name"],"game-dashed-centreline")

    def test_warning_sightline_switches_sides_when_building_hides_board(self):
        points,_=blockout.import_geojson(blockout.DEFAULT_GEOJSON)
        apex,_angle=blockout.sharp_turn_candidates(points)[0]
        i=apex
        travelled=0.0
        while travelled<blockout.SHARP_TURN_WARNING_LEAD_M:
            prev=(i-1)%len(points)
            travelled+=math.dist(points[prev],points[i])
            i=prev
        nx,nz=blockout.normal(points,i)
        preferred=(points[i][0]+nx*10.4,points[i][1]+nz*10.4)
        other=(points[i][0]-nx*10.4,points[i][1]-nz*10.4)
        origin=points[(i-5)%len(points)]
        # Building blocks the view, not the sign pole itself. A mere
        # polygon_clearance check would keep the hidden preferred board.
        center=(origin[0]*.2+preferred[0]*.8,
                origin[1]*.2+preferred[1]*.8)
        footprint=[(center[0]-1.2,center[1]-1.2),
                   (center[0]+1.2,center[1]-1.2),
                   (center[0]+1.2,center[1]+1.2),
                   (center[0]-1.2,center[1]+1.2)]
        self.assertGreater(blockout.polygon_clearance(preferred,footprint),1.6)
        self.assertFalse(blockout.warning_approach_sightlines(
            points,i,preferred,[(footprint,8)]))
        # A short wall below the board must not be treated as occlusion.
        self.assertTrue(blockout.warning_approach_sightlines(
            points,i,preferred,[(footprint,2.0)]))
        self.assertTrue(blockout.warning_approach_sightlines(
            points,i,other,[(footprint,8)]))
        signs=blockout.sharp_turn_warning_meshes(points,buildings=[(footprint,8)])
        vertices=[signs[0]["positions"][j:j+3] for j in range(0,24,3)]
        actual=(sum(v[0] for v in vertices)/8,
                sum(v[2] for v in vertices)/8)
        self.assertLess(math.dist(actual,other),.01)

    def test_turn_warning_has_advance_braking_distance(self):
        # A 30m warning left less than one second at competitive speed;
        # preserve a longer lead even if the route is resampled differently.
        points,_=blockout.import_geojson(blockout.DEFAULT_GEOJSON)
        signs=blockout.sharp_turn_warning_meshes(points)
        self.assertEqual(len(signs[0]["positions"]),2*16*3)
        for k,(apex,angle) in enumerate(blockout.sharp_turn_candidates(points)):
            vertices=[signs[0]["positions"][3*j:3*j+3]
                      for j in range(k*16,k*16+8)]
            center=(sum(v[0] for v in vertices)/8,
                    sum(v[2] for v in vertices)/8)
            i=apex
            travelled=0.0
            while travelled<blockout.SHARP_TURN_WARNING_LEAD_M:
                prev=(i-1)%len(points)
                travelled+=math.dist(points[prev],points[i])
                i=prev
            nx,nz=blockout.normal(points,i)
            side=1 if angle>0 else -1
            expected=(points[i][0]+nx*side*10.4,
                      points[i][1]+nz*side*10.4)
            self.assertLess(math.dist(center,expected),0.01)
            self.assertGreaterEqual(travelled,80.0)
            self.assertLess(travelled,92.0)
            self.assertGreater(travelled/(.62*60),2.0)

    def test_sharp_turn_signs_avoid_mapped_moat_water_and_buildings(self):
        # OSM snapshot: the old 10.4m bend-side rule put the second
        # warning sign inside a mapped moat water polygon.
        points,_=blockout.import_geojson(blockout.DEFAULT_GEOJSON)
        water,_=blockout.load_water_polygons(blockout.DEFAULT_WATER)
        buildings,_=blockout.load_roadside_buildings(blockout.DEFAULT_BUILDINGS)
        signs=blockout.sharp_turn_warning_meshes(points,water,buildings)
        self.assertEqual(len(signs),2)
        poles=signs[0]["positions"]
        self.assertEqual(len(poles),2*16*3)
        for k in range(2):
            vertices=[poles[3*j:3*j+3] for j in range(k*16,k*16+8)]
            center=(sum(v[0] for v in vertices)/8,
                    sum(v[2] for v in vertices)/8)
            self.assertGreaterEqual(min(blockout.polygon_clearance(center,poly)
                                        for poly in water),1.6)
            self.assertGreaterEqual(min(blockout.polygon_clearance(center,poly)
                                        for poly,_ in buildings),1.6)
            # The opposite-side fallback must not cut into a nearby bend.
            def segment_distance(a,b):
                dx=b[0]-a[0];dz=b[1]-a[1]
                t=max(0,min(1,((center[0]-a[0])*dx+
                               (center[1]-a[1])*dz)/(dx*dx+dz*dz)))
                return math.dist(center,(a[0]+t*dx,a[1]+t*dz))
            self.assertGreater(min(segment_distance(points[j],
                             points[(j+1)%len(points)])
                             for j in range(len(points))),9.5)
        # Confirm the main model pipeline passes the footprints through.
        asset=blockout.model(points,water_polygons=water,buildings=buildings,
                             gates=[{"point_index":0,"x":points[0][0],
                                     "z":points[0][1]}])
        actual=next(m for m in asset["meshes"]
                    if m["name"]=="game-sharp-turn-signs")
        self.assertEqual(actual["positions"],signs[0]["positions"])

    def test_sharp_turn_sign_skips_when_both_road_sides_obstructed(self):
        points,_=blockout.import_geojson(blockout.DEFAULT_GEOJSON)
        apex,angle=blockout.sharp_turn_candidates(points)[0]
        i=apex;travel=0
        while travel<blockout.SHARP_TURN_WARNING_LEAD_M:
            prev=(i-1)%len(points)
            travel+=math.dist(points[prev],points[i]);i=prev
        nx,nz=blockout.normal(points,i)
        squares=[]
        for side in (-1,1):
            x=points[i][0]+nx*side*10.4
            z=points[i][1]+nz*side*10.4
            squares.append([(x-3,z-3),(x+3,z-3),(x+3,z+3),(x-3,z+3)])
        signs=blockout.sharp_turn_warning_meshes(points,squares)
        self.assertEqual(len(signs),2)
        self.assertEqual(len(signs[0]["positions"]),16*3)
        # Block both sides of every bend: no empty Geometry/Face3 reaches r50.
        for apex,_ in blockout.sharp_turn_candidates(points)[1:]:
            i=apex;travel=0
            while travel<blockout.SHARP_TURN_WARNING_LEAD_M:
                prev=(i-1)%len(points)
                travel+=math.dist(points[prev],points[i]);i=prev
            nx,nz=blockout.normal(points,i)
            for side in (-1,1):
                x=points[i][0]+nx*side*10.4
                z=points[i][1]+nz*side*10.4
                squares.append([(x-3,z-3),(x+3,z-3),
                                (x+3,z+3),(x-3,z+3)])
        self.assertEqual(blockout.sharp_turn_warning_meshes(points,squares),[])
        asset=blockout.model(points,water_polygons=squares)
        self.assertFalse(any(m["name"].startswith("game-sharp-turn-")
                             for m in asset["meshes"]))

    def test_default_osm_source_has_provenance(self):
        source=blockout.DEFAULT_GEOJSON
        self.assertTrue(source.is_file())
        raw=json.loads(source.read_text(encoding="utf-8"))
        props=raw["properties"]
        self.assertEqual(props["license"],"Open Database License (ODbL) 1.0")
        self.assertEqual(props["source"],"© OpenStreetMap contributors")
        self.assertEqual(len(props["osm_way_ids"]),90)
        self.assertEqual(len(set(props["osm_way_ids"])),90)
        self.assertEqual(len(props["snapshot_sha256"]),64)
        pts,sha=blockout.import_geojson(source)
        self.assertEqual(len(sha),64)
        self.assertTrue(6540*.97<=blockout.perimeter(pts)<=6540*1.03)
        self.assertGreater(len(pts),600)
        with tempfile.TemporaryDirectory() as d:
            subprocess.run([sys.executable,str(SCRIPT),"--out",d],check=True,
                           capture_output=True,text=True,encoding="utf-8")
            route=json.loads((Path(d)/"route.json").read_text(encoding="utf-8"))
            self.assertEqual(route["source"],props["source"])
            self.assertEqual(route["source_sha256"],sha)
            self.assertEqual(route["osm_way_ids"],props["osm_way_ids"])
            self.assertNotIn("schematic",route["source"])

    def test_output_reproducible(self):
        with tempfile.TemporaryDirectory() as d:
            for _ in range(2):
                subprocess.run([sys.executable,str(SCRIPT),"--out",d,"--schematic"],
                               check=True,capture_output=True,text=True,encoding="utf-8")
                route = json.loads((Path(d)/"route.json").read_text(encoding="utf-8"))
                road = json.loads((Path(d)/"road.json").read_text(encoding="utf-8"))
                self.assertEqual(route,self.route)
                self.assertEqual(road,self.model)


if __name__=="__main__":
    unittest.main()
