/*!
 * @class bkcore.threejs.Loader
 *
 * Loads multiple recources, get progress, callback friendly.
 * Supports textures, texturesCube, geometries, analysers, images.
 * 
 * @author Thibaut 'BKcore' Despoulain <http://bkcore.com>
 */

/*!
 * @package bkcore.threejs
 */
var bkcore = bkcore || {};
bkcore.threejs = bkcore.threejs || {};

bkcore.NONE = undefined;

/**
 * Creates a new loader
 * @param {Object{onLoad, onError, onProgress}} opts Callbacks
 */
bkcore.threejs.Loader = function(opts)
{
	var self = this;

	this.jsonLoader = new THREE.JSONLoader();

	this.errorCallback = opts.onError == undefined ? function(s){ console.warn("Error while loading %s.".replace("%s", s)) } : opts.onError;
	this.loadCallback = opts.onLoad == undefined ? function(){ console.log("Loaded.") } : opts.onLoad;
	this.fatalCallback = opts.onFatal == undefined ? function(){} : opts.onFatal;
	this.progressCallback = opts.onProgress == undefined ? function(progress, type, name){ /**/ } : opts.onProgress;

	this.types = {
		textures: null,
		texturesCube: null,
		geometries: null,
		analysers: null,
		images: null,
		sounds: null
	};

	this.states = {};
	this.data = {};
	// A track may mark its indispensable road geometry as required.
	// Optional props still use an empty r50 Geometry on failure.
	this.requiredGeometries = {};

	for(var t in this.types)
	{
		this.data[t] = {};
		this.states[t] = {};
	}

	this.progress = {
		total: 0,
		remaining: 0,
		loaded: 0,
		finished: false,
		failed: false,
		failures: []
	};
}

/**
 * Load the given list of resources
 * @param  {textures, texturesCube, geometries, analysers, images} data 
 */
bkcore.threejs.Loader.prototype.load = function(data)
{
	var self = this;
	this.requiredGeometries = data.requiredGeometries || {};

	for(var k in this.types)
	{
		if(k in data)
		{
			var size = 0;
			for(var j in data[k])
				size++;
			this.progress.total += size;
			this.progress.remaining += size;
		}
	}

	for(var t in data.textures)
		this.loadTexture(t, data.textures[t]);

	for(var c in data.texturesCube)
		this.loadTextureCube(c, data.texturesCube[c]);

	for(var g in data.geometries)
		this.loadGeometry(g, data.geometries[g]);

	for(var a in data.analysers)
		this.loadAnalyser(a, data.analysers[a]);

	for(var i in data.images)
		this.loadImage(i, data.images[i]);

	for(var s in data.sounds)
		this.loadSound(data.sounds[s].src, s, data.sounds[s].loop, data.sounds[s].usePanner);

	this.progressCallback.call(this, this.progress);
}

bkcore.threejs.Loader.prototype.updateState = function(type, name, state)
{
	if(!(type in this.types))
	{
		console.warn("Unkown loader type.");
		return;
	}

	// An image error and a late load event (or repeated callbacks) must
	// never over-count resources or fire the game-ready callback twice.
	if(state === true && this.states[type][name] === true) return;
	this.states[type][name] = state;
	if(state === true)
	{
		this.progress.remaining--;
		this.progress.loaded++;
		this.progressCallback.call(this, this.progress, type, name);
	}
	if(!this.progress.finished && this.progress.total > 0 &&
		this.progress.loaded === this.progress.total)
	{
		this.progress.finished = true;
		// Collision/height analysers are mandatory for Cityscape physics.
		if(!this.progress.failed) this.loadCallback.call(this);
	}
}

/**
 * Get loaded resource
 * @param  string type [textures, texturesCube, geometries, analysers, images]
 * @param  string name 
 * @return Mixed
 */
bkcore.threejs.Loader.prototype.get = function(type, name)
{
	if(!(type in this.types))
	{
		console.warn("Unkown loader type.");
		return null;
	}
	if(!(name in this.data[type]))
	{
		console.warn("Unkown file.");
		return null;
	}

	return this.data[type][name];
}

