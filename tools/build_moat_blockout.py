#!/usr/bin/env python3
"""Generate the Chiang Mai moat prototype from OSM-derived or schematic data.

Default: checked-in OSM outer-road GeoJSON with ODbL attribution.
Use --schematic for the original rounded rectangle, or --geojson for a
separately verified closed LineString. Python standard library only.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

FORMAT = "cmr-static-v1"
TRACK_ID = "chiangmai-moat"
DEFAULT_GEOJSON = Path(__file__).resolve().parents[1] / "assets/tracks/chiangmai-moat/source-osm.geojson"
DEFAULT_WATER = Path(__file__).resolve().parents[1] / "assets/tracks/chiangmai-moat/source-water-osm.geojson"
DEFAULT_GATES = Path(__file__).resolve().parents[1] / "assets/tracks/chiangmai-moat/source-gates-osm.geojson"
DEFAULT_BUILDINGS = Path(__file__).resolve().parents[1] / "assets/tracks/chiangmai-moat/source-buildings-osm.geojson"
DEFAULT_LANDMARKS = Path(__file__).resolve().parents[1] / "assets/tracks/chiangmai-moat/source-wat-chedi-luang-osm.geojson"
# Coordinate system: X east, Z south, Y up; 1 unit = 1 metre.
# A conceptual 1.66 km x 1.656 km loop based on the Chiang Mai old city scale.
HALF_WIDTH = 830.0
HALF_HEIGHT = 828.0
CORNER_RADIUS = 30.0
SAMPLE_STEP = 10.0
ROAD_HALF_WIDTH = 7.0
# Give players time to brake before 38–55 degree OSM bends.
SHARP_TURN_WARNING_LEAD_M = 80.0
MOAT_INNER_OFFSET = 20.0
MOAT_OUTER_OFFSET = 40.0
CENTER_LAT = 18.7883
CENTER_LON = 98.9855

def build_points(step=SAMPLE_STEP):
    """Generate with ordered, nonduplicated vertices and a closing seam."""
    r = CORNER_RADIUS
    w,h = HALF_WIDTH, HALF_HEIGHT
    segments = [
        ("line", (w,0), (w,h-r)),
        ("arc", (w-r,h-r), (0,math.pi/2)),
        ("line", (w-r,h), (-w+r,h)),
        ("arc", (-w+r,h-r), (math.pi/2,math.pi)),
        ("line", (-w,h-r), (-w,-h+r)),
        ("arc", (-w+r,-h+r), (math.pi,3*math.pi/2)),
        ("line", (-w+r,-h), (w-r,-h)),
        ("arc", (w-r,-h+r), (3*math.pi/2,2*math.pi)),
        ("line", (w,-h+r), (w,0)),
    ]
    pts = []
    for kind,a,b in segments:
        if kind == "line":
            x0,z0 = a; x1,z1 = b
            length = math.hypot(x1-x0,z1-z0)
            count = max(1,math.ceil(length/step))
            pts.extend((x0+(x1-x0)*j/count,z0+(z1-z0)*j/count)
                       for j in range(count))
        else:
            cx,cz = a; t0,t1 = b
            count = max(2,math.ceil((t1-t0)*r/step))
            pts.extend((cx+r*math.cos(t0+(t1-t0)*j/count),
                        cz+r*math.sin(t0+(t1-t0)*j/count))
                       for j in range(count))
    if len(pts) < 4 or math.dist(pts[0],pts[-1]) <= 1e-6:
        raise ValueError("invalid generated path")
    return pts

def resample_closed(points, step=SAMPLE_STEP):
    """Resample an already-closed path at near-uniform arc length."""
    total=perimeter(points)
    count=max(4,round(total/step))
    lengths=[math.dist(points[i],points[(i+1)%len(points)])
             for i in range(len(points))]
    output=[]
    segment=0
    start=0.0
    for j in range(count):
        distance=j*total/count
        while segment+1<len(lengths) and start+lengths[segment]<distance:
            start+=lengths[segment]
            segment+=1
        a=points[segment]
        b=points[(segment+1)%len(points)]
        t=(distance-start)/lengths[segment] if lengths[segment]>1e-12 else 0
        output.append((a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t))
    return output


def _segments_intersect(a, b, c, d):
    """True for crossings and nonadjacent endpoint touches."""
    def orient(p, q, r):
        return (q[0]-p[0])*(r[1]-p[1]) - (q[1]-p[1])*(r[0]-p[0])
    def within(p, q, r):
        return (min(p[0],q[0])-1e-7 <= r[0] <= max(p[0],q[0])+1e-7 and
                min(p[1],q[1])-1e-7 <= r[1] <= max(p[1],q[1])+1e-7)
    u=orient(a,b,c); v=orient(a,b,d)
    w=orient(c,d,a); x=orient(c,d,b)
    if ((u>1e-7 and v< -1e-7) or (u< -1e-7 and v>1e-7)) and (
        (w>1e-7 and x< -1e-7) or (w< -1e-7 and x>1e-7)):
        return True
    return ((abs(u)<=1e-7 and within(a,b,c)) or
            (abs(v)<=1e-7 and within(a,b,d)) or
            (abs(w)<=1e-7 and within(c,d,a)) or
            (abs(x)<=1e-7 and within(c,d,b)))


def validate_simple_loop(points):
    """Reject disconnected, self-crossing, degenerate or implausible loops.

    Imported geometry must be a *single simple* ring, not a line accidentally
    closed by a straight segment. O(n^2) runs offline only.
    """
    n=len(points)
    if not 4<=n<=3000:
        raise ValueError("route needs 4..3000 distinct vertices")
    for i,p in enumerate(points):
        if not all(math.isfinite(v) for v in p):
            raise ValueError("non-finite route coordinate")
        if abs(p[0])>3000 or abs(p[1])>3000:
            raise ValueError("route lies outside Chiang Mai old-city vicinity")
        if math.dist(p,points[(i+1)%n])<0.05:
            raise ValueError("route contains a near-zero segment")
    for i in range(n):
        a,b=points[i],points[(i+1)%n]
        for j in range(i+1,n):
            if j==i+1 or (i==0 and j==n-1):
                continue
            c,d=points[j],points[(j+1)%n]
            if (max(a[0],b[0])<min(c[0],d[0])-1e-7 or
                max(c[0],d[0])<min(a[0],b[0])-1e-7 or
                max(a[1],b[1])<min(c[1],d[1])-1e-7 or
                max(c[1],d[1])<min(a[1],b[1])-1e-7):
                continue
            if _segments_intersect(a,b,c,d):
                raise ValueError("route has a self-intersection between "
                                 f"segments {i} and {j}")


def import_geojson(path):
    """Load one closed GeoJSON LineString [lon, lat] as a clockwise loop.

    MultiLineString and way collections require proper OSM topology stitching
    upstream, and are deliberately rejected instead of guessed.
    """
    source=Path(path)
    data=json.loads(source.read_text(encoding="utf-8"))
    if data.get("type")=="FeatureCollection":
        features=data.get("features",[])
        if len(features)!=1:
            raise ValueError("expected a single stitched LineString feature")
        data=features[0]
    if data.get("type")=="Feature":
        data=data.get("geometry") or {}
    if data.get("type")!="LineString":
        raise ValueError("expected a closed GeoJSON LineString")
    coords=data.get("coordinates",[])
    if not isinstance(coords,list) or len(coords)<5:
        raise ValueError("GeoJSON must explicitly close a LineString of >=4 points")
    if len(coords)>3001:
        raise ValueError("too many GeoJSON vertices; simplify upstream")
    earth_radius=6371008.8
    lat0=math.radians(CENTER_LAT)
    points=[]
    for point in coords:
        if (not isinstance(point,(list,tuple)) or len(point)<2 or
            any(isinstance(c,bool) or not isinstance(c,(int,float))
                or not math.isfinite(c) for c in point[:2])):
            raise ValueError("invalid GeoJSON lon/lat")
        lon,lat=point[:2]
        if not (-180<=lon<=180 and -90<=lat<=90):
            raise ValueError("GeoJSON longitude/latitude out of range")
        x=earth_radius*math.cos(lat0)*math.radians(lon-CENTER_LON)
        z=-earth_radius*math.radians(lat-CENTER_LAT)
        if not points or math.dist((x,z),points[-1])>1e-5:
            points.append((x,z))
    # GeoJSON closed LineString means first and last positions are identical.
    # A 10-20 m gap previously got silently bridged by a fictitious road.
    if math.dist(points[0],points[-1])>0.1:
        raise ValueError("GeoJSON LineString is not explicitly closed (0.1 m tolerance)")
    points.pop()
    validate_simple_loop(points)
    area=sum(points[i][0]*points[(i+1)%len(points)][1]-
             points[(i+1)%len(points)][0]*points[i][1]
             for i in range(len(points)))
    if abs(area)<1:
        raise ValueError("collapsed or degenerate route")
    if area<0:
        points.reverse()  # clockwise with +Z toward south

    # Anchor near the actual Tha Phae/east-gate reference, not the
    # easternmost vertex (which can be a sharp corner of a rotated loop).
    start=min(range(len(points)),key=lambda i:
              (points[i][0]-HALF_WIDTH)**2 + points[i][1]**2)
    points=points[start:]+points[:start]
    source_length=perimeter(points)
    points=resample_closed(points)
    validate_simple_loop(points)
    if source_length-perimeter(points)>source_length*0.015:
        raise ValueError("resampling shortened route by >1.5%; inspect sharp corners")
    if not (6540*0.97<=perimeter(points)<=6540*1.03):
        raise ValueError("imported route falls outside 6.54 km +/- 3%; verify source")
    sha=hashlib.sha256(source.read_bytes()).hexdigest()
    return points,sha


def perimeter(points):
    return sum(math.dist(p,points[(i+1)%len(points)]) for i,p in enumerate(points))

def normal(points,i):
    """Right-hand (inward) unit normal to a clockwise track."""
    last=points[(i-1)%len(points)]; nxt=points[(i+1)%len(points)]
    dx=nxt[0]-last[0]; dz=nxt[1]-last[1]
    d=math.hypot(dx,dz)
    if d < 1e-8:
        raise ValueError("zero length centreline tangent")
    return -dz/d,dx/d

def strip_mesh(points, left_offset, right_offset, elevation, name):
    """Build a triangle strip with ~one mesh and two triangles per section."""
    positions=[]
    indices=[]
    for i,(x,z) in enumerate(points):
        nx,nz=normal(points,i)
        for offset in (left_offset,right_offset):
            positions.extend((round(x+nx*offset,4),elevation,round(z+nz*offset,4)))
    n=len(points)
    for i in range(n):
        a=2*i;b=2*((i+1)%n)
        # Winding must point UP (+Y): r50's FrontSide materials would
        # otherwise cull the entire asphalt and water surface from above.
        indices.extend((a,a+1,b,a+1,b+1,b))
    return {"name":name,"material":0,"positions":positions,"indices":indices}

def lane_marking_mesh(points):
    """Merged, non-colliding game-only dashed centreline (not an OSM tag).

    Each stripe occupies only the middle of one sampled road segment, so
    tight turns do not create long diagonal polygons cutting across bends.
    Keep markings just above the asphalt to avoid depth fighting in r50.
    """
    positions=[]
    indices=[]
    for i in range(0,len(points),2):
        a=points[i]
        b=points[(i+1)%len(points)]
        dx=b[0]-a[0]
        dz=b[1]-a[1]
        length=math.hypot(dx,dz)
        if length<0.2:
            continue
        nx,nz=-dz/length,dx/length
        # 5m dash or half a segment, whichever is smaller.
        span=min(5.0,length*0.5)
        midx=(a[0]+b[0])/2
        midz=(a[1]+b[1])/2
        sx=midx-dx/length*span/2
        sz=midz-dz/length*span/2
        ex=midx+dx/length*span/2
        ez=midz+dz/length*span/2
        start=len(positions)//3
        for x,z,offset in ((sx,sz,-0.12),(sx,sz,0.12),
                           (ex,ez,-0.12),(ex,ez,0.12)):
            positions.extend((round(x+nx*offset,4),0.103,
                              round(z+nz*offset,4)))
        # Match upward (+Y) winding of strip_mesh.
        indices.extend((start,start+1,start+2,
                        start+1,start+3,start+2))
    return {"name":"game-dashed-centreline",
            "material":0,"positions":positions,"indices":indices}


def load_water_polygons(path):
    """Read closed OSM water polygons and return X/Z metre rings."""
    data=json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("type")!="FeatureCollection" or not data.get("features"):
        raise ValueError("expected nonempty OSM water FeatureCollection")
    props=data.get("properties",{})
    if props.get("source")!="© OpenStreetMap contributors" or "ODbL" not in props.get("license",""):
        raise ValueError("water data missing verified OSM/ODbL provenance")
    polygons=[]
    for feature in data["features"]:
        geometry=feature.get("geometry") or {}
        if geometry.get("type")!="Polygon" or len(geometry.get("coordinates",[]))!=1:
            raise ValueError("water polygon must have one exterior ring without holes")
        coords=geometry["coordinates"][0]
        if len(coords)<4 or coords[0]!=coords[-1]:
            raise ValueError("water polygon must be explicitly closed")
        points=[]
        for lon,lat in coords[:-1]:
            if not (math.isfinite(lon) and math.isfinite(lat)):
                raise ValueError("invalid OSM water coordinate")
            x=6371008.8*math.cos(math.radians(CENTER_LAT))*math.radians(lon-CENTER_LON)
            z=-6371008.8*math.radians(lat-CENTER_LAT)
            if abs(x)>3000 or abs(z)>3000:
                raise ValueError("water polygon outside old city vicinity")
            if not points or math.dist(points[-1],(x,z))>0.02:
                points.append((x,z))
        if len(points)<3:
            raise ValueError("degenerate OSM water polygon")
        polygons.append(points)
    return polygons,props


def project_lonlat(lon,lat):
    if (isinstance(lon,bool) or isinstance(lat,bool) or
        not isinstance(lon,(int,float)) or not isinstance(lat,(int,float)) or
        not math.isfinite(lon) or not math.isfinite(lat)):
        raise ValueError("invalid OSM coordinate")
    return (6371008.8*math.cos(math.radians(CENTER_LAT))*math.radians(lon-CENTER_LON),
            -6371008.8*math.radians(lat-CENTER_LAT))


def load_historic_gates(path):
    """Validate the four historic OSM nodes, not unrelated barrier=gate POIs."""
    data=json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("type")!="FeatureCollection":
        raise ValueError("expected gate FeatureCollection")
    props=data.get("properties",{})
    if props.get("source")!="© OpenStreetMap contributors" or "ODbL" not in props.get("license",""):
        raise ValueError("historic gate data missing OSM/ODbL provenance")
    expected=("tha-phae","chiang-mai","suan-dok","chang-phueak")
    features=data.get("features",[])
    if len(features)!=4:
        raise ValueError("expected exactly four historic city gates")
    gates=[]
    seen=set()
    for feature,gate_id in zip(features,expected):
        item=feature.get("properties",{})
        geo=feature.get("geometry",{})
        if item.get("id")!=gate_id or gate_id in seen:
            raise ValueError("historic gate order/identity mismatch")
        if geo.get("type")!="Point" or len(geo.get("coordinates",[]))!=2:
            raise ValueError("historic gate must be a Point")
        x,z=project_lonlat(*geo["coordinates"])
        if abs(x)>3000 or abs(z)>3000:
            raise ValueError("historic gate outside old city")
        node_id=item.get("osm_node_id")
        if not str(node_id).isdigit():
            raise ValueError("historic gate missing OSM node ID")
        gates.append({"id":gate_id,"name":item["name"],
                      "osm_node_id":str(node_id),"lon":geo["coordinates"][0],
                      "lat":geo["coordinates"][1],"x":x,"z":z})
        seen.add(gate_id)
    return gates,props


def load_roadside_buildings(path):
    """Validate ODbL building footprints and their game-only height estimates."""
    data=json.loads(Path(path).read_text(encoding="utf-8"))
    props=data.get("properties",{})
    if (data.get("type")!="FeatureCollection" or
        props.get("source")!="© OpenStreetMap contributors" or
        "ODbL" not in props.get("license","")):
        raise ValueError("roadside buildings missing OSM/ODbL provenance")
    features=data.get("features",[])
    if not features or len(features)>900 or len(features)!=props.get("building_count"):
        raise ValueError("roadside building count invalid")
    result=[]
    seen=set()
    for feature in features:
        tags=feature.get("properties",{})
        way_id=str(tags.get("osm_way_id",""))
        if not way_id.isdigit() or way_id in seen:
            raise ValueError("invalid or duplicate building way ID")
        seen.add(way_id)
        height=tags.get("height_m")
        if (isinstance(height,bool) or not isinstance(height,(float,int)) or
            not math.isfinite(height) or not 2<=height<=30):
            raise ValueError("invalid building height")
        if tags.get("height_source") not in (
            "osm:height","osm:building:levels","estimated:game-blockout"
        ):
            raise ValueError("building height provenance missing")
        geometry=feature.get("geometry") or {}
        rings=geometry.get("coordinates",[])
        if geometry.get("type")!="Polygon" or len(rings)!=1:
            raise ValueError("building must be a simple Polygon without holes")
        coords=rings[0]
        if not 4<=len(coords)<=36 or coords[0]!=coords[-1]:
            raise ValueError("building footprint must be explicitly closed")
        points=[]
        for lon,lat in coords[:-1]:
            x,z=project_lonlat(lon,lat)
            if not math.isfinite(x) or not math.isfinite(z) or abs(x)>3000 or abs(z)>3000:
                raise ValueError("building outside Chiang Mai old-city area")
            points.append((x,z))
        # Validate the polygon before it reaches the runtime mesh.
        triangulate_water_polygon(points)
        result.append((points,float(height)))
    return result,props


def roadside_building_meshes(buildings, route_points=None, chunk_m=350):
    """Bake facades/roofs into small meshes so r50 can frustum-cull them.

    The original two meshes had bounding spheres spanning the entire 6.5 km
    ring, forcing all 815 buildings through WebGL on every visible frame.
    Buckets follow road arc length rather than world X/Z so a corner remains
    in a compact, predictable section. The no-route form remains useful for
    standalone geometry tests.
    """
    if route_points is not None:
        if not route_points or not 50 <= chunk_m <= 1000:
            raise ValueError("invalid building chunk route or length")
        cumulative=[0.0]
        for i in range(len(route_points)-1):
            cumulative.append(cumulative[-1]+math.dist(route_points[i],route_points[i+1]))
        groups={}
        for footprint,height in buildings:
            cx=sum(p[0] for p in footprint)/len(footprint)
            cz=sum(p[1] for p in footprint)/len(footprint)
            index=nearest_road_index(route_points,cx,cz)[0]
            bucket=int(cumulative[index]//chunk_m)
            groups.setdefault(bucket,[]).append((footprint,height))
        meshes=[]
        for bucket in sorted(groups):
            facades,roofs=roadside_building_meshes(groups[bucket])
            facades["name"]=f"osm-roadside-facades-{bucket:02d}"
            roofs["name"]=f"osm-roadside-roofs-{bucket:02d}"
            # r50dev computes boundingSphere.radius FROM LOCAL ORIGIN,
            # not from the mesh bounding-box centre. Without rebasing,
            # each global-coordinate chunk still has a ~1 km sphere and
            # defeats frustum culling even though it has fewer triangles.
            for mesh in (facades,roofs):
                p=mesh["positions"]
                cx=round((min(p[::3])+max(p[::3]))/2,4)
                cz=round((min(p[2::3])+max(p[2::3]))/2,4)
                mesh["offset"]=[cx,0,cz]
                for j in range(0,len(p),3):
                    p[j]=round(p[j]-cx,4)
                    p[j+2]=round(p[j+2]-cz,4)
            meshes.extend((facades,roofs))
        return meshes
    wall_pos=[];wall_idx=[]
    roof_pos=[];roof_idx=[]
    for footprint,height in buildings:
        poly,triangles=triangulate_water_polygon(footprint)
        roof_start=len(roof_pos)//3
        for x,z in poly:
            roof_pos.extend((round(x,4),round(height+0.04,4),round(z,4)))
        roof_idx.extend(roof_start+i for i in triangles)
        for i,a in enumerate(poly):
            b=poly[(i+1)%len(poly)]
            base=len(wall_pos)//3
            for x,y,z in ((a[0],0,a[1]),(b[0],0,b[1]),
                          (b[0],height,b[1]),(a[0],height,a[1])):
                wall_pos.extend((round(x,4),round(y,4),round(z,4)))
            # CCW X/Z polygon: right side is exterior, so reverse the
            # inward-facing (a,b,b-top) winding for outward normals.
            wall_idx.extend((base,base+2,base+1,
                             base,base+3,base+2))
    return (
        {"name":"osm-roadside-facades","material":5,
         "positions":wall_pos,"indices":wall_idx},
        {"name":"osm-roadside-roofs","material":6,
         "positions":roof_pos,"indices":roof_idx}
    )



def load_wat_chedi_luang(path):
    """Validate ODbL footprints for the compound, stupa, viharn and shrine."""
    data=json.loads(Path(path).read_text(encoding="utf-8"))
    props=data.get("properties",{})
    if (data.get("type")!="FeatureCollection" or
        props.get("source")!="© OpenStreetMap contributors" or
        "ODbL" not in props.get("license","")):
        raise ValueError("Wat Chedi Luang landmarks missing OSM/ODbL provenance")
    expected={
        "compound":"243018795",
        "stupa":"93413945",
        "viharn":"93413944",
        "city-pillar-shrine":"441418807"
    }
    features=data.get("features",[])
    if len(features)!=len(expected) or props.get("feature_count")!=len(expected):
        raise ValueError("Wat Chedi Luang landmark feature count invalid")
    result={}
    for feature in features:
        item=feature.get("properties",{})
        role=item.get("role")
        way_id=str(item.get("osm_way_id",""))
        if role not in expected or expected[role]!=way_id or role in result:
            raise ValueError("Wat Chedi Luang OSM way identity mismatch")
        geometry=feature.get("geometry") or {}
        rings=geometry.get("coordinates",[])
        if geometry.get("type")!="Polygon" or len(rings)!=1:
            raise ValueError("Wat Chedi Luang footprint must be a simple Polygon")
        coords=rings[0]
        if not 5<=len(coords)<=40 or coords[0]!=coords[-1]:
            raise ValueError("Wat Chedi Luang footprint must be explicitly closed")
        points=[]
        for lon,lat in coords[:-1]:
            x,z=project_lonlat(lon,lat)
            if not math.isfinite(x) or not math.isfinite(z) or abs(x)>500 or abs(z)>500:
                raise ValueError("Wat Chedi Luang footprint outside landmark area")
            points.append((x,z))
        triangulate_water_polygon(points)
        result[role]=(points,item)
    if set(result)!=set(expected):
        raise ValueError("Wat Chedi Luang landmark roles incomplete")
    compound=result["compound"][0]
    def inside(point,poly):
        x,z=point
        hit=False
        for i,a in enumerate(poly):
            b=poly[(i+1)%len(poly)]
            if ((a[1]>z)!=(b[1]>z)) and (
                x<(b[0]-a[0])*(z-a[1])/(b[1]-a[1])+a[0]):
                hit=not hit
        return hit
    for role,(poly,_) in result.items():
        if role=="compound":
            continue
        center=(sum(x for x,_ in poly)/len(poly),
                sum(z for _,z in poly)/len(poly))
        if not inside(center,compound):
            raise ValueError("Wat Chedi Luang feature falls outside compound: "+role)
    return result,props


def _append_oriented_quad(positions,indices,vertices,outward):
    """Append a double-triangle quad with winding facing the supplied normal."""
    vertices=list(vertices)
    a,b,c=vertices[:3]
    ux,uy,uz=b[0]-a[0],b[1]-a[1],b[2]-a[2]
    vx,vy,vz=c[0]-a[0],c[1]-a[1],c[2]-a[2]
    nx=uy*vz-uz*vy
    ny=uz*vx-ux*vz
    nz=ux*vy-uy*vx
    if nx*outward[0]+ny*outward[1]+nz*outward[2]<0:
        vertices=[vertices[0],vertices[3],vertices[2],vertices[1]]
    base=len(positions)//3
    for x,y,z in vertices:
        positions.extend((round(x,4),round(y,4),round(z,4)))
    indices.extend((base,base+1,base+2,base,base+2,base+3))


def _append_oriented_triangle(positions,indices,vertices,outward):
    vertices=list(vertices)
    a,b,c=vertices
    ux,uy,uz=b[0]-a[0],b[1]-a[1],b[2]-a[2]
    vx,vy,vz=c[0]-a[0],c[1]-a[1],c[2]-a[2]
    nx=uy*vz-uz*vy
    ny=uz*vx-ux*vz
    nz=ux*vy-uy*vx
    if nx*outward[0]+ny*outward[1]+nz*outward[2]<0:
        vertices=[a,c,b]
    base=len(positions)//3
    for x,y,z in vertices:
        positions.extend((round(x,4),round(y,4),round(z,4)))
    indices.extend((base,base+1,base+2))


def _append_box(positions,indices,cx,cy,cz,sx,sy,sz):
    hx=sx/2;hy=sy/2;hz=sz/2
    faces=(
        ([ (cx-hx,cy-hy,cz-hz),(cx+hx,cy-hy,cz-hz),
           (cx+hx,cy+hy,cz-hz),(cx-hx,cy+hy,cz-hz)],(0,0,-1)),
        ([ (cx+hx,cy-hy,cz+hz),(cx-hx,cy-hy,cz+hz),
           (cx-hx,cy+hy,cz+hz),(cx+hx,cy+hy,cz+hz)],(0,0,1)),
        ([ (cx-hx,cy-hy,cz+hz),(cx-hx,cy-hy,cz-hz),
           (cx-hx,cy+hy,cz-hz),(cx-hx,cy+hy,cz+hz)],(-1,0,0)),
        ([ (cx+hx,cy-hy,cz-hz),(cx+hx,cy-hy,cz+hz),
           (cx+hx,cy+hy,cz+hz),(cx+hx,cy+hy,cz-hz)],(1,0,0)),
        ([ (cx-hx,cy+hy,cz-hz),(cx+hx,cy+hy,cz-hz),
           (cx+hx,cy+hy,cz+hz),(cx-hx,cy+hy,cz+hz)],(0,1,0)),
        ([ (cx-hx,cy-hy,cz+hz),(cx+hx,cy-hy,cz+hz),
           (cx+hx,cy-hy,cz-hz),(cx-hx,cy-hy,cz-hz)],(0,-1,0))
    )
    for vertices,outward in faces:
        _append_oriented_quad(positions,indices,vertices,outward)


def _append_frustum(positions,indices,cx,cz,hx,hz,y0,y1,scale0,scale1):
    """Append one square/rectangular stepped stupa tier."""
    bottom=[
        (cx-hx*scale0,y0,cz-hz*scale0),
        (cx+hx*scale0,y0,cz-hz*scale0),
        (cx+hx*scale0,y0,cz+hz*scale0),
        (cx-hx*scale0,y0,cz+hz*scale0)
    ]
    top=[
        (cx-hx*scale1,y1,cz-hz*scale1),
        (cx+hx*scale1,y1,cz-hz*scale1),
        (cx+hx*scale1,y1,cz+hz*scale1),
        (cx-hx*scale1,y1,cz+hz*scale1)
    ]
    for i in range(4):
        j=(i+1)%4
        mx=(bottom[i][0]+bottom[j][0]+top[i][0]+top[j][0])/4-cx
        mz=(bottom[i][2]+bottom[j][2]+top[i][2]+top[j][2])/4-cz
        _append_oriented_quad(positions,indices,
            [bottom[i],bottom[j],top[j],top[i]],(mx,0,mz))
    _append_oriented_quad(positions,indices,top,(0,1,0))


def _append_polygon_walls(positions,indices,polygon,height):
    cx=sum(x for x,_ in polygon)/len(polygon)
    cz=sum(z for _,z in polygon)/len(polygon)
    for i,a in enumerate(polygon):
        b=polygon[(i+1)%len(polygon)]
        midx=(a[0]+b[0])/2
        midz=(a[1]+b[1])/2
        _append_oriented_quad(positions,indices,
            [(a[0],0,a[1]),(b[0],0,b[1]),
             (b[0],height,b[1]),(a[0],height,a[1])],
            (midx-cx,0,midz-cz))


def _append_gable_roof(positions,indices,cx,cz,hx,hz,eave,ridge):
    """Two sloped roof planes and gable ends for a low-poly Lanna viharn."""
    x0=cx-hx-2.5;x1=cx+hx+2.5
    z0=cz-hz-2.5;z1=cz+hz+2.5
    _append_oriented_quad(positions,indices,
        [(x0,eave,z0),(x1,eave,z0),(x1,ridge,cz),(x0,ridge,cz)],
        (0,1,-1))
    _append_oriented_quad(positions,indices,
        [(x1,eave,z1),(x0,eave,z1),(x0,ridge,cz),(x1,ridge,cz)],
        (0,1,1))
    _append_oriented_triangle(positions,indices,
        [(x0,eave,z0),(x0,eave,z1),(x0,ridge,cz)],(-1,0,0))
    _append_oriented_triangle(positions,indices,
        [(x1,eave,z1),(x1,eave,z0),(x1,ridge,cz)],(1,0,0))
    _append_box(positions,indices,cx,ridge+0.18,cz,2*hx+5,0.45,0.7)


def wat_chedi_luang_meshes(landmarks,material_start):
    """Build low-poly landmark meshes from OSM footprints, not OSM 3D models."""
    stupa=landmarks["stupa"][0]
    sx=[p[0] for p in stupa];sz=[p[1] for p in stupa]
    cx=(min(sx)+max(sx))/2;cz=(min(sz)+max(sz))/2
    hx=(max(sx)-min(sx))/2;hz=(max(sz)-min(sz))/2

    brick_pos=[];brick_idx=[]
    tiers=(
        (0,2.5,1.00,0.98),(2.5,5,0.98,0.90),
        (5,9,0.90,0.78),(9,13,0.78,0.65),
        (13,17.5,0.65,0.53),(17.5,22,0.53,0.42),
        (22,26,0.42,0.32),(26,30,0.32,0.23),
        (30,34,0.23,0.15),(34,37,0.15,0.08)
    )
    for y0,y1,s0,s1 in tiers:
        _append_frustum(brick_pos,brick_idx,cx,cz,hx,hz,y0,y1,s0,s1)
    # A deliberately truncated crown: the present-day chedi is a ruin, not
    # an intact imaginary golden spire.
    _append_box(brick_pos,brick_idx,cx,37.7,cz,hx*0.15,1.4,hz*0.15)

    accent_pos=[];accent_idx=[]
    # Four simple buttress blocks at the cardinal faces make the large square
    # base readable at racing distance without claiming exact sculpture detail.
    for sign in (-1,1):
        _append_box(accent_pos,accent_idx,cx+sign*hx*0.79,3.2,cz,
                    7.0,4.8,9.0)
        _append_box(accent_pos,accent_idx,cx,3.2,cz+sign*hz*0.79,
                    9.0,4.8,7.0)

    viharn=landmarks["viharn"][0]
    vx=[p[0] for p in viharn];vz=[p[1] for p in viharn]
    vcx=(min(vx)+max(vx))/2;vcz=(min(vz)+max(vz))/2
    vhx=(max(vx)-min(vx))/2;vhz=(max(vz)-min(vz))/2
    shrine=landmarks["city-pillar-shrine"][0]
    qx=[p[0] for p in shrine];qz=[p[1] for p in shrine]
    qcx=(min(qx)+max(qx))/2;qcz=(min(qz)+max(qz))/2
    qhx=(max(qx)-min(qx))/2;qhz=(max(qz)-min(qz))/2

    wall_pos=[];wall_idx=[]
    _append_polygon_walls(wall_pos,wall_idx,viharn,7.5)
    _append_polygon_walls(wall_pos,wall_idx,shrine,4.5)

    roof_pos=[];roof_idx=[]
    _append_gable_roof(roof_pos,roof_idx,vcx,vcz,vhx*1.02,vhz*1.02,8.0,14.2)
    _append_gable_roof(roof_pos,roof_idx,vcx,vcz,vhx*0.72,vhz*0.72,10.8,16.4)
    # A compact hipped roof marks the city-pillar shrine without adding a
    # fourth large landmark or a high draw-call count.
    base=[
        (qcx-qhx-1,4.5,qcz-qhz-1),(qcx+qhx+1,4.5,qcz-qhz-1),
        (qcx+qhx+1,4.5,qcz+qhz+1),(qcx-qhx-1,4.5,qcz+qhz+1)
    ]
    apex=(qcx,9.7,qcz)
    for i in range(4):
        j=(i+1)%4
        mx=(base[i][0]+base[j][0])/2-qcx
        mz=(base[i][2]+base[j][2])/2-qcz
        _append_oriented_triangle(roof_pos,roof_idx,
            [base[i],base[j],apex],(mx,1.0,mz))

    return [
        {"name":"wat-chedi-luang-stupa","material":material_start,
         "positions":brick_pos,"indices":brick_idx},
        {"name":"wat-chedi-luang-stupa-buttresses","material":material_start+1,
         "positions":accent_pos,"indices":accent_idx},
        {"name":"wat-chedi-luang-viharn-and-shrine","material":material_start+2,
         "positions":wall_pos,"indices":wall_idx},
        {"name":"wat-chedi-luang-roofs","material":material_start+3,
         "positions":roof_pos,"indices":roof_idx}
    ]


def nearest_road_index(points,x,z):
    """Return nearest resampled centreline vertex and its distance in metres."""
    i=min(range(len(points)),key=lambda j:
          (points[j][0]-x)**2+(points[j][1]-z)**2)
    return i,math.dist(points[i],(x,z))


def align_gates_to_route(points,gates):
    """Re-anchor route at Tha Phae and attach ordered road-side checkpoints."""
    for gate in gates:
        gate["point_index"],gate["distance_to_road_m"]=nearest_road_index(
            points,gate["x"],gate["z"])
        if not (12<gate["distance_to_road_m"]<150):
            raise ValueError("historic gate unexpectedly overlaps/far from race road: "+
                             gate["name"])
    offset=gates[0]["point_index"]
    points=points[offset:]+points[:offset]
    for gate in gates:
        gate["point_index"]=(gate["point_index"]-offset)%len(points)
    if not (gates[0]["point_index"]==0 and
            all(gates[i]["point_index"]<gates[i+1]["point_index"]
                for i in range(3))):
        raise ValueError("OSM gates do not follow expected clockwise order")
    return points


def triangulate_water_polygon(points):
    """Ear-clip a simple polygon into upward-facing triangles in X/Z."""
    points=list(points)
    # Remove near-collinear vertices to avoid zero-area triangles.
    changed=True
    while changed and len(points)>3:
        changed=False
        for i in range(len(points)):
            a=points[i-1];b=points[i];c=points[(i+1)%len(points)]
            cross=(b[0]-a[0])*(c[1]-b[1])-(b[1]-a[1])*(c[0]-b[0])
            if abs(cross)<1e-6:
                points.pop(i);changed=True;break
    if len(points)<3:
        raise ValueError("collapsed water polygon")
    area=sum(points[i][0]*points[(i+1)%len(points)][1]-
             points[(i+1)%len(points)][0]*points[i][1]
             for i in range(len(points)))
    if abs(area)<1:
        raise ValueError("zero-area water polygon")
    if area<0:
        points.reverse()  # ear clipping uses positive X/Z signed area
    vertices=list(range(len(points)))
    triangles=[]
    def cross(a,b,c):
        return ((b[0]-a[0])*(c[1]-a[1])-
                (b[1]-a[1])*(c[0]-a[0]))
    while len(vertices)>3:
        found=False
        for k in range(len(vertices)):
            a=vertices[k-1];b=vertices[k];c=vertices[(k+1)%len(vertices)]
            if cross(points[a],points[b],points[c])<=1e-7:
                continue
            # Any other point inside or on this ear invalidates it.
            if any(v not in (a,b,c) and
                   cross(points[a],points[b],points[v])>=-1e-7 and
                   cross(points[b],points[c],points[v])>=-1e-7 and
                   cross(points[c],points[a],points[v])>=-1e-7
                   for v in vertices):
                continue
            triangles.extend((a,c,b))  # reverse CCW for +Y normal
            vertices.pop(k)
            found=True
            break
        if not found:
            raise ValueError("cannot triangulate water polygon; inspect OSM geometry")
    triangles.extend((vertices[0],vertices[2],vertices[1]))
    return points,triangles


def water_mesh(polygons):
    positions=[]
    indices=[]
    for polygon in polygons:
        points,triangles=triangulate_water_polygon(polygon)
        offset=len(positions)//3
        for x,z in points:
            positions.extend((round(x,4),-0.06,round(z,4)))
        indices.extend(offset+i for i in triangles)
    return {"name":"moat-water","material":2,
            "positions":positions,"indices":indices}



def is_water_polygon_end_cap(polygon, i):
    """Conservatively identify straight, short cross-water polygon end edges.

    OSM water polygons are often split at bridges. A short edge nearly
    perpendicular to two much longer, parallel banks is an artificial
    polygon closure, not evidence of a retaining wall across the moat.
    Ambiguous rounded/irregular ends are intentionally left untouched.
    """
    a = polygon[i]
    b = polygon[(i+1) % len(polygon)]
    before = polygon[(i-1) % len(polygon)]
    after = polygon[(i+2) % len(polygon)]
    edge = (b[0]-a[0], b[1]-a[1])
    incoming = (a[0]-before[0], a[1]-before[1])
    outgoing = (after[0]-b[0], after[1]-b[1])
    length = math.hypot(*edge)
    left = math.hypot(*incoming)
    right = math.hypot(*outgoing)
    if not (8 <= length <= 28 and left > 3*length and right > 3*length):
        return False
    # Both banks must run in opposite directions around a cut end.
    # Two same-direction banks instead form a real stepped/notched shoreline:
    # deleting the short connector there would create an artificial gap.
    return (abs(sum(x*y for x,y in zip(edge,incoming))) < 0.16*length*left
            and abs(sum(x*y for x,y in zip(edge,outgoing))) < 0.16*length*right
            and sum(x*y for x,y in zip(incoming,outgoing)) < -0.9*left*right)


def water_bank_meshes(polygons, material_index):
    """Visual-only OSM shoreline retaining-wall blockouts, one mesh per ring.

    OSM maps the shoreline footprint, NOT its elevation or wall material.
    Vertices are rebased to each ring's centre for Three.js r50 frustum
    culling. No collision objects or artificial road bridges are added.
    """
    meshes = []
    for ring_id, polygon in enumerate(polygons):
        cx = (min(x for x, _ in polygon) + max(x for x, _ in polygon)) / 2
        cz = (min(z for _, z in polygon) + max(z for _, z in polygon)) / 2
        positions = []
        indices = []
        for x, z in polygon:
            positions.extend((round(x-cx, 4), -0.45, round(z-cz, 4),
                              round(x-cx, 4), 0.18, round(z-cz, 4)))
        for i in range(len(polygon)):
            if is_water_polygon_end_cap(polygon, i):
                continue  # Do not wall off the water at a mapped polygon split.
            a = 2*i
            b = 2*((i+1) % len(polygon))
            indices.extend((a, b, a+1, a+1, b, b+1))
        meshes.append({
            "name": "osm-moat-bank-%02d" % ring_id,
            "material": material_index,
            "positions": positions,
            "indices": indices,
            "offset": [round(cx, 4), 0, round(cz, 4)]
        })
    return meshes

def cube_into(positions,indices,cx,cy,cz,sx,sy,sz,nx=1,nz=0):
    """Append an oriented cuboid (local X along supplied ground normal).

    Local Z is the orthogonal axis (-nz, nx), preserving face winding.
    """
    start=len(positions)//3
    for x,y,z in (
        (-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),
        (-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)
    ):
        u=x*sx/2
        v=z*sz/2
        positions.extend((round(cx+u*nx-v*nz,4),round(cy+y*sy/2,4),
                          round(cz+u*nz+v*nx,4)))
    for a,b,c,d in ((0,3,2,1),(4,5,6,7),(0,1,5,4),
                    (3,7,6,2),(1,2,6,5),(0,4,7,3)):
        indices.extend((start+a,start+b,start+c,start+a,start+c,start+d))

def gate_mesh(points,checkpoint_indices=None):
    positions=[];indices=[]
    # Orient gate columns and beams perpendicular to each road tangent,
    # including diagonal OSM segments. No axis-aligned approximation.
    indexes=(checkpoint_indices if checkpoint_indices is not None else
             [0,len(points)//4,len(points)//2,3*len(points)//4])
    for i in indexes:
        x,z=points[i]
        nx,nz=normal(points,i)
        for sign in (-1,1):
            cube_into(positions,indices,x+nx*9.2*sign,3.0,
                      z+nz*9.2*sign,1.5,6,1.5,nx,nz)
        cube_into(positions,indices,x,6.8,z,20,1.6,1.5,nx,nz)
    return {"name":"checkpoint-gates","material":3,"positions":positions,"indices":indices}

def historic_gate_mesh(points,gates):
    """A single merged terracotta placeholder mesh for four OSM-located gates.

    Gate locations are mapped OSM facts; the low-poly walls and towers are
    explicitly fictional visual blockouts, not claimed heritage models.
    """
    positions=[];indices=[]
    for gate in gates:
        i=gate["point_index"]
        nx,nz=normal(points,i)
        tx,tz=nz,-nx  # along the city wall, perpendicular to its opening
        x,z=gate["x"],gate["z"]
        # Two towers, lintel and low wall wings. No physics colliders:
        # each OSM point is on the old-city side, away from the race lane.
        for sign in (-1,1):
            cube_into(positions,indices,x+tx*8*sign,4,z+tz*8*sign,
                      5,8,5,tx,tz)
            cube_into(positions,indices,x+tx*18*sign,2.2,z+tz*18*sign,
                      14,4.4,2.2,tx,tz)
        cube_into(positions,indices,x,7,z,13,2.4,3.0,tx,tz)
    return {"name":"historic-gates-blockout","material":4,
            "positions":positions,"indices":indices}



def sharp_turn_candidates(points, threshold_deg=28.0, spacing_m=45.0):
    """Return distinct sharp bends; merge nearby resampling vertices.

    These are game-only visual warnings, not OSM road-sign observations.
    Select the strongest turn in each short cluster, including wraparound.
    """
    n=len(points)
    if n<3:
        return []
    lengths=[math.dist(points[i],points[(i+1)%n]) for i in range(n)]
    if min(lengths)<1e-6:
        raise ValueError("duplicate centreline vertex in turn warning")
    cumulative=[0.0]
    for length in lengths:
        cumulative.append(cumulative[-1]+length)
    candidates=[]
    for i in range(n):
        a,b,c=points[i-1],points[i],points[(i+1)%n]
        ux,uz=b[0]-a[0],b[1]-a[1]
        vx,vz=c[0]-b[0],c[1]-b[1]
        degrees=math.degrees(math.atan2(ux*vz-uz*vx,ux*vx+uz*vz))
        if abs(degrees)>=threshold_deg:
            candidates.append((i,degrees))
    selected=[]
    for i,angle in sorted(candidates,key=lambda item:(-abs(item[1]),item[0])):
        if all(min(abs(cumulative[i]-cumulative[j]),
                   cumulative[-1]-abs(cumulative[i]-cumulative[j]))>=spacing_m
               for j,_ in selected):
            selected.append((i,angle))
    return sorted(selected)


def polygon_clearance(point, polygon):
    """Signed ground-plane clearance to a footprint (negative inside).

    A sign needs space for its full 2.6m board, not just a pole that happens
    to fall outside a moat polygon. This calculation runs only at build time.
    """
    x,z=point
    inside=False
    distance=float("inf")
    for i,(ax,az) in enumerate(polygon):
        bx,bz=polygon[(i+1)%len(polygon)]
        dx,dz=bx-ax,bz-az
        length2=dx*dx+dz*dz
        t=max(0.0,min(1.0,((x-ax)*dx+(z-az)*dz)/length2)) if length2 else 0.0
        distance=min(distance,math.hypot(x-ax-t*dx,z-az-t*dz))
        if (az>z)!=(bz>z) and x<ax+(z-az)*dx/dz:
            inside=not inside
    return -distance if inside else distance


def warning_approach_sightlines(points, sign_index, target, buildings, distances=(30.0,50.0)):
    """Approximate low-board visibility from the incoming driving lane.

    A footprint between the approaching driver and a sign hides a 2.75m
    board when the footprint's modelled height reaches the board top.
    This is a conservative 2D build-time check, not camera/GPU occlusion.
    """
    if not buildings:
        return True
    n=len(points)
    previous=sign_index
    travelled=0.0
    approach=[]
    for distance in distances:
        while travelled<distance:
            i=(previous-1)%n
            travelled+=math.dist(points[i],points[previous])
            previous=i
        approach.append(points[previous])
    for origin in approach:
        for poly,height in buildings:
            if height<2.75:
                continue
            if polygon_clearance(origin,poly)<=0:
                return False
            if any(_segments_intersect(origin,target,poly[j],poly[(j+1)%len(poly)])
                   for j in range(len(poly))):
                return False
    return True


def sharp_turn_warning_meshes(points, water_polygons=None, buildings=None):
    """Merge small amber direction signs before the strongest bends.

    Each board is outside the 14m playable corridor and is deliberately
    non-colliding. Board/arrow dimensions are invented gameplay art.
    """
    turns=sharp_turn_candidates(points)
    if not turns:
        return []
    panels=[];panel_ids=[];arrows=[];arrow_ids=[]
    n=len(points)
    for apex,angle in turns:
        # Give ~2s of advance warning at 0.62m/frame and 60fps; use
        # route arc length rather than a fixed number of vertices
        # (GeoJSON sampling can be uneven).
        i=apex
        travelled=0.0
        while travelled<SHARP_TURN_WARNING_LEAD_M:
            prev=(i-1)%n
            travelled+=math.dist(points[prev],points[i])
            i=prev
        x,z=points[i]
        nx,nz=normal(points,i)
        tx,tz=nz,-nx
        # The OSM water polygons can extend right up to a sharp corner.
        # Placing every sign on the bend side previously put one warning
        # pole IN the moat. Try the preferred side, then the opposite side;
        # omit a warning rather than place it in water or a mapped building.
        # A clear pole is not enough: check sightlines from 30m and 50m
        # upstream so a roadside building cannot hide the warning board.
        side=1 if angle>0 else -1
        footprints=list(water_polygons or ())
        if buildings:
            footprints.extend(poly for poly,_ in buildings)
        for candidate in (side,-side):
            cx=x+nx*candidate*10.4
            cz=z+nz*candidate*10.4
            if (all(polygon_clearance((cx,cz),poly)>=1.6
                    for poly in footprints) and
                warning_approach_sightlines(points,i,(cx,cz),buildings)):
                break
        else:
            continue
        cube_into(panels,panel_ids,cx,1.15,cz,0.16,2.3,0.16,nx,nz)
        cube_into(panels,panel_ids,cx,2.75,cz,2.6,1.5,0.16,nx,nz)
        # Dark arrow on the face seen by approaching drivers. Both faces
        # render so this remains legible with the legacy r50 renderer.
        def vertex(local_x,y):
            arrows.extend((round(cx+nx*local_x-tx*0.095,4),
                           round(y,4),
                           round(cz+nz*local_x-tz*0.095,4)))
        start=len(arrows)//3
        for px,py in ((-0.65,2.65),(0.65,2.65),
                      (0.65,2.88),(-0.65,2.88),
                      (side*1.03,2.765),(side*0.47,2.35),
                      (side*0.47,3.18)):
            vertex(px,py)
        arrow_ids.extend((start,start+1,start+2,start,start+2,start+3,
                          start+4,start+5,start+6))
    if not panels:
        return []  # no empty r50 meshes when all locations are obstructed
    return [
        {"name":"game-sharp-turn-signs","material":0,
         "positions":panels,"indices":panel_ids},
        {"name":"game-sharp-turn-arrows","material":0,
         "positions":arrows,"indices":arrow_ids}
    ]


def model(points,water_polygons=None,gates=None,buildings=None,landmarks=None):
    road=strip_mesh(points,-ROAD_HALF_WIDTH,ROAD_HALF_WIDTH,0.08,"race-asphalt")
    road["material"]=0
    curb_a=strip_mesh(points,-ROAD_HALF_WIDTH-1.6,-ROAD_HALF_WIDTH,0.1,"outer-shoulder")
    curb_a["material"]=1
    curb_b=strip_mesh(points,ROAD_HALF_WIDTH,ROAD_HALF_WIDTH+1.6,0.1,"inner-shoulder")
    curb_b["material"]=1
    water=(water_mesh(water_polygons) if water_polygons is not None else
           strip_mesh(points,MOAT_INNER_OFFSET,MOAT_OUTER_OFFSET,-0.06,"moat-water"))
    water["material"]=2
    materials=[
        {"name":"road","color":"#4a4843","shininess":5},
        {"name":"curb","color":"#c9a887","shininess":8},
        {"name":"water","color":"#3b9da5","shininess":20},
        {"name":"checkpoint","color":"#d9a34b","shininess":15}
    ]
    meshes=[road,curb_a,curb_b,water,gate_mesh(
        points,[g["point_index"] for g in gates] if gates is not None else None)]
    if gates is not None:
        materials.append({"name":"historic-wall-blockout","color":"#a96548","shininess":3})
        meshes.append(historic_gate_mesh(points,gates))
    if buildings is not None:
        if gates is None:
            raise ValueError("roadside building material IDs require historic gates")
        materials.extend((
            {"name":"osm-building-facades","color":"#c8b99b","shininess":3},
            {"name":"osm-building-roofs","color":"#8f6958","shininess":3}
        ))
        meshes.extend(roadside_building_meshes(buildings,points))
    if landmarks is not None:
        landmark_material_start=len(materials)
        materials.extend((
            {"name":"wat-chedi-luang-stupa-brick","color":"#9f6649","shininess":4},
            {"name":"wat-chedi-luang-stupa-trim","color":"#c2a27d","shininess":6},
            {"name":"wat-chedi-luang-viharn-walls","color":"#d4c6a4","shininess":5},
            {"name":"wat-chedi-luang-temple-roof","color":"#8b3f36","shininess":10}
        ))
        meshes.extend(wat_chedi_luang_meshes(landmarks,landmark_material_start))
    if water_polygons is not None:
        # M3 shoreline detail follows OSM water edges. Heights/stone colour
        # are original illustrative choices, not surveyed embankment data.
        bank_material=len(materials)
        materials.append({"name":"illustrative-moat-bank",
                          "color":"#92836f","shininess":2,"doubleSided":True})
        meshes.extend(water_bank_meshes(water_polygons,bank_material))
    # Gameplay-only bend warnings, not surveyed road signs; zero colliders.
    warnings=sharp_turn_warning_meshes(points,water_polygons,buildings)
    if warnings:
        amber=len(materials)
        materials.append({"name":"game-turn-sign-amber",
                          "color":"#f3b93c","shininess":3,"doubleSided":True})
        dark=len(materials)
        materials.append({"name":"game-turn-sign-arrow",
                          "color":"#252b2a","shininess":2,"doubleSided":True})
        warnings[0]["material"]=amber
        warnings[1]["material"]=dark
        meshes.extend(warnings)
    # Keep the stylised centreline as the final mesh for the existing preview.
    marking=lane_marking_mesh(points)
    marking["material"]=len(materials)
    materials.append({"name":"game-centreline-marking",
                      "color":"#eee4c7","shininess":2})
    meshes.append(marking)
    return {
        "format":FORMAT,
        "name":"chiangmai-moat-blockout",
        "materials":materials,
        "meshes":meshes,
    }

def metadata(points,gates=None):
    n=len(points)
    cp_indices=[0,n//4,n//2,3*n//4]
    names=["Tha Phae / Start","Chiang Mai / South","Suan Dok / West",
           "Chang Phueak / North"]
    if gates is not None:
        cp_indices=[gate["point_index"] for gate in gates]
        names=[gate["name"] for gate in gates]
    # A vehicle travels along local +Z; quaternion must rotate +Z onto
    # the route's tangent. An imported route may start on a diagonal.
    dx=points[1][0]-points[-1][0]
    dz=points[1][1]-points[-1][1]
    yaw=math.atan2(dx,dz)
    result={
        "format":"cmr-track-route-v1",
        "id":TRACK_ID,
        "source":"schematic-rounded-rectangle (NOT OSM-extracted)",
        "projection":{"origin_lat":CENTER_LAT,"origin_lon":CENTER_LON,
                      "x":"east in metres","z":"south in metres"},
        "clockwise":True,
        "closed":True,
        "road_width_m":2*ROAD_HALF_WIDTH,
        "moat_width_m":MOAT_OUTER_OFFSET-MOAT_INNER_OFFSET,
        "length_m":round(perimeter(points),3),
        "points":[[round(x,4),round(z,4)] for x,z in points],
        "checkpoints":[{"id":i,"name":names[i],"point_index":idx,
                        "x":round(points[idx][0],3),
                        "z":round(points[idx][1],3)}
                       for i,idx in enumerate(cp_indices)],
        "spawn":{"x":round(points[0][0],3),"z":round(points[0][1],3),
                 "yaw_rad":round(yaw,9),
                 "quaternion":[0,round(math.sin(yaw/2),9),0,
                               round(math.cos(yaw/2),9)]}
    }
    if gates is not None:
        result["historic_gates"]=[
            {"id":g["id"],"name":g["name"],"osm_node_id":g["osm_node_id"],
             "lon":g["lon"],"lat":g["lat"],"x":round(g["x"],3),
             "z":round(g["z"],3),"road_distance_m":round(g["distance_to_road_m"],3),
             "checkpoint_index":g["point_index"]}
            for g in gates]
        for cp,g in zip(result["checkpoints"],gates):
            cp["osm_gate_node_id"]=g["osm_node_id"]
    return result

def validate_geometry(data):
    assert data["format"]==FORMAT
    for mesh in data["meshes"]:
        n=len(mesh["positions"])//3
        assert len(mesh["positions"])%3==0
        assert len(mesh["indices"])%3==0
        assert 0<=mesh["material"]<len(data["materials"])
        assert all(0<=v<n for v in mesh["indices"])
        assert all(math.isfinite(v) for v in mesh["positions"])
        if "offset" in mesh:
            assert len(mesh["offset"])==3
            assert all(math.isfinite(v) for v in mesh["offset"])
    return True

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out",default="assets/tracks/chiangmai-moat")
    parser.add_argument("--geojson",help="verified, connected, closed LineString [lon,lat]")
    parser.add_argument("--water-geojson",help="optional OSM moat water polygons")
    parser.add_argument("--gates-geojson",help="optional OSM historic gate Points")
    parser.add_argument("--buildings-geojson",help="optional OSM roadside building footprints")
    parser.add_argument("--landmarks-geojson",help="optional OSM Wat Chedi Luang footprints")
    parser.add_argument("--schematic",action="store_true",
                        help="generate the original synthetic rounded rectangle")
    args=parser.parse_args()
    if args.schematic and args.geojson:
        parser.error("--schematic and --geojson cannot be combined")
    out=Path(args.out)
    source_path=None if args.schematic else Path(args.geojson or DEFAULT_GEOJSON)
    if source_path is not None:
        pts,source_sha=import_geojson(source_path)
        raw=json.loads(source_path.read_text(encoding="utf-8"))
        properties=raw.get("properties",{}) if raw.get("type")=="Feature" else {}
    else:
        pts=build_points()
        source_sha=None
        properties={}
    water_path=(Path(args.water_geojson) if args.water_geojson else
                DEFAULT_WATER if source_path==DEFAULT_GEOJSON else None)
    if water_path is not None:
        water_polygons,water_props=load_water_polygons(water_path)
        if properties.get("snapshot_sha256") and (
            water_props.get("snapshot_sha256")!=properties["snapshot_sha256"]
        ):
            raise ValueError("road/water OSM snapshot hashes differ")
    else:
        water_polygons=None
        water_props={}
    gates_path=(Path(args.gates_geojson) if args.gates_geojson else
                DEFAULT_GATES if source_path==DEFAULT_GEOJSON else None)
    if gates_path is not None:
        gates,gate_props=load_historic_gates(gates_path)
        if (properties.get("snapshot_sha256") and
            gate_props.get("snapshot_sha256")!=properties["snapshot_sha256"]):
            raise ValueError("road/gate OSM snapshot hashes differ")
        pts=align_gates_to_route(pts,gates)
    else:
        gates=None
        gate_props={}
    building_path=(Path(args.buildings_geojson) if args.buildings_geojson else
                   DEFAULT_BUILDINGS if source_path==DEFAULT_GEOJSON else None)
    if building_path is not None:
        buildings,building_props=load_roadside_buildings(building_path)
        if (properties.get("snapshot_sha256") and
            building_props.get("snapshot_sha256")!=properties["snapshot_sha256"]):
            raise ValueError("road/buildings OSM snapshot hashes differ")
    else:
        buildings=None
        building_props={}
    landmark_path=(Path(args.landmarks_geojson) if args.landmarks_geojson else
                   DEFAULT_LANDMARKS if source_path==DEFAULT_GEOJSON else None)
    if landmark_path is not None:
        landmarks,landmark_props=load_wat_chedi_luang(landmark_path)
        if (properties.get("snapshot_sha256") and
            landmark_props.get("snapshot_sha256")!=properties["snapshot_sha256"]):
            raise ValueError("road/Wat Chedi Luang OSM snapshot hashes differ")
    else:
        landmarks=None
        landmark_props={}
    asset=model(pts,water_polygons,gates,buildings,landmarks)
    validate_geometry(asset)
    route=metadata(pts,gates)
    if buildings is not None:
        route["building_source"]="OpenStreetMap building footprints (ODbL)"
        route["building_count"]=len(buildings)
        route["building_estimated_height_count"]=building_props["estimated_height_count"]
        route["building_source_sha256"]=hashlib.sha256(building_path.read_bytes()).hexdigest()
    if gates is not None:
        route["gate_source"]="OpenStreetMap historic=city_gate nodes (ODbL)"
        route["gate_source_sha256"]=hashlib.sha256(gates_path.read_bytes()).hexdigest()
    if landmarks is not None:
        route["landmark_source"]="OpenStreetMap Wat Chedi Luang compound/building footprints (ODbL)"
        route["landmark_source_sha256"]=hashlib.sha256(landmark_path.read_bytes()).hexdigest()
        route["landmark_model_status"]=landmark_props.get(
            "model_status","procedural visual blockout; not a surveyed reconstruction")
        route["landmarks"]=[{
            "name":"Wat Chedi Luang",
            "osm_way_ids":[landmarks[k][1]["osm_way_id"] for k in
                           ("compound","stupa","viharn","city-pillar-shrine")],
            "roles":["compound","stupa","viharn","city-pillar-shrine"]
        }]
    if water_polygons is not None:
        route["moat_width_m"]=None  # OSM polygon width varies; no fixed 20m claim
        route["water_source"]="OpenStreetMap water=moat polygons (ODbL)"
        route["water_polygon_count"]=len(water_polygons)
        route["water_way_ids"]=[f["properties"]["osm_way_id"] for f in
                                json.loads(water_path.read_text(encoding="utf-8"))["features"]]
        route["water_source_sha256"]=hashlib.sha256(water_path.read_bytes()).hexdigest()
    if source_sha:
        route["source"]=properties.get("source","GeoJSON input (provenance unverified)")
        route["source_sha256"]=source_sha
        if properties.get("license"):
            route["source_license"]=properties["license"]
        if properties.get("source_url"):
            route["source_url"]=properties["source_url"]
        if properties.get("osm_way_ids"):
            route["osm_way_ids"]=properties["osm_way_ids"]
            route["osm_snapshot_sha256"]=properties.get("snapshot_sha256")
            route["osm_snapshot_date_utc"]=properties.get("snapshot_date_utc")
            route["osm_source_api_url"]=properties.get("source_api_url")
            route["road_names"]=properties.get("road_names",[])
            route["review_status"]=properties.get("review_status","unreviewed")
    if not (6540*0.97 <= route["length_m"] <= 6540*1.03):
        raise ValueError("blockout loop outside ±3% length tolerance")
    for name,obj in (("road.json",asset),("route.json",route)):
        (out/name).write_text(json.dumps(obj,separators=(",",":"),ensure_ascii=False)+"\n",
                             encoding="utf-8")
    # Static route data is needed before the legacy engine boots, because
    # its collision analyser is synchronous. This is generated, not edited.
    route_js = ("var bkcore = bkcore || {};\n"
                "bkcore.hexgl = bkcore.hexgl || {};\n"
                "bkcore.hexgl.MoatRouteData = " +
                json.dumps(route,separators=(",",":"),ensure_ascii=False) + ";\n")
    (out/"route-data.js").write_text(route_js,encoding="utf-8")
    faces=sum(len(m["indices"])//3 for m in asset["meshes"])
    print(f"{route['length_m']:.1f} m, {len(pts)} points, {faces} triangles, "
          f"{len(asset['meshes'])} meshes; generated in {out}")

if __name__=="__main__":
    main()
