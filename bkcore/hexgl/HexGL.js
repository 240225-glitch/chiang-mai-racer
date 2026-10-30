 /*
 * HexGL
 * @author Thibaut 'BKcore' Despoulain <http://bkcore.com>
 * @license This work is licensed under the Creative Commons Attribution-NonCommercial 3.0 Unported License.
 *          To view a copy of this license, visit http://creativecommons.org/licenses/by-nc/3.0/.
 */

'use strict';
'v1.0.1';

var bkcore = bkcore || {};
bkcore.hexgl = bkcore.hexgl || {};

bkcore.hexgl.HexGL = function(opts)
{
	var self = this;

	this.document = opts.document || document;

	this.a = window.location.href;

	this.active = true;
	this.displayHUD = opts.hud == undefined ? true : opts.hud;
	this.width = opts.width == undefined ? window.innerWidth : opts.width;
	this.height = opts.height == undefined ? window.innerHeight : opts.height;
	
	this.difficulty = opts.difficulty == undefined ? 0 : opts.difficulty;
	this.player = opts.player == undefined ? "Anonym" : opts.player;

	this.track = bkcore.hexgl.tracks[ opts.track == undefined ? 'Cityscape' : opts.track ];

	this.mode = opts.mode == undefined ? 'timeattack' : opts.mode;

	// Local split-screen: two ships, two chase cameras and two HUDs share
	// the same scene. Reuses the original ShipControls/CameraChase/Gameplay
	// components twice instead of introducing a second engine.
	this.twoPlayer = opts.twoPlayer == undefined ? false : opts.twoPlayer;

	this.controlType = opts.controlType == undefined ? 1 : opts.controlType;
	
	// 0 == low, 1 == mid, 2 == high, 3 == very high
	// the old platform+quality combinations map to these new quality values
	// as follows:
	// mobile + low quality => 0 (LOW)
	// mobile + mid quality OR desktop + low quality => 1 (MID)
	// mobile + high quality => 2 (HIGH)
	// desktop + mid or high quality => 3 (VERY HIGH)
	this.quality = opts.quality == undefined ? 3 : opts.quality;

	if(this.quality === 0)
	{
		this.width /= 2;
		this.height /=2;
	}

	this.settings = null;
	this.renderer = null;
	this.manager = null;
	this.lib = null;
	this.materials = {};
	this.components = {};
	this.extras = {
		vignetteColor: new THREE.Color(0x458ab1),
		bloom: null,
		fxaa: null
	};

	this.containers = {};
	this.containers.main = opts.container == undefined ? document.body : opts.container;
	this.containers.overlay = opts.overlay == undefined ? document.body : opts.overlay;

	this.gameover = opts.gameover == undefined ? null : opts.gameover;

	this.godmode = opts.godmode == undefined ? false : opts.godmode;

	this.laps = opts.laps == undefined ? 3 : opts.laps;
	this.paused = false;
	this._rafActive = false;
	this._pauseTime = 0;
	this._shipActiveBeforePause = [];

	this.hud = null;
	this.huds = [];

	this.gameplay = null;
	this.gameplays = [];
	this.raceOver = false;
	this.winner = -1;

	this.composers = {
		game: null
	};

	this.initRenderer();

	function onKeyPress(event)
	{
		if(event.keyCode == 27/*escape*/ || event.keyCode == 80/*P*/)
		{
			self.togglePause();
		}
		else if(event.keyCode == 82/*R*/)
		{
			if(self.paused || self.isRaceFinished())
				self.restartRace();
		}
	}

	this.document.addEventListener('keydown', onKeyPress, false);
}

bkcore.hexgl.HexGL.prototype.getShipControls = function()
{
	var list = [];
	if(this.components.shipControls) list.push(this.components.shipControls);
	if(this.components.shipControls2) list.push(this.components.shipControls2);
	return list;
};