bkcore.threejs.Loader.prototype.loaded = function(type, name)
{
	if(!(type in this.types))
	{
		console.warn("Unkown loader type.");
		return null;
	}
	if(!(name in this.states[type]))
	{
		console.warn("Unkown file.");
		return null;
	}

	return this.states[type][name];
}

// The old HUD requires drawable images even when an optional asset is 404.
// Use a tiny, transparent canvas with the HUD's 1920:250 aspect ratio.
// A missing material texture uses opaque white pixels, not a broken image.
bkcore.threejs.Loader.prototype.fallbackCanvas = function(hud)
{
	var canvas = document.createElement('canvas');
	canvas.width = hud ? 192 : 2;
	canvas.height = hud ? 25 : 2;
	if(!hud)
	{
		var ctx = canvas.getContext('2d');
		ctx.fillStyle = '#ffffff';
		ctx.fillRect(0, 0, 2, 2);
	}
	return canvas;
}

bkcore.threejs.Loader.prototype.loadTexture = function(name, url)
{
	var self = this;
	var completed = false;
	var timer = null;
	this.updateState("textures", name, false);
	function finish(failed)
	{
		if(completed) return;
		completed = true;
		if(timer !== null) clearTimeout(timer);
		if(failed)
		{
			self.errorCallback.call(self, name);
			// A stalled image may never emit onerror. Keep the material
			// drawable and allow the rest of the game to initialize.
			var texture = self.data.textures[name];
			if(!texture) texture = self.data.textures[name] = new THREE.Texture();
			texture.image = self.fallbackCanvas(false);
			texture.needsUpdate = true;
		}
		self.updateState("textures", name, true);
	}
	timer = setTimeout(function(){ finish(true); }, 15000);
	try
	{
		this.data.textures[name] = THREE.ImageUtils.loadTexture(
			url, bkcore.NONE,
			function(){ finish(false); },
			function(){ finish(true); }
		);
	}
	catch(e) { finish(true); }
}

bkcore.threejs.Loader.prototype.loadTextureCube = function(name, url)
{
	var self = this;
	var faces = ["px", "nx", "py", "ny", "pz", "nz"];
	var images = [];
	// r50 ImageUtils.loadTextureCube only installs onload handlers; a single
	// 404 leaves its six-face completion callback pending forever. Build the
	// same r50 Texture directly so every face has an error/timeout path.
	var texture = new THREE.Texture(images, new THREE.CubeRefractionMapping());
	texture.flipY = false;
	this.updateState("texturesCube", name, false);
	this.data.texturesCube[name] = texture;
	var completed = false;
	var count = 0;
	var timer = null;
	function finish(failed)
	{
		if(completed) return;
		completed = true;
		if(timer !== null) clearTimeout(timer);
		if(failed)
		{
			self.errorCallback.call(self, name);
			// WebGL requires all six cube faces to have matching dimensions.
			// Do not mix a 2x2 fallback with real (larger) skybox images.
			for(var i = 0; i < 6; i++)
				images[i] = self.fallbackCanvas(false);
		}
		texture.needsUpdate = true;
		self.updateState("texturesCube", name, true);
	}
	timer = setTimeout(function(){ finish(true); }, 15000);
	for(var i = 0; i < faces.length; i++)
	{
		var img = new Image();
		images[i] = img;
		img.onload = function()
		{
			if(completed) return;
			count++;
			if(count === 6) finish(false);
		};
		img.onerror = function(){ finish(true); };
		img.crossOrigin = THREE.ImageUtils.crossOrigin || "anonymous";
		try { img.src = url.replace("%1", faces[i]); }
		catch(e) { finish(true); }
		if(completed) break;
	}
}

