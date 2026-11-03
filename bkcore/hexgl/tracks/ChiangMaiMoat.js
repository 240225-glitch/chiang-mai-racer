/*
 * Opt-in M2 playable Chiang Mai moat blockout.
 *
 * Shares the proven Cityscape scene/HUD/controls but loads only assets that
 * scene actually uses in moat mode. Default Cityscape is left untouched.
 * OSM-derived road/water/building footprints with stylised geometry; the
 * gameplay road width and most building heights are estimated, not surveyed.
 */
var bkcore = bkcore || {};
bkcore.hexgl = bkcore.hexgl || {};
bkcore.hexgl.tracks = bkcore.hexgl.tracks || {};

(function () {
    var original = bkcore.hexgl.tracks.Cityscape;
    var route = bkcore.hexgl.MoatRouteData;
    if (!original) return;

    // The road JSON has a Cityscape fallback, but a missing/corrupt route
    // script used to abort track registration before that fallback existed.
    // Validate the metadata before building the opt-in track so Cityscape
    // remains playable even when the route asset is damaged or missing.
    var analyser;
    function validNumber(value) {
        return typeof value === 'number' && isFinite(value);
    }
    try {
        if (!route || !route.spawn || !route.spawn.quaternion ||
            route.spawn.quaternion.length !== 4 ||
            !validNumber(route.spawn.x) || !validNumber(route.spawn.z) ||
            !validNumber(route.spawn.yaw_rad) ||
            !route.checkpoints || route.checkpoints.length !== 4)
            throw new Error('invalid route metadata');
        for (var i=0;i<4;i++) {
            if (!validNumber(route.spawn.quaternion[i]) ||
                !validNumber(route.checkpoints[i].x) ||
                !validNumber(route.checkpoints[i].z))
                throw new Error('invalid route spawn or checkpoint');
        }
        analyser = new bkcore.hexgl.MoatCollision.Collision(route);
        // Numeric metadata alone is not sufficient: a misplaced start or
        // checkpoint can leave a race impossible to start or complete.
        // Keep the game playable by taking the existing Cityscape fallback.
        var q=route.spawn.quaternion, qLength2=0;
        for (var k=0;k<4;k++) qLength2+=q[k]*q[k];
        if (Math.abs(qLength2-1)>0.01)
            throw new Error('invalid route spawn orientation');
        var maxDistance=Math.max(0,analyser.halfWidth-0.5);
        var maxDistance2=maxDistance*maxDistance;
        if (analyser.distanceSquared(route.spawn.x,route.spawn.z)>maxDistance2)
            throw new Error('route spawn outside road');
        for (var c=0;c<route.checkpoints.length;c++) {
            var cp=route.checkpoints[c];
            if (analyser.distanceSquared(cp.x,cp.z)>maxDistance2)
                throw new Error('route checkpoint outside road');
        }
    } catch (error) {
        console.warn('Moat route unavailable: using Cityscape', error);
        bkcore.hexgl.tracks.ChiangMaiMoat = original;
        return;
    }

    var track = Object.create(original);
    track.id = route.id;
    track.name = 'Chiang Mai Moat (OSM prototype)';
    track.lib = null;
    track.materials = {};
    track.moatMode = true;
    track.roadModel = null;
    track.trackScale = 1;
    track.pixelRatio = 1; // collision samples use metres, not image pixels
    track.spawn = {x:route.spawn.x, y:4, z:route.spawn.z};
    track.spawnRotation = {
        x:route.spawn.quaternion[0],
        y:route.spawn.quaternion[1],
        z:route.spawn.quaternion[2],
        w:route.spawn.quaternion[3]
    };
    // Sideways offset relative to the direction of travel, not world X.
    // Otherwise imported diagonal/east-west starts put two players in a row.
    track.spawnLateral = {
        x:Math.cos(route.spawn.yaw_rad),
        z:-Math.sin(route.spawn.yaw_rad)
    };
    track.checkpoints = {list:[0,1,2,3], start:0, last:3};
    track.analyser = analyser;
    track.flatHeight = new bkcore.hexgl.MoatCollision.HeightMap();

    function resources(quality) {
        var low = quality < 2;
        var prefix = low ? 'textures/' : 'textures.full/';
        var manifest = {
            textures: {
                'hex': prefix + 'hud/hex.jpg',
                'ship.feisar.diffuse': prefix + 'ships/feisar/diffuse.jpg',
                'booster.diffuse': prefix + 'ships/feisar/booster/booster.png',
                'booster.sprite': prefix + 'ships/feisar/booster/boostersprite.jpg'
            },
            texturesCube: {
                'skybox.dawnclouds': prefix + 'skybox/dawnclouds/%1.jpg'
            },
            geometries: {
                'booster': 'geometries/booster/booster.js',
                'ship.feisar': 'geometries/ships/feisar/feisar.js'
            },
            images: {
                'hud.bg': prefix + 'hud/hud-bg.png',
                'hud.speed': prefix + 'hud/hud-fg-speed.png',
                'hud.shield': prefix + 'hud/hud-fg-shield.png'
            },
            sounds: {
                bg: {src:'audio/bg.ogg',loop:true,usePanner:false},
                crash: {src:'audio/crash.ogg',loop:false,usePanner:true},
                destroyed: {src:'audio/destroyed.ogg',loop:false,usePanner:false},
                boost: {src:'audio/boost.ogg',loop:false,usePanner:true},
                wind: {src:'audio/wind.ogg',loop:true,usePanner:true}
            }
        };
        if (!low) {
            manifest.textures['ship.feisar.specular'] = prefix + 'ships/feisar/specular.jpg';
            manifest.textures['ship.feisar.normal'] = prefix + 'ships/feisar/normal.jpg';
        }
        if (quality > 2) {
            manifest.textures.spark = prefix + 'particles/spark.png';
            manifest.textures.cloud = prefix + 'particles/cloud.png';
        }
        return manifest;
    }

    track.buildMaterials = function(quality) {
        if (!this.moatMode) return original.buildMaterials.call(this, quality);

        if (quality < 2) {
            this.materials.ship = new THREE.MeshBasicMaterial({
                map:this.lib.get('textures','ship.feisar.diffuse'),
                ambient:0xaaaaaa
            });
        } else {
            this.materials.ship = bkcore.Utils.createNormalMaterial({
                diffuse:this.lib.get('textures','ship.feisar.diffuse'),
                specular:this.lib.get('textures','ship.feisar.specular'),
                normal:this.lib.get('textures','ship.feisar.normal'),
                ambient:0x444444,
                shininess:42, metal:true, perPixel:false
            });
        }
        this.materials.booster = new THREE.MeshBasicMaterial({
            map:this.lib.get('textures','booster.diffuse'),
            transparent:true
        });
        // No Cityscape track, start-line, bonus or checkpoint materials.
    };

    // A 200-OK cmr-static-v1 file can be a valid *model* but the wrong
    // model for this route (or a stale build from another route). The
    // physics corridor would still work while the visible road was absent
    // or displaced. Our blockout generator emits exactly two asphalt
    // vertices per centreline point and two triangles per segment; verify
    // that contract before allowing the race to start.
    function validRoadModel(model) {
        if (!model || !model.modelData ||
            !Array.isArray(model.modelData.meshes) ||
            !model.children) return false;
        var n=route.points.length, surface=null, i;
        for (i=0;i<model.modelData.meshes.length;i++) {
            if (model.modelData.meshes[i].name==='race-asphalt') {
                // A duplicate road strip may render far from the collider,
                // even when the first strip is completely valid.
                if (surface) return false;
                surface=model.modelData.meshes[i];
            }
        }
        if (!surface || !Array.isArray(model.modelData.materials))
            return false;
        var asphaltMaterial=model.modelData.materials[surface.material];
        // The generated asphalt must remain visible. A structurally valid
        // transparent material can hide the only driveable surface.
        if (!asphaltMaterial || asphaltMaterial.name!=='road' ||
            !!asphaltMaterial.transparent ||
            (asphaltMaterial.opacity!==undefined &&
             (!validNumber(asphaltMaterial.opacity) ||
              asphaltMaterial.opacity<0.95))) return false;
        if (!Array.isArray(surface.positions) ||
            !Array.isArray(surface.indices) ||
            surface.positions.length!==n*6 ||
            surface.indices.length!==n*6) return false;
        // StaticModelLoader applies mesh.offset *after* constructing local
        // vertices. The generator emits world-space asphalt positions, so
        // even a valid optional offset would displace the visible road
        // while leaving the collision corridor unchanged.
        if (surface.offset &&
            (surface.offset[0]!==0 || surface.offset[1]!==0 ||
             surface.offset[2]!==0)) return false;
        // Check every centreline point (650 for the current OSM loop).
        // This is cheap compared with building r50 geometry, and prevents
        // a single damaged corner from passing a sparse sample check.
        for (i=0;i<n;i++) {
            if (!surfacePointMatches(i)) return false;
            // Two triangles must connect this cross-section to the next
            // one, including the final wraparound. Merely checking face
            // counts accepts corrupt, in-range indices that draw giant
            // triangles through the city while physics follows the road.
            var a=i*2, b=((i+1)%n)*2, j=i*6;
            var expected=[a,a+1,b,a+1,b+1,b];
            for (var t=0;t<6;t++)
                if (surface.indices[j+t]!==expected[t]) return false;
        }
        var renderedAsphalt=0;
        for (i=0;i<model.children.length;i++) {
            var child=model.children[i];
            if (child.name==='race-asphalt') {
                renderedAsphalt++;
                if (!child.geometry || !child.geometry.faces ||
                    child.geometry.faces.length!==n*2) return false;
            }
        }
        return renderedAsphalt===1;

        function surfacePointMatches(index) {
            var offset=index*6,p=surface.positions;
            var center=route.points[index];
            var prev=route.points[(index+n-1)%n];
            var next=route.points[(index+1)%n];
            var tx=next[0]-prev[0],tz=next[1]-prev[1];
            var tangentLength=Math.sqrt(tx*tx+tz*tz);
            if (tangentLength<1e-8) return false;
            // Midpoint and width alone cannot detect a reversed or rotated
            // cross-section: both produce torn/inverted triangles with
            // correct index topology. Match the generator's two edges.
            var nx=-tz/tangentLength,nz=tx/tangentLength;
            var halfWidth=route.road_width_m*0.5;
            var tolerance=0.35;
            return Math.abs(p[offset]-(center[0]-nx*halfWidth))<=tolerance &&
                   Math.abs(p[offset+2]-(center[1]-nz*halfWidth))<=tolerance &&
                   Math.abs(p[offset+3]-(center[0]+nx*halfWidth))<=tolerance &&
                   Math.abs(p[offset+5]-(center[1]+nz*halfWidth))<=tolerance &&
                   // The current blockout has flat asphalt at +0.08m.
                   // Large vertical offsets would leave a floating road.
                   Math.abs(p[offset+1]-0.08)<=0.25 &&
                   Math.abs(p[offset+4]-0.08)<=0.25;
        }
    }

    track.load = function(opts, quality) {
        var self = this;
        function fallback(error) {
            console.warn('Moat road unavailable: using Cityscape', error);
            self.moatMode = false;
            self.name = original.name;
            self.trackScale = original.trackScale;
            self.pixelRatio = original.pixelRatio;
            self.spawn = original.spawn;
            self.spawnRotation = original.spawnRotation;
            self.checkpoints = original.checkpoints;
            self.analyser = null;
            self.flatHeight = null;
            self.roadModel = null;
            original.load.call(self, opts, quality);
        }
        // First verify the M2 road asset, then load the minimum legacy
        // resources. If the road is unavailable, load the FULL Cityscape
        // resources before invoking onLoad; no half-initialized fallback.
        THREE.StaticModelLoader.load(
            'assets/tracks/chiangmai-moat/road.json',
            function(road) {
                if (!validRoadModel(road)) {
                    fallback(new Error('OSM asphalt geometry does not match route'));
                    return;
                }
                self.roadModel = road;
                self.lib = new bkcore.threejs.Loader(opts);
                self.lib.load(resources(quality));
            },
            fallback
        );
    };

    bkcore.hexgl.tracks.ChiangMaiMoat = track;
})();