bkcore.hexgl.HexGL.prototype.getGameplays = function()
{
	return this.gameplays.length > 0 ? this.gameplays : (this.gameplay ? [this.gameplay] : []);
};

bkcore.hexgl.HexGL.prototype.getHuds = function()
{
	return this.huds.length > 0 ? this.huds : (this.hud ? [this.hud] : []);
};

bkcore.hexgl.HexGL.prototype.isRaceFinished = function()
{
	if(this.raceOver) return true;

	var gameplays = this.getGameplays();
	for(var i = 0; i < gameplays.length; i++)
	{
		if(gameplays[i].result != gameplays[i].results.NONE)
			return true;
	}
	return false;
};

bkcore.hexgl.HexGL.prototype.start = function()
{
	this.manager.setCurrent("game");

	this.startLoop();

	this.initGameplay();
}

bkcore.hexgl.HexGL.prototype.startLoop = function()
{
	if(this._rafActive) return;

	var self = this;
	this._rafActive = true;

	// The loop may have been idle for a while (loading, pause, results...).
	// Reset the render clock so the first frame uses a sane delta.
	if(this.manager) this.manager.time = window.perfNow();

	function raf()
	{
		if(!self.active)
		{
			self._rafActive = false;
			return;
		}

		self.update();

		if(self.active)
			requestAnimationFrame(raf);
		else
			self._rafActive = false;
	}

	raf();
}

bkcore.hexgl.HexGL.prototype.pause = function()
{
	if(this.paused || !this.active || !this.gameplay) return;
	if(this.isRaceFinished()) return;

	var gameplays = this.getGameplays();
	var controls = this.getShipControls();

	this.paused = true;
	this.active = false;
	this._pauseTime = Date.now();
	this._shipActiveBeforePause = [];

	for(var i = 0; i < gameplays.length; i++)
		gameplays[i].active = false;

	for(var j = 0; j < controls.length; j++)
	{
		this._shipActiveBeforePause.push(controls[j].active);
		controls[j].active = false;
		controls[j].clearKeys();
	}

	bkcore.Audio.stop('bg');
	bkcore.Audio.stop('wind');
	bkcore.Audio.stop('boost');

	var overlay = this.document.getElementById('pause');
	if(overlay) overlay.style.display = 'flex';
}

bkcore.hexgl.HexGL.prototype.resume = function()
{
	if(!this.paused || !this.gameplay) return;

	var pausedFor = Date.now() - this._pauseTime;
	var gameplays = this.getGameplays();
	var controls = this.getShipControls();

	this.paused = false;
	this.active = true;

	for(var i = 0; i < gameplays.length; i++)
	{
		gameplays[i].active = true;
		gameplays[i].timer.time.start += pausedFor;
		gameplays[i].timer.time.previous = Date.now();
	}

	for(var j = 0; j < controls.length; j++)
	{
		controls[j].active = this._shipActiveBeforePause[j] == undefined ? true : this._shipActiveBeforePause[j];
		controls[j].clearKeys();
	}

	var overlay = this.document.getElementById('pause');
	if(overlay) overlay.style.display = 'none';

	bkcore.Audio.play('bg');
	bkcore.Audio.play('wind');
	bkcore.Audio.volume('wind', 0.35);

	if(this.manager) this.manager.time = window.perfNow();
	this.startLoop();
}

bkcore.hexgl.HexGL.prototype.togglePause = function()
{
	if(this.paused)
	{
		this.resume();
		return;
	}

	if(this.active && this.gameplay && !this.isRaceFinished())
		this.pause();
}