// r50 JSONLoader.load() has no HTTP error callback: 404, empty responses,
// malformed JSON and stalled requests otherwise leave the loading screen up.
// Keep the same JSONLoader.createModel() conversion on success, but own the
// request lifecycle so each geometry completes exactly once.
bkcore.threejs.Loader.prototype.loadGeometry = function(name, url)
{
	var self = this;
	var done = false;
	var timer = null;
	var request = new XMLHttpRequest();
	this.data.geometries[name] = null;
	this.updateState("geometries", name, false);
	function finish(geometry)
	{
		if(done) return;
		done = true;
		if(timer !== null) clearTimeout(timer);
		var required = !!self.requiredGeometries[name];
		var unusable = !geometry || (required &&
			(!geometry.faces || !geometry.faces.length ||
			 !geometry.vertices || !geometry.vertices.length));
		if(unusable)
		{
			self.errorCallback.call(self, name);
			// The Cityscape road is essential for rendering and driving.
			// Do not silently launch with an empty road, even when the HTTP
			// request succeeded but its model contains no triangles.
			if(required)
			{
				self.progress.failures.push(name);
				if(!self.progress.failed)
				{
					self.progress.failed = true;
					self.fatalCallback.call(self, name);
				}
			}
			// Optional models may still degrade to an empty r50 Geometry.
			if(!geometry) geometry = new THREE.Geometry();
		}
		self.data.geometries[name] = geometry;
		self.updateState("geometries", name, true);
	}
	request.onreadystatechange = function()
	{
		if(done || request.readyState !== 4) return;
		if((request.status !== 200 && request.status !== 0) || !request.responseText)
		{
			finish(null);
			return;
		}
		try
		{
			var data = JSON.parse(request.responseText);
			self.jsonLoader.createModel(data, function(geometry){ finish(geometry); },
				self.jsonLoader.extractUrlBase(url));
		}
		catch(e) { finish(null); }
	};
	request.onerror = request.onabort = function(){ finish(null); };
	timer = setTimeout(function(){ finish(null); }, 15000);
	try
	{
		request.open("GET", url, true);
		if(request.overrideMimeType) request.overrideMimeType("text/plain; charset=x-user-defined");
		request.send(null);
	}
	catch(e) { finish(null); }
}

bkcore.threejs.Loader.prototype.loadAnalyser = function(name, url)
{
	var self = this;
	this.updateState("analysers", name, false);
	this.data.analysers[name] = new bkcore.ImageData(
		url,
		function(){
			self.updateState("analysers", name, true);
		},
		function(){
			if(self.states.analysers[name] === true) return;
			self.errorCallback.call(self, name);
			self.progress.failures.push(name);
			if(!self.progress.failed) {
				self.progress.failed = true;
				self.fatalCallback.call(self, name);
			}
			// Drain progress for diagnostics, but never call onLoad after a
			// missing physics map. An all-zero image would disable collision.
			self.updateState("analysers", name, true);
		}
	);
}

bkcore.threejs.Loader.prototype.loadImage = function(name, url)
{
	var self = this;
	var completed = false;
	var timer = null;
	this.updateState("images", name, false);
	var e = new Image();
	this.data.images[name] = e;
	function finish(failed)
	{
		if(completed) return;
		completed = true;
		if(timer !== null) clearTimeout(timer);
		if(failed)
		{
			self.errorCallback.call(self, name);
			self.data.images[name] = self.fallbackCanvas(true);
		}
		self.updateState("images", name, true);
	}
	e.onload = function(){ finish(false); };
	e.onerror = function(){ finish(true); };
	e.crossOrigin = "anonymous";
	timer = setTimeout(function(){ finish(true); }, 15000);
	try { e.src = url; }
	catch(error) { finish(true); }
}

bkcore.threejs.Loader.prototype.loadSound = function(src, name, loop, usePanner){
    var self = this;
    this.updateState("sounds", name, false);
    
    bkcore.Audio.addSound(
    	src,
    	name, 
    	loop, 
    	function(){
       	 self.updateState("sounds", name, true);
        },
        usePanner
    );
    
    this.data.sounds[name] = {
        play: function(){
            bkcore.Audio.play(name);
        },
        stop: function(){
            bkcore.Audio.stop(name);
        },
        volume: function(vol){
            bkcore.Audio.volume(name, vol);
        }
    };
};