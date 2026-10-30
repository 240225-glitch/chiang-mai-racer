/*
 * HexGL
 * @author Thibaut 'BKcore' Despoulain <http://bkcore.com>
 * @license This work is licensed under the Creative Commons Attribution-NonCommercial 3.0 Unported License.
 *          To view a copy of this license, visit http://creativecommons.org/licenses/by-nc/3.0/.
 */

var bkcore = bkcore || {};
bkcore.hexgl = bkcore.hexgl || {};
bkcore.hexgl.tracks = bkcore.hexgl.tracks || {};

bkcore.hexgl.tracks.Cityscape = {

	lib: null,
	materials: {},

	name: "Cityscape",

	// The original city loop is enlarged on the ground plane. Only X/Z are
	// scaled so the original height map stays valid; the collision/height
	// sampling ratios below are divided by the same factor.
	trackScale: 1.5,

	checkpoints: {
		list: [0,1,2],
		start: 0,
		last: 2
	},

	spawn: {
		x: -1134*3,
		y: 387,
		z: -443*3
	},

	spawnRotation: {
		x: 0,
		y: 0,
		z: 0
	},

	analyser: null,
	pixelRatio: (2048.0 / 6000.0) / 1.5,

	load: function(opts, quality)
	{
		this.lib = new bkcore.threejs.Loader(opts);

		// desktop + quality low
		// OR
		// mobile + quality low or mid
		if(quality < 2) // LOW
		{
			this.lib.load({
				textures: {
					'hex'								: "textures/hud/hex.jpg",
					'spark'								: "textures/particles/spark.png",
					'cloud'								: "textures/particles/cloud.png",
					'ship.feisar.diffuse'				: "textures/ships/feisar/diffuse.jpg",
					'booster.diffuse'					: "textures/ships/feisar/booster/booster.png",
					'booster.sprite'					: "textures/ships/feisar/booster/boostersprite.jpg",
					'track.cityscape.diffuse'			: "textures/tracks/cityscape/diffuse.jpg",
					'track.cityscape.start.diffuse'		: "textures/tracks/cityscape/start/diffuse.jpg",
					'track.cityscape.start.banner'		: "textures/tracks/cityscape/start/start.jpg",
					'bonus.base.diffuse'				: "textures/bonus/base/diffuse.jpg"
				},
				texturesCube: {
					'skybox.dawnclouds'					: "textures/skybox/dawnclouds/%1.jpg"
				},
				geometries: {
					'bonus.base'						: "geometries/bonus/base/base.js",
					'booster'							: "geometries/booster/booster.js",
					'ship.feisar'						: "geometries/ships/feisar/feisar.js",
					'track.cityscape'					: "geometries/tracks/cityscape/track.js",
					'track.cityscape.start'				: "geometries/tracks/cityscape/start.js",
					'track.cityscape.start.banner'		: "geometries/tracks/cityscape/startbanner.js",
					'track.cityscape.bonus.speed'		: "geometries/tracks/cityscape/bonus/speed.js"
				},
				analysers: {
					'track.cityscape.collision'			: "textures/tracks/cityscape/collision.png",
					'track.cityscape.height'			: "textures/tracks/cityscape/height.png"
				},
				images: {
					'hud.bg'							: "textures/hud/hud-bg.png",
					'hud.speed'							: "textures/hud/hud-fg-speed.png",
					'hud.shield'						: "textures/hud/hud-fg-shield.png"
				},
				sounds: {
					bg: {
						src: 'audio/bg.ogg',
						loop: true,
						usePanner: false
					},
					crash: {
						src: 'audio/crash.ogg',
						loop: false,
						usePanner: true
					},
					destroyed: {
						src: 'audio/destroyed.ogg',
						loop: false,
						usePanner: false
					},
					boost: {
						src: 'audio/boost.ogg',
						loop: false,
						usePanner: true
					},
					wind: {
						src: 'audio/wind.ogg',
						loop: true,
						usePanner: true
					}
				}
			});
		}
		// desktop + quality mid or high
		// OR
		// mobile + quality high
		else // HIGH
		{console.log('HIGH');
			this.lib.load({
				textures: {
					'hex'								: "textures.full/hud/hex.jpg",
					'spark'								: "textures.full/particles/spark.png",
					'cloud'								: "textures.full/particles/cloud.png",
					'ship.feisar.diffuse'				: "textures.full/ships/feisar/diffuse.jpg",
					'ship.feisar.specular'				: "textures.full/ships/feisar/specular.jpg",
					'ship.feisar.normal'				: "textures.full/ships/feisar/normal.jpg",
					'booster.diffuse'					: "textures.full/ships/feisar/booster/booster.png",
					'booster.sprite'					: "textures.full/ships/feisar/booster/boostersprite.jpg",
					'track.cityscape.diffuse'			: "textures.full/tracks/cityscape/diffuse.jpg",
					'track.cityscape.specular'			: "textures.full/tracks/cityscape/specular.jpg",
					'track.cityscape.normal'			: "textures.full/tracks/cityscape/normal.jpg",
					'track.cityscape.start.diffuse'		: "textures.full/tracks/cityscape/start/diffuse.jpg",
					'track.cityscape.start.specular'	: "textures.full/tracks/cityscape/start/specular.jpg",
					'track.cityscape.start.normal'		: "textures.full/tracks/cityscape/start/normal.jpg",
					'track.cityscape.start.banner'		: "textures.full/tracks/cityscape/start/start.jpg",
					'bonus.base.diffuse'				: "textures.full/bonus/base/diffuse.jpg",
					'bonus.base.normal'					: "textures.full/bonus/base/normal.jpg",
					'bonus.base.specular'				: "textures.full/bonus/base/specular.jpg"
				},
				texturesCube: {
					'skybox.dawnclouds'					: "textures.full/skybox/dawnclouds/%1.jpg"
				},
				geometries: {
					'bonus.base'						: "geometries/bonus/base/base.js",
					'booster'							: "geometries/booster/booster.js",
					'ship.feisar'						: "geometries/ships/feisar/feisar.js",
					'track.cityscape'					: "geometries/tracks/cityscape/track.js",
					'track.cityscape.start'				: "geometries/tracks/cityscape/start.js",
					'track.cityscape.start.banner'		: "geometries/tracks/cityscape/startbanner.js",
					'track.cityscape.bonus.speed'		: "geometries/tracks/cityscape/bonus/speed.js"
				},
				analysers: {
					'track.cityscape.collision'			: "textures.full/tracks/cityscape/collision.png",
					'track.cityscape.height'			: "textures.full/tracks/cityscape/height.png"
				},
				images: {
					'hud.bg'							: "textures.full/hud/hud-bg.png",
					'hud.speed'							: "textures.full/hud/hud-fg-speed.png",
					'hud.shield'						: "textures.full/hud/hud-fg-shield.png"
				},
				sounds: {
					bg: {
						src: 'audio/bg.ogg',
						loop: true
					},
					crash: {
						src: 'audio/crash.ogg',
						loop: false
					},
					destroyed: {
						src: 'audio/destroyed.ogg',
						loop: false
					},
					boost: {
						src: 'audio/boost.ogg',
						loop: false
					},
					wind: {
						src: 'audio/wind.ogg',
						loop: true
					}
				}
			});
		}
	},

	buildMaterials: function(quality)
	{
		// desktop + quality low
		// OR
		// mobile + quality low or mid
		if(quality < 2) // LOW
		{
			this.materials.track = new THREE.MeshBasicMaterial({
				map: this.lib.get("textures", "track.cityscape.diffuse"),
				ambient: 0xcccccc
			});

			this.materials.bonusBase = new THREE.MeshBasicMaterial({
				map: this.lib.get("textures", "bonus.base.diffuse"),
				ambient: 0xcccccc
			});

			this.materials.bonusSpeed = new THREE.MeshBasicMaterial({
				color: 0x0096ff
			});

			this.materials.ship = new THREE.MeshBasicMaterial({
				map: this.lib.get("textures", "ship.feisar.diffuse"),
				ambient: 0xaaaaaa
			});

			this.materials.booster = new THREE.MeshBasicMaterial({
				map: this.lib.get("textures", "booster.diffuse"),
				transparent: true
			});

			this.materials.start = new THREE.MeshBasicMaterial({
				map: this.lib.get("textures", "track.cityscape.start.diffuse"),
				ambient: 0xcccccc
			});

			this.materials.startBanner = new THREE.MeshBasicMaterial({
				map: this.lib.get("textures", "track.cityscape.start.banner"),
				transparent: false
			});
		}
		// desktop + quality mid or high
		// OR
		// mobile + quality high
		else // HIGH
		{
			this.materials.track = bkcore.Utils.createNormalMaterial({
				diffuse: this.lib.get("textures", "track.cityscape.diffuse"),
				specular: this.lib.get("textures", "track.cityscape.specular"),
				normal: this.lib.get("textures", "track.cityscape.normal"),
				ambient: 0xffffff,
				shininess: 42,
				metal: true,
				perPixel: true
			});

			this.materials.bonusBase = bkcore.Utils.createNormalMaterial({
				diffuse: this.lib.get("textures", "bonus.base.diffuse"),
				specular: this.lib.get("textures", "bonus.base.specular"),
				normal: this.lib.get("textures", "bonus.base.normal"),
				normalScale: 3.0,
				ambient: 0x444444,
				shininess: 42,
				metal: false,
				perPixel: false
			});

			this.materials.bonusSpeed = new THREE.MeshBasicMaterial({
				color: 0x0096ff
			});

			this.materials.ship = bkcore.Utils.createNormalMaterial({
				diffuse: this.lib.get("textures", "ship.feisar.diffuse"),
				specular: this.lib.get("textures", "ship.feisar.specular"),
				normal: this.lib.get("textures", "ship.feisar.normal"),
				ambient: 0x444444,
				shininess: 42,
				metal: true,
				perPixel: false
			});

			this.materials.booster = new THREE.MeshBasicMaterial({
				map: this.lib.get("textures", "booster.diffuse"),
				transparent: true
			});

			this.materials.start = bkcore.Utils.createNormalMaterial({
				diffuse: this.lib.get("textures", "track.cityscape.start.diffuse"),
				specular: this.lib.get("textures", "track.cityscape.start.specular"),
				normal: this.lib.get("textures", "track.cityscape.start.normal"),
				ambient: 0xaaaaaa,
				shininess: 42,
				metal: false,
				perPixel: false
			});

			this.materials.startBanner = new THREE.MeshBasicMaterial({
				map: this.lib.get("textures", "track.cityscape.start.banner"),
				transparent: false
			});
		}

		// Visible checkpoint markers (the gameplay trigger itself is still
		// painted into the collision analyser, like the original game).
		this.materials.checkpoint = new THREE.MeshBasicMaterial({
			color: 0xffd84a,
			transparent: true,
			opacity: 0.85,
			blending: THREE.AdditiveBlending,
			depthWrite: false
		});
	},

	buildScenes: function(ctx, quality)
	{
		var self = this;
		var S = this.trackScale;

		// IMPORTANT
		this.analyser = this.lib.get("analysers", "track.cityscape.collision");

		// SKYBOX
		var sceneCube = new THREE.Scene();

		var viewAspect = (ctx.twoPlayer ? ctx.width / 2 : ctx.width) / ctx.height;
		var cameraCube = new THREE.PerspectiveCamera( 70, viewAspect, 1, 6000 );
		sceneCube.add( cameraCube );

		var cameraCube2 = null;
		if(ctx.twoPlayer)
		{
			cameraCube2 = new THREE.PerspectiveCamera( 70, viewAspect, 1, 6000 );
			sceneCube.add( cameraCube2 );
		}

		var skyshader = THREE.ShaderUtils.lib[ "cube" ];
		skyshader.uniforms[ "tCube" ].texture = this.lib.get("texturesCube", "skybox.dawnclouds");

		var skymaterial = new THREE.ShaderMaterial(
		{
			fragmentShader: skyshader.fragmentShader,
			vertexShader: skyshader.vertexShader,
			uniforms: skyshader.uniforms,
			depthWrite: false
		});

		var mesh = new THREE.Mesh( new THREE.CubeGeometry( 100, 100, 100 ), skymaterial );
		mesh.flipSided = true;

		sceneCube.add(mesh);

		ctx.manager.add("sky", sceneCube, cameraCube);

		var ambient = 0xbbbbbb, diffuse = 0xffffff, specular = 0xffffff, shininess = 42, scale = 23;

		// MAIN SCENE
		var camera = new THREE.PerspectiveCamera( ctx.twoPlayer ? 78 : 70, viewAspect, 1, 60000 );
		var camera2 = ctx.twoPlayer ? new THREE.PerspectiveCamera( 78, viewAspect, 1, 60000 ) : null;

		var scene = new THREE.Scene();
		scene.add( camera );
		if(camera2) scene.add( camera2 );
		scene.add( new THREE.AmbientLight( ambient ) );

		// SUN
		var sun = new THREE.DirectionalLight( diffuse, 1.5, 30000 );
		sun.position.set( -4000, 1200, 1800 );
		sun.lookAt(new THREE.Vector3());

		// desktop + quality mid or high
		// Shadows are disabled in split-screen to keep two scene renders fast.
		if(quality > 2 && !ctx.twoPlayer)
		{
			sun.castShadow = true;
			sun.shadowCameraNear = 50;
			sun.shadowCameraFar = camera.far*2;
			sun.shadowCameraRight     =  5000;
			sun.shadowCameraLeft      = -5000;
			sun.shadowCameraTop       =  5000;
			sun.shadowCameraBottom    = -5000;
			//sun.shadowCameraVisible = true;
			sun.shadowBias = 0.0001;
			sun.shadowDarkness = 0.7;
			sun.shadowMapWidth = 2048;
			sun.shadowMapHeight = 2048;
		}
		scene.add( sun );

		// SHIPS (one for solo, two side-by-side ships for split-screen)
		var sideOffset = 22 * S;
		var spawns = [{x: this.spawn.x, y: this.spawn.y, z: this.spawn.z}];
		if(ctx.twoPlayer)
		{
			spawns = [
				{x: this.spawn.x - sideOffset, y: this.spawn.y, z: this.spawn.z},
				{x: this.spawn.x + sideOffset, y: this.spawn.y, z: this.spawn.z}
			];
		}
		ctx.components.spawns = spawns;

		function createShip(position)
		{
			var ship = ctx.createMesh(scene, self.lib.get("geometries", "ship.feisar"), position.x, 10, position.z, self.materials.ship);

			var booster = ctx.createMesh(ship, self.lib.get("geometries", "booster"), 0, 0.665, -3.8, self.materials.booster);
			booster.depthWrite = false;

			var boosterSprite = new THREE.Sprite({
				map: self.lib.get("textures", "booster.sprite"),
				blending: THREE.AdditiveBlending,
				useScreenCoordinates: false,
				color: 0xffffff
			});
			boosterSprite.scale.set(0.02, 0.02, 0.02);
			boosterSprite.mergeWith3D = false;
			booster.add(boosterSprite);

			var boosterLight = new THREE.PointLight(0x00a2ff, 4.0, 60);
			boosterLight.position.set(0, 0.665, -4);

			// desktop + quality low, mid or high
			// OR
			// mobile + quality mid or high
			if(quality > 0)
				ship.add(boosterLight);

			return {ship: ship, booster: booster, boosterSprite: boosterSprite, boosterLight: boosterLight};
		}

		var shipObjects = [createShip(spawns[0])];
		if(ctx.twoPlayer) shipObjects.push(createShip(spawns[1]));

		// SHIP CONTROLS
		function createShipControls(ship, customControls)
		{
			var controlContext = ctx;
			if(customControls)
			{
				controlContext = {
					document: ctx.document,
					width: ctx.width,
					controlType: 0,
					restart: function(){ ctx.restart(); },
					controls: customControls
				};
			}

			var shipControls = new bkcore.hexgl.ShipControls(controlContext);
			shipControls.collisionMap = self.lib.get("analysers", "track.cityscape.collision");
			shipControls.collisionPixelRatio = self.pixelRatio;
			shipControls.collisionDetection = true;
			shipControls.heightMap = self.lib.get("analysers", "track.cityscape.height");
			shipControls.heightPixelRatio = self.pixelRatio;
			shipControls.heightBias = 4.0;
			shipControls.heightScale = 10.0;
			shipControls.control(ship);
			return shipControls;
		}

		var p1Controls = ctx.twoPlayer ? {
			forward: [87],   // W
			backward: [83],  // S
			left: [65],      // A
			right: [68],     // D
			ltrigger: [81],  // Q
			rtrigger: [69],  // E
			nitro: [16]      // Left Shift
		} : null;

		var p2Controls = {
			forward: [38],   // Arrow up
			backward: [40],  // Arrow down
			left: [37],      // Arrow left
			right: [39],     // Arrow right
			ltrigger: [],
			rtrigger: [],
			nitro: [32]      // Space
		};

		var controls = [createShipControls(shipObjects[0].ship, p1Controls)];
		if(ctx.twoPlayer) controls.push(createShipControls(shipObjects[1].ship, p2Controls));

		ctx.components.shipControls = controls[0];
		if(ctx.twoPlayer) ctx.components.shipControls2 = controls[1];
		ctx.tweakShipControls();

		// SHIP EFFECTS AND PARTICLES
		function createShipEffects(shipObject, shipControls)
		{
			var fxParams = {
				scene: scene,
				shipControls: shipControls,
				booster: shipObject.booster,
				boosterSprite: shipObject.boosterSprite,
				boosterLight: shipObject.boosterLight,
				useParticles: false
			};

			// desktop + quality mid or high
			if(quality > 2)
			{
				fxParams.textureCloud = self.lib.get("textures", "cloud");
				fxParams.textureSpark = self.lib.get("textures", "spark");
				fxParams.useParticles = true;
			}

			return new bkcore.hexgl.ShipEffects(fxParams);
		}

		var effects = [createShipEffects(shipObjects[0], controls[0])];
		if(ctx.twoPlayer) effects.push(createShipEffects(shipObjects[1], controls[1]));

		ctx.components.shipEffects = effects[0];
		if(ctx.twoPlayer) ctx.components.shipEffects2 = effects[1];

		// TRACK
		// Keep the racing ribbon, start gate and boost pads; the city
		// skyscrapers are intentionally left out so the enlarged track
		// floats in the open sky with only checkpoints as landmarks.
		function createTrackMesh(geometryName, material)
		{
			var mesh = ctx.createMesh(scene, self.lib.get("geometries", geometryName), 0, -5, 0, material);
			mesh.scale.set(S, 1, S);
			return mesh;
		}

		var track = createTrackMesh("track.cityscape", this.materials.track);
		var bonusBase = createTrackMesh("bonus.base", this.materials.bonusBase);
		var bonusSpeed = createTrackMesh("track.cityscape.bonus.speed", this.materials.bonusSpeed);
		bonusSpeed.receiveShadow = false;
		var start = createTrackMesh("track.cityscape.start", this.materials.start);
		var startbanner = createTrackMesh("track.cityscape.start.banner", this.materials.startBanner);
		startbanner.doubleSided = true;

		// Visible checkpoint gates. Positions come from the yellow pixels in
		// the original collision map (checkpoints 0, 1 and 2). Each gate is
		// a vertical ring facing the approximate track direction, so it reads
		// as a gate instead of a giant disc lying on the road.
		// yaw is the local track heading at each gate, measured from the
		// collision map around the checkpoint (the yellow stripe marks the
		// gate line, so its perpendicular is the approach direction). Using
		// the next-minus-previous checkpoint chord would point across the
		// whole map instead of along the local straight.
		var checkpointData = [
			{x: -2264.65, y: 387, z: -610.84, yaw: 0.8},
			{x: 1505.86, y: 753, z: 607.91, yaw: -0.7},
			{x: 2253.60, y: 326, z: 823.43, yaw: -4.8}
		];
		for(var cp = 0; cp < checkpointData.length; cp++)
		{
			var ring = new THREE.Mesh(
				new THREE.TorusGeometry(55, 3, 8, 48),
				this.materials.checkpoint
			);
			ring.position.set(checkpointData[cp].x * S, checkpointData[cp].y + 56, checkpointData[cp].z * S);
			ring.rotation.y = checkpointData[cp].yaw * Math.PI / 180;
			scene.add(ring);
		}

		// CAMERA
		var cameraChase = new bkcore.hexgl.CameraChase({
			target: shipObjects[0].ship,
			camera: camera,
			cameraCube: cameraCube,
			lerp: 0.5,
			yoffset: 8.0,
			zoffset: 10.0,
			viewOffset: 10.0
		});
		ctx.components.cameraChase = cameraChase;

		var cameraChase2 = null;
		if(ctx.twoPlayer)
		{
			cameraChase2 = new bkcore.hexgl.CameraChase({
				target: shipObjects[1].ship,
				camera: camera2,
				cameraCube: cameraCube2,
				lerp: 0.5,
				yoffset: 8.0,
				zoffset: 10.0,
				viewOffset: 10.0
			});
			ctx.components.cameraChase2 = cameraChase2;
		}

		var doc = ctx.document;
		var nitroPanels = [
			{
				fill: doc.getElementById('nitro-fill'),
				state: doc.getElementById('nitro-state'),
				panel: doc.getElementById('nitro-panel'),
				vignette: doc.getElementById('boost-vignette')
			},
			{
				fill: doc.getElementById('nitro-fill-p2'),
				state: doc.getElementById('nitro-state-p2'),
				panel: doc.getElementById('nitro-panel-p2'),
				vignette: doc.getElementById('boost-vignette-p2')
			}
		];

		if(ctx.twoPlayer)
		{
			var key1 = doc.querySelector('#nitro-panel .nitro-key');
			var key2 = doc.querySelector('#nitro-panel-p2 .nitro-key');
			if(key1) key1.innerHTML = '左 Shift 释放 · 红色加速带补充';
			if(key2) key2.innerHTML = '空格 释放 · 红色加速带补充';
		}

		var huds = ctx.huds && ctx.huds.length > 0 ? ctx.huds : [ctx.hud];
		var players = [
			{
				ship: shipObjects[0].ship,
				controls: controls[0],
				effects: effects[0],
				chase: cameraChase,
				camera: camera,
				skyCamera: cameraCube,
				hud: huds[0] || null,
				nitro: nitroPanels[0]
			}
		];

		if(ctx.twoPlayer)
		{
			players.push({
				ship: shipObjects[1].ship,
				controls: controls[1],
				effects: effects[1],
				chase: cameraChase2,
				camera: camera2,
				skyCamera: cameraCube2,
				hud: huds[1] || null,
				nitro: nitroPanels[1]
			});
		}

		function updateNitroUI(ui, shipControls)
		{
			if(!ui) return;

			var nitroRatio = shipControls.getNitroRatio();
			var nitroStatus = shipControls.getNitroState();

			if(ui.fill)
				ui.fill.style.width = (nitroRatio * 100).toFixed(1) + '%';

			if(ui.state && ui.state.getAttribute('data-state') !== nitroStatus)
			{
				ui.state.setAttribute('data-state', nitroStatus);
				ui.state.innerHTML = nitroStatus == 'active' ? '推进中' : (nitroStatus == 'ready' ? '就绪' : '充能中');
			}

			if(ui.panel && ui.panel.getAttribute('data-state') !== nitroStatus)
			{
				ui.panel.setAttribute('data-state', nitroStatus);
				ui.panel.className = nitroStatus == 'ready' ? 'ready' : '';
			}

			if(ui.vignette)
			{
				var boosting = shipControls.nitroActive > 0;
				if(ui.vignette.getAttribute('data-active') !== String(boosting))
				{
					ui.vignette.setAttribute('data-active', String(boosting));
					ui.vignette.className = boosting ? 'active' : '';
				}
			}
		}

		// Two viewports, one per player, drawn directly with the WebGL
		// renderer. The full-screen EffectComposer is reserved for solo mode.
		function renderSplit(renderer, objects)
		{
			var width = ctx.width;
			var height = ctx.height;
			var half = Math.floor(width / 2);

			renderer.autoClear = false;
			renderer.enableScissorTest(true);

			for(var i = 0; i < objects.players.length; i++)
			{
				var viewX = i === 0 ? 0 : half;
				var viewW = i === 0 ? half : width - half;
				var player = objects.players[i];

				renderer.setViewport(viewX, 0, viewW, height);
				renderer.setScissor(viewX, 0, viewW, height);
				renderer.clear(true, true, true);

				if(player.skyCamera)
					renderer.render(objects.skyScene, player.skyCamera);
				renderer.render(objects.scene, player.camera);
			}

			renderer.enableScissorTest(false);
			renderer.setViewport(0, 0, width, height);
		}

		ctx.manager.add("game", scene, camera, function(delta, renderer)
		{
			if(delta > 25 && this.objects.lowFPS < 1000) this.objects.lowFPS++;

			var dt = delta / 16.6;
			var objects = this.objects;
			var activePlayers = objects.players;

			for(var i = 0; i < activePlayers.length; i++)
			{
				var p = activePlayers[i];
				p.controls.update(dt);
				p.effects.update(dt);
				p.chase.update(dt, p.controls.getSpeedRatio());
			}

			if(ctx.twoPlayer)
				renderSplit(renderer, objects);
			else
				objects.composers.game.render(dt);

			for(var j = 0; j < activePlayers.length; j++)
			{
				var player = activePlayers[j];
				var shipControls = player.controls;

				if(player.hud) player.hud.update(
					shipControls.getRealSpeed(100),
					shipControls.getRealSpeedRatio(),
					shipControls.getShield(100),
					shipControls.getShieldRatio()
				);

				updateNitroUI(player.nitro, shipControls);
			}

			if(!ctx.twoPlayer)
			{
				var soloControls = activePlayers[0].controls;
				if(soloControls.getShieldRatio() < 0.2)
					objects.extras.vignetteColor.setHex(0x992020);
				else
					objects.extras.vignetteColor.setHex(0x458ab1);
			}
		},
		{
			components: ctx.components,
			composers: ctx.composers,
			extras: ctx.extras,
			quality: quality,
			hud: ctx.hud,
			huds: ctx.huds,
			players: players,
			scene: scene,
			skyScene: sceneCube,
			time: 0.0,
			lowFPS: 0
		});
	}
}