bkcore.hexgl.HexGL.prototype.restartRace = function()
{
	if(!this.gameplay) return;

	var pauseOverlay = this.document.getElementById('pause');
	if(pauseOverlay) pauseOverlay.style.display = 'none';

	var legacyFinish = this.document.getElementById('finish');
	if(legacyFinish) legacyFinish.style.display = 'none';

	if(this.gameover) this.gameover.style.display = 'none';
	if(this.containers.main && this.containers.main.parentElement)
		this.containers.main.parentElement.style.display = 'block';

	var gameplays = this.getGameplays();
	var controls = this.getShipControls();

	this.active = true;
	this.paused = false;
	this._pauseTime = 0;
	this._shipActiveBeforePause = [];
	this.raceOver = false;
	this.winner = -1;
	if(this.manager && this.manager.get('game'))
		this.manager.get('game').objects.lowFPS = 0;

	for(var j = 0; j < controls.length; j++)
		controls[j].clearKeys();

	for(var i = 0; i < gameplays.length; i++)
	{
		gameplays[i].active = true;
		gameplays[i].start();
	}

	bkcore.Audio.stop('bg');
	bkcore.Audio.stop('wind');
	bkcore.Audio.play('bg');
	bkcore.Audio.play('wind');
	bkcore.Audio.volume('wind', 0.35);

	if(this.manager) this.manager.time = window.perfNow();
	this.startLoop();
}

bkcore.hexgl.HexGL.prototype.reset = function()
{
	var gameplays = this.getGameplays();
	if(this.manager && this.manager.get('game'))
		this.manager.get('game').objects.lowFPS = 0;

	for(var i = 0; i < gameplays.length; i++)
		gameplays[i].start();

	bkcore.Audio.stop('bg');
	bkcore.Audio.stop('wind');
	bkcore.Audio.volume('wind', 0.35);
	bkcore.Audio.play('bg');
	bkcore.Audio.play('wind');
}

bkcore.hexgl.HexGL.prototype.restart = function()
{
	this.restartRace();
}

bkcore.hexgl.HexGL.prototype.update = function()
{
	if(!this.active) return;

	var gameplays = this.getGameplays();
	for(var i = 0; i < gameplays.length; i++)
	{
		gameplays[i].update();
		if(!this.active) break;
	}

	if(this.active)
		this.manager.renderCurrent();
}

bkcore.hexgl.HexGL.prototype.init = function()
{
	this.initHUD();
	
	this.track.buildMaterials(this.quality);

	this.track.buildScenes(this, this.quality);

	this.initGameComposer();
}

bkcore.hexgl.HexGL.prototype.load = function(opts)
{
	this.track.load(opts, this.quality);
}

bkcore.hexgl.HexGL.prototype.initGameplay = function()
{
	var self = this;
	var count = this.twoPlayer ? 2 : 1;
	var controls = [this.components.shipControls, this.components.shipControls2];
	var cameras = [this.components.cameraChase, this.components.cameraChase2];
	var huds = this.getHuds();
	var spawns = this.components.spawns || [this.track.spawn];

	this.gameplays = [];

	for(var i = 0; i < count; i++)
	{
		(function(index)
		{
			var game = new bkcore.hexgl.Gameplay({
				mode: self.mode,
				hud: huds[index] || null,
				laps: self.laps,
				maxLaps: self.laps,
				shipControls: controls[index],
				cameraControls: cameras[index],
				analyser: self.track.analyser,
				pixelRatio: self.track.pixelRatio,
				track: self.track,
				spawn: spawns[index] || self.track.spawn,
				spawnRotation: self.track.spawnRotation,
				onEnd: self.twoPlayer ? function(result) {
					self.onPlayerEnd(index, result);
				} : null,
				onFinish: self.twoPlayer ? function() {} : function() {
					self.components.shipControls.terminate();
					self.displayScore(this.finishTime, this.lapTimes);
				}
			});

			self.gameplays.push(game);
		})(i);
	}

	this.gameplay = this.gameplays[0] || null;

	for(var j = 0; j < this.gameplays.length; j++)
		this.gameplays[j].start();

	bkcore.Audio.play('bg');
	bkcore.Audio.play('wind');
	bkcore.Audio.volume('wind', 0.35);
}

