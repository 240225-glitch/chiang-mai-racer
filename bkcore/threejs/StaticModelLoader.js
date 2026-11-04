/**
 * StaticModelLoader for Three.js r50dev (HexGL).
 *
 * Loads the compact `cmr-static-v1` JSON produced by tools/obj2json.py and
 * builds old-style THREE.Geometry meshes. No glTF / OBJ parser required.
 *
 * Usage:
 *   THREE.StaticModelLoader.load('assets/cars/grab3d-race-car/model.json', function (model) {
 *     scene.add(model);
 *   });
 */
THREE.StaticModelLoader = (function () {

    // Offline OSM/OBJ conversion is not a guarantee of valid JSON. Validate
    // before creating Face3 objects: an out-of-range index can otherwise
    // survive construction and crash WebGL later, after the loading screen.
    // Limits also bound allocations from an accidental corrupt asset.
    function validate(data) {
        if (!data || data.format !== 'cmr-static-v1' ||
            !Array.isArray(data.materials) || !data.materials.length ||
            data.materials.length > 128 ||
            !Array.isArray(data.meshes) || !data.meshes.length ||
            data.meshes.length > 256) {
            throw new Error('StaticModelLoader: invalid model manifest');
        }
        // Per-mesh limits alone are not enough: a corrupt asset can carry
        // hundreds of individually valid meshes and allocate millions of
        // legacy Face3 objects before the first WebGL frame. Bound the
        // entire model before constructing any Three.js geometry.
        var totalVertices = 0;
        var totalIndices = 0;
        for (var i = 0; i < data.materials.length; i++) {
            if (!data.materials[i] || typeof data.materials[i] !== 'object')
                throw new Error('StaticModelLoader: invalid material ' + i);
        }
        for (var j = 0; j < data.meshes.length; j++) {
            var mesh = data.meshes[j];
            if (!mesh || !Array.isArray(mesh.positions) ||
                !Array.isArray(mesh.indices) ||
                mesh.positions.length < 9 ||
                mesh.positions.length % 3 !== 0 ||
                mesh.positions.length > 900000 ||
                mesh.indices.length < 3 ||
                mesh.indices.length % 3 !== 0 ||
                mesh.indices.length > 1200000) {
                throw new Error('StaticModelLoader: invalid mesh arrays at ' + j);
            }
            if (mesh.offset !== undefined &&
                (!Array.isArray(mesh.offset) || mesh.offset.length !== 3 ||
                 mesh.offset.some(function (v) {
                     return typeof v !== 'number' || !isFinite(v);
                 }))) {
                throw new Error('StaticModelLoader: invalid mesh offset at ' + j);
            }
            var vertices = mesh.positions.length / 3;
            totalVertices += vertices;
            totalIndices += mesh.indices.length;
            if (totalVertices > 500000)
                throw new Error('StaticModelLoader: model vertex limit exceeded');
            if (totalIndices > 2000000)
                throw new Error('StaticModelLoader: model face index limit exceeded');
            if (typeof mesh.material !== 'number' ||
                mesh.material % 1 !== 0 ||
                mesh.material < 0 || mesh.material >= data.materials.length)
                throw new Error('StaticModelLoader: invalid material index at ' + j);

            var normals = mesh.normals || [];
            var uvs = mesh.uvs || [];
            var colors = mesh.colors || [];
            if (!Array.isArray(normals) || !Array.isArray(uvs) ||
                !Array.isArray(colors) ||
                (normals.length && normals.length !== mesh.positions.length) ||
                (uvs.length && uvs.length !== vertices * 2) ||
                (colors.length && colors.length !== mesh.positions.length)) {
                throw new Error('StaticModelLoader: mismatched attributes at ' + j);
            }
            var arrays = [mesh.positions, normals, uvs, colors];
            for (var k = 0; k < arrays.length; k++)
                for (var n = 0; n < arrays[k].length; n++)
                    if (typeof arrays[k][n] !== 'number' || !isFinite(arrays[k][n]))
                        throw new Error('StaticModelLoader: non-finite vertex attribute at ' + j);
            for (var m = 0; m < mesh.indices.length; m++) {
                var index = mesh.indices[m];
                if (typeof index !== 'number' || index % 1 !== 0 ||
                    index < 0 || index >= vertices)
                    throw new Error('StaticModelLoader: invalid face index at ' + j);
            }
        }
    }

    function buildGeometry(meshData) {
        var geometry = new THREE.Geometry();
        var positions = meshData.positions || [];
        var normals = meshData.normals || [];
        var uvs = meshData.uvs || [];
        var colors = meshData.colors || [];
        var indices = meshData.indices || [];

        var i;
        for (i = 0; i < positions.length; i += 3) {
            geometry.vertices.push(
                new THREE.Vector3(positions[i], positions[i + 1], positions[i + 2])
            );
        }

        var vertexColors = [];
        if (colors.length) {
            for (i = 0; i < colors.length; i += 3) {
                // Three.js r50's Color constructor only accepts a single hex
                // value, so vertex colors must be assigned through setRGB().
                var vertexColor = new THREE.Color();
                vertexColor.setRGB(colors[i], colors[i + 1], colors[i + 2]);
                vertexColors.push(vertexColor);
            }
            geometry.colors = vertexColors.slice();
        }

        var hasNormals = normals.length === positions.length;
        var hasUVs = uvs.length > 0;

        for (i = 0; i < indices.length; i += 3) {
            var a = indices[i];
            var b = indices[i + 1];
            var c = indices[i + 2];
            var face = new THREE.Face3(a, b, c);

            if (vertexColors.length) {
                face.vertexColors = [vertexColors[a], vertexColors[b], vertexColors[c]];
            }

            if (hasNormals) {
                var na = new THREE.Vector3(normals[a * 3], normals[a * 3 + 1], normals[a * 3 + 2]);
                var nb = new THREE.Vector3(normals[b * 3], normals[b * 3 + 1], normals[b * 3 + 2]);
                var nc = new THREE.Vector3(normals[c * 3], normals[c * 3 + 1], normals[c * 3 + 2]);
                face.vertexNormals = [na, nb, nc];
                face.normal.copy(na).addSelf(nb).addSelf(nc).normalize();
            }

            geometry.faces.push(face);

            if (hasUVs) {
                var ia = a * 2, ib = b * 2, ic = c * 2;
                geometry.faceVertexUvs[0].push([
                    new THREE.UV(uvs[ia], uvs[ia + 1]),
                    new THREE.UV(uvs[ib], uvs[ib + 1]),
                    new THREE.UV(uvs[ic], uvs[ic + 1])
                ]);
            }
        }

        if (!hasNormals) {
            geometry.computeFaceNormals();
            geometry.computeVertexNormals();
        }

        geometry.computeBoundingBox();
        geometry.computeBoundingSphere();
        return geometry;
    }

    // Three.js r50dev Color only accepts numeric 0xRRGGBB. Our asset
    // converter emits CSS-style #RRGGBB strings, which otherwise turn black.
    //
    // Return numbers, not Color instances: r50's MeshPhongMaterial.setValues()
    // feeds constructor parameters through Color.set(), and passing a Color
    // object there silently resolves to black. That bug made every imported
    // surface black and left only the white ambient light visible.
    function legacyHex(value, fallback) {
        if (typeof value === 'string') {
            value = /^#[0-9a-f]{6}$/i.test(value) ? parseInt(value.slice(1), 16) : fallback;
        }
        return value === undefined || value === null ? fallback : value;
    }

    function buildMaterial(materialData, basePath) {
        var params = {
            color: legacyHex(materialData.color, 0xffffff),
            // The stock Phong material defaults ambient to white. With
            // HexGL's bright ambient light that washes flat-colour OSM
            // blockouts out to near-white, so keep a dim neutral floor.
            ambient: legacyHex(materialData.ambient, 0x222222),
            // r50 also passes emissive through Color.set(), so it needs a
            // number rather than "#RRGGBB" or a Color instance.
            emissive: legacyHex(materialData.emissive, 0x000000),
            shininess: materialData.shininess !== undefined ? materialData.shininess : 30,
            specular: legacyHex(materialData.specular, 0x111111),
            transparent: !!materialData.transparent,
            opacity: materialData.opacity !== undefined ? materialData.opacity : 1,
            side: materialData.doubleSided ? THREE.DoubleSide : THREE.FrontSide,
            vertexColors: materialData.vertexColors ? THREE.VertexColors : THREE.NoColors
        };

        if (materialData.map) {
            params.map = THREE.ImageUtils.loadTexture(basePath + materialData.map);
        }

        return new THREE.MeshPhongMaterial(params);
    }

    function build(data, basePath) {
        validate(data);

        basePath = basePath || '';
        var root = new THREE.Object3D();
        root.name = data.name || 'static-model';
        root.modelData = data;

        var materials = [];
        var i;
        for (i = 0; i < data.materials.length; i++) {
            materials.push(buildMaterial(data.materials[i], basePath));
        }

        for (i = 0; i < data.meshes.length; i++) {
            var meshData = data.meshes[i];
            var geometry = buildGeometry(meshData);
            var material = materials[meshData.material] || materials[0];
            var mesh = new THREE.Mesh(geometry, material);
            mesh.name = meshData.name || ('mesh-' + i);
            // Optional baked world offset. Local vertices are centred so
            // Three.js r50's origin-based bounding sphere can cull chunks.
            if (meshData.offset) {
                mesh.position.set(meshData.offset[0], meshData.offset[1],
                                  meshData.offset[2]);
            }
            root.add(mesh);
        }

        return root;
    }

    function load(url, onLoad, onError, onProgress) {
        var xhr = new XMLHttpRequest();
        var settled = false;
        var watchdog = null;
        // XHR.timeout is not reliably delivered by every browser/protocol.
        // A fully silent request must still release the M2 road fallback.
        xhr.timeout = 30000;

        function finish() {
            if (settled) return false;
            settled = true;
            if (watchdog !== null) clearTimeout(watchdog);
            return true;
        }

        function fail(error) {
            if (!finish()) return;
            if (onError) onError(error);
        }

        xhr.onerror = function () {
            fail(new Error('StaticModelLoader: network error for ' + url));
        };
        xhr.ontimeout = function () {
            fail(new Error('StaticModelLoader: timeout for ' + url));
        };
        xhr.onabort = function () {
            fail(new Error('StaticModelLoader: aborted request for ' + url));
        };

        if (onProgress) {
            xhr.onprogress = function (event) {
                if (!settled && event.lengthComputable && event.total > 0) {
                    onProgress(event.loaded / event.total);
                }
            };
        }

        xhr.onreadystatechange = function () {
            if (settled || xhr.readyState !== 4) return;

            // Status 0 is valid for a locally opened file:// asset when it
            // has a response body; network errors are handled separately.
            if (xhr.status !== 200 && xhr.status !== 0) {
                fail(new Error('StaticModelLoader: HTTP ' + xhr.status + ' for ' + url));
                return;
            }

            var data;
            try {
                data = JSON.parse(xhr.responseText);
            } catch (error) {
                fail(error);
                return;
            }

            var slash = url.lastIndexOf('/');
            var basePath = slash >= 0 ? url.substring(0, slash + 1) : '';
            var model;
            try {
                model = build(data, basePath);
            } catch (error) {
                fail(error);
                return;
            }
            if (finish()) onLoad(model);
        };

        watchdog = setTimeout(function () {
            fail(new Error('StaticModelLoader: timeout for ' + url));
        }, 30000);
        try {
            xhr.open('GET', url, true);
            xhr.responseType = 'text';
            xhr.send(null);
        } catch (error) {
            fail(error);
        }
    }

    return {
        build: build,
        load: load
    };

})();
