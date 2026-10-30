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

    function buildMaterial(materialData, basePath) {
        var params = {
            color: new THREE.Color(materialData.color || '#ffffff'),
            shininess: materialData.shininess !== undefined ? materialData.shininess : 30,
            specular: new THREE.Color(materialData.specular || '#111111'),
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
        if (!data || data.format !== 'cmr-static-v1') {
            throw new Error('StaticModelLoader: unsupported format');
        }

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
            root.add(mesh);
        }

        return root;
    }

    function load(url, onLoad, onError, onProgress) {
        var xhr = new XMLHttpRequest();
        xhr.open('GET', url, true);
        xhr.responseType = 'text';

        if (onProgress) {
            xhr.onprogress = function (event) {
                if (event.lengthComputable) {
                    onProgress(event.loaded / event.total);
                }
            };
        }

        xhr.onreadystatechange = function () {
            if (xhr.readyState !== 4) {
                return;
            }

            if (xhr.status !== 200 && xhr.status !== 0) {
                if (onError) {
                    onError(new Error('StaticModelLoader: HTTP ' + xhr.status + ' for ' + url));
                }
                return;
            }

            var data;
            try {
                data = JSON.parse(xhr.responseText);
            } catch (error) {
                if (onError) {
                    onError(error);
                }
                return;
            }

            var slash = url.lastIndexOf('/');
            var basePath = slash >= 0 ? url.substring(0, slash + 1) : '';

            try {
                onLoad(build(data, basePath));
            } catch (error) {
                if (onError) {
                    onError(error);
                }
            }
        };

        xhr.send(null);
    }

    return {
        build: build,
        load: load
    };

})();