bkcore.hexgl.HexGL.prototype.onPlayerEnd = function(index, result)
{
	if(!this.twoPlayer || this.raceOver) return;

	this.raceOver = true;

	var gameplays = this.getGameplays();
	var controls = this.getShipControls();

	if(result == gameplays[index].results.FINISH)
		this.winner = index;
	else if(result == gameplays[index].results.DESTROYED)
		this.winner = index === 0 ? 1 : 0;
	else
		this.winner = -1;

	for(var i = 0; i < controls.length; i++)
	{
		controls[i].active = false;
		controls[i].clearKeys();
	}

	for(var j = 0; j < gameplays.length; j++)
		gameplays[j].active = false;

	bkcore.Audio.stop('bg');
	bkcore.Audio.stop('wind');
	bkcore.Audio.stop('boost');

	this.displayTwoPlayerScore(this.winner);
}

bkcore.hexgl.HexGL.prototype.displayScore = function(f, l)
{
	this.active = false;
	l = l || [];

	var finished = this.gameplay.result == this.gameplay.results.FINISH;
	var fmt = function(ms)
	{
		ms = Math.max(0, Math.round(ms || 0));
		var t = bkcore.Timer.msToTimeString(ms);
		return t.m + "'" + t.s + "''" + t.ms;
	};

	var bestLap = null;
	for(var i = 0; i < l.length; i++)
	{
		if(l[i] > 0 && (bestLap === null || l[i] < bestLap))
			bestLap = l[i];
	}

	var recordKey = 'hexgl-best-' + this.track.name + '-' + this.difficulty + '-' + this.laps;
	var oldBest = null;
	try
	{
		var stored = Number(localStorage.getItem(recordKey));
		if(stored > 0) oldBest = stored;
	}
	catch(e) {}

	var isRecord = finished && (oldBest === null || f < oldBest);
	if(isRecord)
	{
		try { localStorage.setItem(recordKey, Math.round(f)); }
		catch(e) {}
	}

	var doc = this.document;
	var setText = function(id, text)
	{
		var el = doc.getElementById(id);
		if(el) el.innerHTML = text;
	};

	setText('go-kicker', finished ? 'RACE COMPLETE' : 'RACE FAILED');
	setText('time', fmt(f));
	setText('go-label-best-lap', '最佳单圈');
	setText('go-label-mode', '难度 / 圈数');
	setText('go-label-best', '历史最佳');
	setText('go-best-lap', bestLap === null ? '--' : fmt(bestLap));
	setText('go-mode', (this.difficulty == 0 ? '休闲' : '竞技') + ' · ' + this.laps + ' 圈');
	setText('go-best', fmt(finished ? (isRecord ? f : (oldBest === null ? f : oldBest)) : (oldBest === null ? 0 : oldBest)));
	if(!finished && oldBest === null)
		setText('go-best', '--');

	var recordEl = this.document.getElementById('go-record');
	if(recordEl)
	{
		recordEl.innerHTML = finished ? (isRecord ? '新纪录！' : '完成比赛') : '赛车损毁 · 未能完赛';
		recordEl.className = finished ? 'go-record good' : 'go-record bad';
	}

	var lapsHtml = '';
	for(var j = 0; j < l.length; j++)
		lapsHtml += '<div class="go-lap"><span>第 ' + (j+1) + ' 圈</span><b>' + fmt(l[j]) + '</b></div>';
	if(lapsHtml === '')
		lapsHtml = '<div class="go-lap empty">暂无完整圈速</div>';
	setText('go-laps', lapsHtml);

	if(this.gameover !== null)
	{
		this.gameover.style.display = 'block';
		if(this.containers.main && this.containers.main.parentElement)
			this.containers.main.parentElement.style.display = 'none';
		return;
	}

	// Legacy fallback for embedded builds without the custom results screen.
	if(this.hud != null) this.hud.display(finished ? '完赛' : '赛车损毁');
}

