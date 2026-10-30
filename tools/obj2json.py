#!/usr/bin/env python3
"""Convert Wavefront OBJ + MTL into a compact JSON format for Three.js r50dev.

The target engine (HexGL / Three.js r50dev) has no glTF or OBJ loader, so assets
are converted offline into `cmr-static-v1` JSON and loaded by
`bkcore/threejs/StaticModelLoader.js`.

Usage:
    python tools/obj2json.py input.obj output.json \
        --name my-car --target-length 5.28 --center --merge-untextured

No third-party Python packages are required.
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
from collections import OrderedDict
from pathlib import Path


# ---------------------------------------------------------------------------
# MTL parsing
# ---------------------------------------------------------------------------

DEFAULT_MATERIAL = {
    "name": "default",
    "Kd": [1.0, 1.0, 1.0],
    "Ks": [0.0, 0.0, 0.0],
    "Ns": 30.0,
    "d": 1.0,
    "map_Kd": None,
}


def _floats(parts: list[str], count: int, fallback: list[float]) -> list[float]:
    values = []
    for raw in parts[:count]:
        try:
            values.append(float(raw))
        except ValueError:
            return list(fallback)
    while len(values) < count:
        values.append(fallback[len(values)])
    return values


def parse_mtl(path: Path) -> "OrderedDict[str, dict]":
    materials: "OrderedDict[str, dict]" = OrderedDict()
    current = None

    text = path.read_text(encoding="utf-8", errors="replace")
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        parts = line.split()
        key = parts[0]

        if key == "newmtl":
            name = " ".join(parts[1:]).strip() or "material"
            current = {
                "name": name,
                "Kd": [1.0, 1.0, 1.0],
                "Ks": [0.0, 0.0, 0.0],
                "Ns": 30.0,
                "d": 1.0,
                "map_Kd": None,
            }
            materials[name] = current
            continue

        if current is None:
            continue

        if key == "Kd":
            current["Kd"] = _floats(parts[1:], 3, [1.0, 1.0, 1.0])
        elif key == "Ks":
            current["Ks"] = _floats(parts[1:], 3, [0.0, 0.0, 0.0])
        elif key == "Ns":
            try:
                current["Ns"] = float(parts[1])
            except (IndexError, ValueError):
                pass
        elif key == "d":
            try:
                current["d"] = float(parts[1])
            except (IndexError, ValueError):
                pass
        elif key == "map_Kd":
            # Handles: "map_Kd file.png" and "map_Kd -s 1 1 1 file.png"
            candidate = " ".join(parts[1:]).strip().strip('"').strip("'")
            if candidate:
                # Drop common option prefixes.
                tokens = candidate.split()
                if tokens and tokens[0].startswith("-"):
                    candidate = tokens[-1]
                current["map_Kd"] = candidate

    return materials


# ---------------------------------------------------------------------------
# OBJ parsing
# ---------------------------------------------------------------------------


def _index(token: str, count: int) -> int | None:
    if token == "":
        return None
    value = int(token)
    if value < 0:
        value = count + value
    else:
        value -= 1
    if value < 0 or value >= count:
        raise ValueError(f"index out of range: {token}")
    return value


def parse_obj(path: Path) -> dict:
    positions: list[tuple[float, float, float]] = []
    uvs: list[tuple[float, float]] = []
    normals: list[tuple[float, float, float]] = []
    groups: "OrderedDict[str, list[list[tuple[int, int | None, int | None]]]]" = OrderedDict()
    current_group = "default"
    mtllib = None

    text = path.read_text(encoding="utf-8", errors="replace")
    for line_number, raw_line in enumerate(text.splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        parts = line.split()
        key = parts[0]

        try:
            if key == "v":
                positions.append((float(parts[1]), float(parts[2]), float(parts[3])))
            elif key == "vt":
                u = float(parts[1]) if len(parts) > 1 else 0.0
                v = float(parts[2]) if len(parts) > 2 else 0.0
                uvs.append((u, v))
            elif key == "vn":
                normals.append((float(parts[1]), float(parts[2]), float(parts[3])))
            elif key == "mtllib":
                mtllib = " ".join(parts[1:]).strip()
            elif key == "usemtl":
                current_group = " ".join(parts[1:]).strip() or "default"
                groups.setdefault(current_group, [])
            elif key == "f":
                corners = []
                for token in parts[1:]:
                    chunks = token.split("/")
                    vi = _index(chunks[0], len(positions))
                    if vi is None:
                        raise ValueError("face without vertex index")
                    ti = _index(chunks[1], len(uvs)) if len(chunks) > 1 and chunks[1] else None
                    ni = _index(chunks[2], len(normals)) if len(chunks) > 2 and chunks[2] else None
                    corners.append((vi, ti, ni))
                if len(corners) < 3:
                    continue
                groups.setdefault(current_group, []).append(corners)
        except (IndexError, ValueError) as exc:
            raise ValueError(f"{path.name}:{line_number}: {exc}") from exc

    return {
        "positions": positions,
        "uvs": uvs,
        "normals": normals,
        "groups": groups,
        "mtllib": mtllib,
    }


# ---------------------------------------------------------------------------
# Transform helpers
# ---------------------------------------------------------------------------


def rotate_xyz(
    position: tuple[float, float, float], rot_x_deg: float, rot_y_deg: float
) -> tuple[float, float, float]:
    x, y, z = position

    if rot_x_deg:
        radians = math.radians(rot_x_deg)
        cos_a, sin_a = math.cos(radians), math.sin(radians)
        y, z = y * cos_a - z * sin_a, y * sin_a + z * cos_a

    if rot_y_deg:
        radians = math.radians(rot_y_deg)
        cos_a, sin_a = math.cos(radians), math.sin(radians)
        x, z = x * cos_a + z * sin_a, -x * sin_a + z * cos_a

    return x, y, z


def bounds_of(positions: list[tuple[float, float, float]]) -> tuple[list[float], list[float]]:
    if not positions:
        return [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]
    mins = [min(p[i] for p in positions) for i in range(3)]
    maxs = [max(p[i] for p in positions) for i in range(3)]
    return mins, maxs


def color_hex(rgb: list[float]) -> str:
    channels = []
    for value in rgb[:3]:
        channels.append(max(0, min(255, round(value * 255))))
    return "#{:02x}{:02x}{:02x}".format(*channels)


# ---------------------------------------------------------------------------
# Conversion
# ---------------------------------------------------------------------------


def build_mesh(
    face_lists: list[list[tuple[int, int | None, int | None]]],
    positions: list[tuple[float, float, float]],
    uvs: list[tuple[float, float]],
    normals: list[tuple[float, float, float]],
    vertex_color: tuple[float, float, float] | None,
) -> dict:
    """Build one mesh. Deduplicate by (position, uv, normal, color) so hard/soft
    edges from the original OBJ are preserved while keeping the vertex count low.
    """
    vertex_map: dict[tuple, int] = {}
    out_positions: list[float] = []
    out_normals: list[float] = []
    out_uvs: list[float] = []
    out_colors: list[float] = []
    indices: list[int] = []

    color_key = None
    if vertex_color is not None:
        color_key = tuple(round(c, 6) for c in vertex_color)

    for corners in face_lists:
        # Fan triangulation for n-gons.
        for triangle in range(1, len(corners) - 1):
            for corner in (corners[0], corners[triangle], corners[triangle + 1]):
                vi, ti, ni = corner
                key = (vi, ti, ni, color_key)
                index = vertex_map.get(key)
                if index is None:
                    index = len(out_positions) // 3
                    vertex_map[key] = index

                    x, y, z = positions[vi]
                    out_positions.extend((x, y, z))

                    if ni is not None:
                        out_normals.extend(normals[ni])
                    else:
                        out_normals.extend((0.0, 0.0, 0.0))

                    if ti is not None:
                        out_uvs.extend(uvs[ti])
                    else:
                        out_uvs.extend((0.0, 0.0))

                    if vertex_color is not None:
                        out_colors.extend(vertex_color)

                indices.append(index)

    mesh = {
        "positions": out_positions,
        "normals": out_normals,
        "uvs": out_uvs,
        "indices": indices,
    }
    if vertex_color is not None:
        mesh["colors"] = out_colors
    return mesh


def resolve_texture(texture_path: str, obj_dir: Path, mtl_dir: Path) -> Path | None:
    raw = Path(texture_path.replace("\\", "/"))
    candidates = []
    if raw.is_absolute():
        candidates.append(raw)
    else:
        candidates.extend([mtl_dir / raw, obj_dir / raw])

    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    return None


def convert(args: argparse.Namespace) -> dict:
    obj_path = Path(args.input).resolve()
    out_path = Path(args.output).resolve()
    out_dir = out_path.parent
    out_dir.mkdir(parents=True, exist_ok=True)

    obj = parse_obj(obj_path)
    if not obj["positions"]:
        raise SystemExit(f"No vertices found in {obj_path}")

    mtl_path = None
    materials: "OrderedDict[str, dict]" = OrderedDict()
    if obj["mtllib"]:
        mtl_path = (obj_path.parent / obj["mtllib"]).resolve()
    if mtl_path is None or not mtl_path.is_file():
        fallback = obj_path.with_suffix(".mtl")
        if fallback.is_file():
            mtl_path = fallback.resolve()

    if mtl_path and mtl_path.is_file():
        materials = parse_mtl(mtl_path)

    # Transform positions: rotate -> scale -> center.
    transformed: list[tuple[float, float, float]] = []
    for position in obj["positions"]:
        transformed.append(rotate_xyz(position, args.rotate_x, args.rotate_y))

    mins, maxs = bounds_of(transformed)
    size = [maxs[i] - mins[i] for i in range(3)]
    scale = args.scale
    if args.target_length and max(size) > 0:
        scale *= args.target_length / max(size)

    if scale != 1.0:
        transformed = [(x * scale, y * scale, z * scale) for x, y, z in transformed]

    if args.center:
        mins, maxs = bounds_of(transformed)
        cx = (mins[0] + maxs[0]) * 0.5
        cz = (mins[2] + maxs[2]) * 0.5
        min_y = mins[1]
        transformed = [
            (x - cx, y - min_y, z - cz) for x, y, z in transformed
        ]

    # Transform normals (rotation only).
    transformed_normals: list[tuple[float, float, float]] = []
    for normal in obj["normals"]:
        transformed_normals.append(rotate_xyz(normal, args.rotate_x, args.rotate_y))

    mins, maxs = bounds_of(transformed)
    bounds = {
        "min": [round(v, 6) for v in mins],
        "max": [round(v, 6) for v in maxs],
    }

    # Ensure every group has an entry, even if the OBJ omits usemtl.
    if not obj["groups"]:
        obj["groups"]["default"] = []

    # Resolve textures and copy them next to the JSON.
    texture_dir = out_dir / "textures"
    texture_cache: dict[Path, str] = {}
    used_names: dict[str, Path] = {}

    def texture_reference(source: Path, material_name: str) -> str:
        if source in texture_cache:
            return texture_cache[source]

        texture_dir.mkdir(parents=True, exist_ok=True)
        name = source.name
        if name in used_names and used_names[name] != source:
            stem, suffix = source.stem, source.suffix
            safe_material = "".join(
                c if c.isalnum() or c in "-_" else "_" for c in material_name
            )
            name = f"{stem}_{safe_material}{suffix}"

        target = texture_dir / name
        if not target.is_file() or target.stat().st_size != source.stat().st_size:
            shutil.copy2(source, target)

        used_names[name] = source
        reference = f"textures/{name}"
        texture_cache[source] = reference
        return reference

    out_materials: list[dict] = []
    out_meshes: list[dict] = []
    textured_groups = []
    untextured_groups = []

    for group_name, face_lists in obj["groups"].items():
        material = materials.get(group_name)
        if material is None:
            material = dict(DEFAULT_MATERIAL)
            material["name"] = group_name

        texture_source = None
        if material.get("map_Kd"):
            texture_source = resolve_texture(
                material["map_Kd"], obj_path.parent, mtl_path.parent if mtl_path else obj_path.parent
            )
            if texture_source is None:
                print(
                    f"warning: texture not found for material '{group_name}': "
                    f"{material['map_Kd']}",
                    file=sys.stderr,
                )

        if texture_source is not None:
            textured_groups.append((group_name, face_lists, material, texture_source))
        else:
            untextured_groups.append((group_name, face_lists, material))

    # Textured materials: one mesh per material (one texture each).
    for group_name, face_lists, material, texture_source in textured_groups:
        mesh = build_mesh(
            face_lists,
            transformed,
            obj["uvs"],
            transformed_normals,
            vertex_color=None,
        )
        reference = texture_reference(texture_source, group_name)
        material_index = len(out_materials)
        out_materials.append(
            {
                "name": material["name"],
                "color": "#ffffff",
                "map": reference,
                "shininess": max(0.0, min(1000.0, float(material["Ns"]))),
                "specular": color_hex(material["Ks"]),
                "opacity": float(material["d"]),
                "transparent": float(material["d"]) < 1.0,
                "doubleSided": bool(args.double_sided),
                "vertexColors": False,
            }
        )
        out_meshes.append({"name": group_name, "material": material_index, **mesh})

    # Untextured materials: merge into one vertex-colored mesh by default.
    if untextured_groups:
        if args.merge_untextured:
            merged = {
                "positions": [],
                "normals": [],
                "uvs": [],
                "colors": [],
                "indices": [],
            }
            for group_name, face_lists, material in untextured_groups:
                mesh = build_mesh(
                    face_lists,
                    transformed,
                    obj["uvs"],
                    transformed_normals,
                    vertex_color=tuple(material["Kd"]),
                )
                offset = len(merged["positions"]) // 3
                merged["positions"].extend(mesh["positions"])
                merged["normals"].extend(mesh["normals"])
                merged["uvs"].extend(mesh["uvs"])
                merged["colors"].extend(mesh["colors"])
                merged["indices"].extend(index + offset for index in mesh["indices"])

            material_index = len(out_materials)
            out_materials.append(
                {
                    "name": "merged-untextured",
                    "color": "#ffffff",
                    "map": None,
                    "shininess": 30.0,
                    "specular": "#111111",
                    "opacity": 1.0,
                    "transparent": False,
                    "doubleSided": bool(args.double_sided),
                    "vertexColors": True,
                }
            )
            out_meshes.append(
                {"name": "merged-untextured", "material": material_index, **merged}
            )
        else:
            for group_name, face_lists, material in untextured_groups:
                mesh = build_mesh(
                    face_lists,
                    transformed,
                    obj["uvs"],
                    transformed_normals,
                    vertex_color=None,
                )
                material_index = len(out_materials)
                out_materials.append(
                    {
                        "name": material["name"],
                        "color": color_hex(material["Kd"]),
                        "map": None,
                        "shininess": max(0.0, min(1000.0, float(material["Ns"]))),
                        "specular": color_hex(material["Ks"]),
                        "opacity": float(material["d"]),
                        "transparent": float(material["d"]) < 1.0,
                        "doubleSided": bool(args.double_sided),
                        "vertexColors": False,
                    }
                )
                out_meshes.append(
                    {"name": group_name, "material": material_index, **mesh}
                )

    vertex_count = sum(len(mesh["positions"]) // 3 for mesh in out_meshes)
    triangle_count = sum(len(mesh["indices"]) // 3 for mesh in out_meshes)

    data = {
        "format": "cmr-static-v1",
        "name": args.name or obj_path.stem,
        "generator": "tools/obj2json.py",
        "source": {
            "obj": obj_path.name,
            "mtl": mtl_path.name if mtl_path else None,
        },
        "license": args.license or "",
        "author": args.author or "",
        "bounds": bounds,
        "materials": out_materials,
        "meshes": out_meshes,
        "stats": {
            "sourceVertices": len(obj["positions"]),
            "sourceFaces": sum(len(faces) for faces in obj["groups"].values()),
            "vertices": vertex_count,
            "triangles": triangle_count,
            "materials": len(out_materials),
            "meshes": len(out_meshes),
            "textures": len(texture_cache),
        },
    }

    return data


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert OBJ + MTL to cmr-static-v1 JSON for Three.js r50dev."
    )
    parser.add_argument("input", help="input .obj file")
    parser.add_argument("output", help="output .json file")
    parser.add_argument("--name", default=None, help="model name")
    parser.add_argument("--license", default=None, help="license label, e.g. CC0-1.0")
    parser.add_argument("--author", default=None, help="author credit")
    parser.add_argument("--scale", type=float, default=1.0, help="uniform scale")
    parser.add_argument(
        "--target-length",
        type=float,
        default=None,
        help="uniformly scale so the longest bbox axis equals this value (meters)",
    )
    parser.add_argument("--rotate-x", type=float, default=0.0, help="rotation around X in degrees")
    parser.add_argument("--rotate-y", type=float, default=0.0, help="rotation around Y in degrees")
    parser.add_argument(
        "--center",
        action="store_true",
        help="center X/Z and place the lowest point at Y=0",
    )
    parser.add_argument(
        "--merge-untextured",
        action="store_true",
        default=True,
        help="merge all materials without a texture into one vertex-colored mesh (default)",
    )
    parser.add_argument(
        "--no-merge-untextured",
        dest="merge_untextured",
        action="store_false",
        help="keep untextured materials as separate meshes",
    )
    parser.add_argument(
        "--double-sided",
        action="store_true",
        help="render both sides (useful for thin foliage / cloth)",
    )
    parser.add_argument("--pretty", action="store_true", help="pretty-print JSON")

    args = parser.parse_args()
    data = convert(args)

    out_path = Path(args.output)
    with out_path.open("w", encoding="utf-8", newline="\n") as handle:
        if args.pretty:
            json.dump(data, handle, ensure_ascii=False, indent=2)
        else:
            json.dump(data, handle, ensure_ascii=False, separators=(",", ":"))

    stats = data["stats"]
    print(
        f"wrote {out_path} | vertices={stats['vertices']} "
        f"triangles={stats['triangles']} materials={stats['materials']} "
        f"meshes={stats['meshes']} textures={stats['textures']}"
    )


if __name__ == "__main__":
    main()