bkcore.hexgl.HexGL.prototype.displayTwoPlayerScore = function(winner)
{
	this.active = false;
	this.raceOver = true;

	var doc = this.document;
	var gameplays = this.gameplays;
	var fmt = function(ms)
	{
		ms = Math.max(0, Math.round(ms || 0));
		var t = bkcore.Timer.msToTimeString(ms);
		return t.m + "'" + t.s + "''" + t.ms;
	};
	var setText = function(id, text)
	{
		var el = doc.getElementById(id);
		if(el) el.innerHTML = text;
	};

	var bestLap = null;
	for(var i = 0; i < gameplays.length; i++)
	{
		var laps = gameplays[i].lapTimes || [];
		for(var j = 0; j < laps.length; j++)
		{
			if(laps[j] > 0 && (bestLap === null || laps[j] < bestLap))
				bestLap = laps[j];
		}
	}

	var winnerGame = winner >= 0 ? gameplays[winner] : null;
	var winnerFinished = winnerGame != null && winnerGame.result == winnerGame.results.FINISH;

	setText('go-kicker', 'VERSUS COMPLETE');
	setText('time', winnerFinished ? fmt(winnerGame.finishTime) : (winner >= 0 ? '获胜' : '平局'));
	setText('go-label-best-lap', '全场最快单圈');
	setText('go-label-mode', '模式 / 圈数');
	setText('go-label-best', '获胜者');
	setText('go-best-lap', bestLap === null ? '--' : fmt(bestLap));
	setText('go-mode', '双人对战 · ' + this.laps + ' 圈');
	setText('go-best', winner >= 0 ? '玩家 ' + (winner + 1) : '平局');

	var recordEl = doc.getElementById('go-record');
	if(recordEl)
	{
		recordEl.innerHTML = winner >= 0 ? '玩家 ' + (winner + 1) + ' 获胜' : '双方均未完成';
		recordEl.className = winner >= 0 ? 'go-record good' : 'go-record bad';
	}

	var html = '<div class="vs-result">';
	for(var p = 0; p < gameplays.length; p++)
	{
		var game = gameplays[p];
		var finished = game.result == game.results.FINISH;
		var destroyed = game.result == game.results.DESTROYED;
		var status = p == winner ? '冠军' : (finished ? '完赛' : (destroyed ? '赛车损毁' : '未完赛'));

		var lapHtml = '';
		var playerLaps = game.lapTimes || [];
		for(var k = 0; k < playerLaps.length; k++)
			lapHtml += '<div class="vs-lap"><span>第 ' + (k+1) + ' 圈</span><b>' + fmt(playerLaps[k]) + '</b></div>';
		if(lapHtml === '')
			lapHtml = '<div class="vs-lap empty">暂无完整圈速</div>';

		html += '<div class="vs-card ' + (p === 0 ? 'p1' : 'p2') + (p == winner ? ' winner' : '') + '">'
			+ '<div class="vs-head"><span>玩家 ' + (p+1) + '</span><b>' + status + '</b></div>'
			+ '<div class="vs-total">' + (finished ? fmt(game.finishTime) : (p == winner ? '对手损毁' : '未完赛')) + '</div>'
			+ '<div class="vs-meta">' + (finished ? '完成 ' + game.maxLaps + ' 圈' : '第 ' + Math.min(game.lap, game.maxLaps) + ' / ' + game.maxLaps + ' 圈') + '</div>'
			+ '<div class="vs-laps">' + lapHtml + '</div>'
			+ '</div>';
	}
	html += '</div>';
	setText('go-laps', html);

	if(this.gameover !== null)
	{
		this.gameover.style.display = 'block';
		if(this.containers.main && this.containers.main.parentElement)
			this.containers.main.parentElement.style.display = 'none';
		return;
	}

	if(this.hud != null) this.hud.display(winner >= 0 ? '玩家 ' + (winner+1) + ' 获胜' : '平局');
}

bkcore.hexgl.HexGL.prototype.initRenderer = function()
{
	var renderer = new THREE.WebGLRenderer({
		antialias: false,
		clearColor: 0x000000
	});

	// desktop + quality mid or high
	// Split-screen runs two scene passes per frame, so shadows stay off.
	if(this.quality > 2 && !this.twoPlayer)
	{
		renderer.physicallyBasedShading = true;
		renderer.gammaInput = true;
		renderer.gammaOutput = true;
		renderer.shadowMapEnabled = true;
		renderer.shadowMapSoft = true;
	}
	else if(this.quality > 2)
	{
		renderer.physicallyBasedShading = true;
		renderer.gammaInput = true;
		renderer.gammaOutput = true;
	}

	renderer.autoClear = false;
	renderer.sortObjects = false;
	renderer.setSize( this.width, this.height );
	renderer.domElement.style.position = "relative";

	this.containers.main.appendChild( renderer.domElement );
	this.canvas = renderer.domElement;
	this.renderer = renderer;
	this.manager = new bkcore.threejs.RenderManager(renderer);
}

bkcore.hexgl.HexGL.prototype.initHUD = function()
{
	if(this.twoPlayer)
	{
		if(this.document.body) this.document.body.classList.add('two-player');
		var raceUI = this.document.getElementById('race-ui');
		if(raceUI) raceUI.className = 'two-player';
	}
	else if(this.document.body)
	{
		this.document.body.classList.remove('two-player');
	}

	if(!this.displayHUD) return;

	var hudOpts = {
		width: this.width,
		height: this.height,
		font: "BebasNeueRegular, 'Microsoft YaHei', 'PingFang SC', sans-serif",
		bg: this.track.lib.get("images", "hud.bg"),
		speed: this.track.lib.get("images", "hud.speed"),
		shield: this.track.lib.get("images", "hud.shield")
	};

	if(this.twoPlayer)
	{
		this.huds = [];
		var half = Math.floor(this.width / 2);

		for(var i = 0; i < 2; i++)
		{
			var opts = {};
			for(var k in hudOpts)
			{
				if(Object.prototype.hasOwnProperty.call(hudOpts, k))
					opts[k] = hudOpts[k];
			}
			opts.width = half;

			var hud = new bkcore.hexgl.HUD(opts);
			hud.canvas.className = 'hud-split ' + (i === 0 ? 'hud-left' : 'hud-right');
			this.containers.overlay.appendChild(hud.canvas);
			this.huds.push(hud);
		}

		this.hud = this.huds[0];
		return;
	}

	this.hud = new bkcore.hexgl.HUD(hudOpts);
	this.containers.overlay.appendChild(this.hud.canvas);
}

bkcore.hexgl.HexGL.prototype.initGameComposer = function()
{
	// Split-screen renders each camera directly through WebGL viewports.
	// The full-screen post-processing chain (bloom/hex vignette) only makes
	// sense for a single view, so keep it for solo mode.
	if(this.twoPlayer) return;

	var renderTargetParameters = { minFilter: THREE.LinearFilter, magFilter: THREE.LinearFilter, format: THREE.RGBFormat, stencilBuffer: false };
	var renderTarget = new THREE.WebGLRenderTarget( this.width, this.height, renderTargetParameters );

	// GAME COMPOSER
	var renderSky = new THREE.RenderPass( this.manager.get("sky").scene, this.manager.get("sky").camera );

	var renderModel = new THREE.RenderPass( this.manager.get("game").scene, this.manager.get("game").camera );
	renderModel.clear = false;

	this.composers.game = new THREE.EffectComposer( this.renderer, renderTarget );

	var effectScreen = new THREE.ShaderPass( THREE.ShaderExtras[ "screen" ] );
	effectScreen.renderToScreen = true;
	var effectVignette = new THREE.ShaderPass( THREE.ShaderExtras[ "vignette" ] );

	var effectHex = new THREE.ShaderPass( bkcore.threejs.Shaders[ "hexvignette" ] );
	effectHex.uniforms[ 'size' ].value = 512.0 * (this.width/1633);
	effectHex.uniforms[ 'rx' ].value = this.width;
	effectHex.uniforms[ 'ry' ].value = this.height;
	effectHex.uniforms[ 'tHex' ].texture = this.track.lib.get("textures", "hex");
	effectHex.uniforms[ 'color' ].value = this.extras.vignetteColor;

	effectHex.renderToScreen = true;

	this.composers.game.addPass( renderSky );
	this.composers.game.addPass( renderModel );

	// if(this.quality > 0 && !this.mobile)
	// {
	// 	var effectFXAA = new THREE.ShaderPass( THREE.ShaderExtras[ "fxaa" ] );
	// 	effectFXAA.uniforms[ 'resolution' ].value.set( 1 / this.width, 1 / this.height );

	// 	this.composers.game.addPass( effectFXAA );

	// 	this.extras.fxaa = effectFXAA;
	
	// }
	
	// desktop + quality mid or high
	if(this.quality > 2)
	{
		var effectBloom = new THREE.BloomPass( 0.8, 25, 4 , 256);

		this.composers.game.addPass( effectBloom );

		this.extras.bloom = effectBloom;
	}

	// desktop + quality low, mid or high
	// OR
	// mobile + quality mid or high
	if(this.quality > 0)
		this.composers.game.addPass( effectHex );
	else
		this.composers.game.addPass( effectScreen );
}

bkcore.hexgl.HexGL.prototype.createMesh = function(parent, geometry, x, y, z, mat)
{
	geometry.computeTangents();

	var mesh = new THREE.Mesh( geometry, mat );
	mesh.position.set( x, y, z );
	parent.add(mesh);

	// desktop + quality mid or high
	if(this.quality > 2 && !this.twoPlayer)
	{
		mesh.castShadow = true;
		mesh.receiveShadow = true;
	}

	return mesh;
}

bkcore.hexgl.HexGL.prototype.tweakShipControls = function()
{
	var controls = this.getShipControls();

	for(var i = 0; i < controls.length; i++)
	{
		var c = controls[i];

		if(this.difficulty == 1)
		{
			c.airResist = 0.040;
			c.airDrift = 0.07;
			c.thrust = 0.046;
			c.airBrake = 0.050;
			c.maxSpeed = 12.5;
			c.boosterSpeed = c.maxSpeed * 0.35;
			c.boosterDecay = 0.007;
			c.angularSpeed = 0.0210;
			c.airAngularSpeed = 0.0240;
			c.rollAngle = 0.65;
			c.shieldDamage = 0.03;
			c.collisionSpeedDecrease = 0.8;
			c.collisionSpeedDecreaseCoef = 0.5;
			c.rollLerp = 0.12;
			c.driftLerp = 0.4;
			c.angularLerp = 0.55;
		}
		else if(this.difficulty == 0)
		{
			c.airResist = 0.026;
			c.airDrift = 0.06;
			c.thrust = 0.026;
			c.airBrake = 0.032;
			c.maxSpeed = 9.1;
			c.boosterSpeed = c.maxSpeed * 0.5;
			c.boosterDecay = 0.007;
			c.angularSpeed = 0.0190;
			c.airAngularSpeed = 0.0210;
			c.rollAngle = 0.65;
			c.shieldDamage = 0.06;
			c.collisionSpeedDecrease = 0.8;
			c.collisionSpeedDecreaseCoef = 0.5;
			c.rollLerp = 0.10;
			c.driftLerp = 0.3;
			c.angularLerp = 0.55;
		}

		if(this.godmode)
			c.shieldDamage = 0.0;
	}
}
