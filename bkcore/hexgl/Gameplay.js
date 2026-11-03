 /*
 * HexGL
 * @author Thibaut 'BKcore' Despoulain <http://bkcore.com>
 * @license This work is licensed under the Creative Commons Attribution-NonCommercial 3.0 Unported License. 
 *          To view a copy of this license, visit http://creativecommons.org/licenses/by-nc/3.0/.
 */

var bkcore = bkcore || {};
bkcore.hexgl = bkcore.hexgl || {};

bkcore.hexgl.Gameplay = function(opts)
{
	var self = this;

	this.startDelay = opts.hud == null ? 0 : 800;
	this.countDownDelay = opts.hud == null ? 800 : 900;

	this.active = false;
	this.timer = new bkcore.Timer();
	this.modes = {
		'timeattack':null,
		'survival':null,
		'replay':null
	};
	this.mode = opts.mode == undefined || !(opts.mode in this.modes) ? "timeattack" : opts.mode;
	this.step = 0;

	this.hud = opts.hud;
	this.shipControls = opts.shipControls;
	this.cameraControls = opts.cameraControls;
	this.track = opts.track;
	this.analyser = opts.analyser;
	this.pixelRatio = opts.pixelRatio;
	this.spawn = opts.spawn == undefined ? this.track.spawn : opts.spawn;
	this.spawnRotation = opts.spawnRotation == undefined ? this.track.spawnRotation : opts.spawnRotation;

	this.previousCheckPoint = -1;
	this.nextCheckPointIndex = 0;

	this.results = {
		FINISH: 1,
		DESTROYED: 2,
		WRONGWAY: 3,
		REPLAY: 4,
		NONE: -1
	};
	this.result = this.results.NONE;

	this.lap = 1;
	this.lapTimes = [];
	this.lapTimeElapsed = 0;
	this.maxLaps = opts.maxLaps == undefined ? 3 : opts.maxLaps;
	this.score = null;
	this.finishTime = null;
	this.onFinish = opts.onFinish == undefined ? function(){console.log("FINISH");} : opts.onFinish;
	this.onEnd = opts.onEnd == undefined ? null : opts.onEnd;

	this.raceData = null;

	this.modes.timeattack = function()
	{
		self.raceData.tick(this.timer.time.elapsed);

		self.hud != null && self.hud.updateTime(self.timer.getElapsedTime());
		var cp = self.checkPoint();

		// Only accept the next checkpoint in the ordered route. Crossing
		// the last gate and start line alone must never count as a lap.
		var checkpoints = self.track.checkpoints.list;
		if(cp != -1 && checkpoints.length > 1 &&
			cp == checkpoints[self.nextCheckPointIndex])
		{
			self.previousCheckPoint = cp;
			self.nextCheckPointIndex = (self.nextCheckPointIndex + 1) % checkpoints.length;
			if(cp == self.track.checkpoints.start)
			{
				var t = self.timer.time.elapsed;
				self.lapTimes.push(t - self.lapTimeElapsed);
				self.lapTimeElapsed = t;
				if(self.lap == self.maxLaps)
				{
					self.end(self.results.FINISH);
				}
				else
				{
					self.lap++;
					if(self.hud != null) self.hud.updateLap(self.lap, self.maxLaps);
					if(self.lap == self.maxLaps && self.hud != null)
						self.hud.display("最后一圈", 0.5);
				}
			}
		}

		if(self.result == self.results.NONE && self.shipControls.destroyed == true)
		{
			self.end(self.results.DESTROYED);
		}
	};

	this.modes.replay = function()
	{
		self.raceData.applyInterpolated(this.timer.time.elapsed);

		if(self.raceData.seek == self.raceData.last)
		{
			self.end(self.results.REPLAY);
		}
	};
}

bkcore.hexgl.Gameplay.prototype.simu = function()
{
	this.lapTimes = [92300, 91250, 90365];
	this.finishTime = this.lapTimes[0]+this.lapTimes[1]+this.lapTimes[2];
	if(this.hud != null) this.hud.display("Finish");
	this.step = 100;
	this.result = this.results.FINISH;
	this.shipControls.active = false;
}

bkcore.hexgl.Gameplay.prototype.start = function(opts)
{
	this.finishTime = null;
	this.score = null;
	this.result = this.results.NONE;
	this.lap = 1;
	this.lapTimes = [];
	this.lapTimeElapsed = 0;
	// Remember the last OSM checkpoint sample so a long frame cannot skip
	// a narrow gate between two legal positions on the same road.
	this._lastCheckpointSample = null;
	if(this.analyser && this.analyser.projectMovement && this.spawn &&
		isFinite(this.spawn.x) && isFinite(this.spawn.z))
		this._lastCheckpointSample = {x:this.spawn.x,z:this.spawn.z};

	this.shipControls.reset(this.spawn, this.spawnRotation);
	this.shipControls.active = false;

	this.previousCheckPoint = this.track.checkpoints.start;
	var checkPointList = this.track.checkpoints.list;
	this.nextCheckPointIndex = (checkPointList.indexOf(this.track.checkpoints.start) + 1) % checkPointList.length;

	this.raceData = new bkcore.hexgl.RaceData(this.track.name, this.mode, this.shipControls);
	if(this.mode == 'replay')
	{
		this.cameraControls.mode = this.cameraControls.modes.ORBIT;
		if(this.hud != null) this.hud.messageOnly = true;

		try {
			var d = localStorage['race-'+this.track.name+'-replay'];
			if(d == undefined)
			{
				console.error('No replay data for '+'race-'+this.track.name+'-replay'+'.');
				return false;
			}
			this.raceData.import(
				JSON.parse(d)
			);
		}
		catch(e) { console.error('Bad replay format : '+e); return false; }
	}

	this.active = true;
	this.step = 0;
	this.timer.start();
	if(this.hud != null)
	{
		this.hud.resetTime();
		this.hud.display("准备发车", 1);
		this.hud.updateLap(this.lap, this.maxLaps);
	}
}

bkcore.hexgl.Gameplay.prototype.end = function(result)
{
	this.score = this.timer.getElapsedTime();
	this.finishTime = this.timer.time.elapsed;
	this.timer.start();
	this.result = result;

	this.shipControls.active = false;

	if(this.onEnd != null)
		this.onEnd.call(this, result);

	if(result == this.results.FINISH)
	{
		if(this.hud != null) this.hud.display("完赛");
		this.step = 100;
	}
	else if(result == this.results.DESTROYED)
	{
		if(this.hud != null) this.hud.display("赛车损毁");
		this.step = 100;
	}
}

bkcore.hexgl.Gameplay.prototype.update = function()
{
	if(!this.active) return;

	this.timer.update();
	
	if(this.step == 0 && this.timer.time.elapsed >= this.countDownDelay+this.startDelay)
	{
		if(this.hud != null) this.hud.display("3");
		this.step = 1;
	}
	else if(this.step == 1 && this.timer.time.elapsed >= 2*this.countDownDelay+this.startDelay)
	{
		if(this.hud != null) this.hud.display("2");
		this.step = 2;
	}
	else if(this.step == 2 && this.timer.time.elapsed >= 3*this.countDownDelay+this.startDelay)
	{
		if(this.hud != null) this.hud.display("1");
		this.step = 3;
	}
	else if(this.step == 3 && this.timer.time.elapsed >= 4*this.countDownDelay+this.startDelay)
	{
		if(this.hud != null) this.hud.display("出发", 0.5);
		this.step = 4;
		this.timer.start();
		
		if(this.mode != "replay")
			this.shipControls.active = true;
	}
	else if(this.step == 4)
	{
		this.modes[this.mode].call(this);
	}
	else if(this.step == 100 && this.timer.time.elapsed >= 2000)
	{
		this.active = false;
		this.onFinish.call(this);
	}
}

bkcore.hexgl.Gameplay.prototype.checkPoint = function()
{
	var x = this.analyser.pixels.width/2 + this.shipControls.dummy.position.x * this.pixelRatio;
	var z = this.analyser.pixels.height/2 + this.shipControls.dummy.position.z * this.pixelRatio;
	// Cityscape samples a pixel bitmap; the OSM road analyser instead uses
	// continuous world metres. Rounding a diagonal road-edge position can
	// push a legal car outside its 14m corridor and miss the checkpoint.
	if(!this.analyser.projectInside) { x = Math.round(x); z = Math.round(z); }

	var color = this.analyser.getPixel(x, z);
	var previous = this._lastCheckpointSample;
	var continuous = !!(this.analyser.projectMovement &&
		this.analyser.route && this.analyser.route.checkpoints);
	if(continuous)
	{
		// Validate *every* OSM sample, not just frames touching a gate:
		// otherwise a teleport can cross a road gap on one tick and claim
		// the checkpoint on the next. Keep the last trusted sample when
		// a movement is rejected, including when the car stays at the
		// invalid destination. The physics layer handles normal recovery.
		if(previous &&
			(this.analyser.distanceSquared(previous.x,previous.z) >
				this.analyser.halfWidth*this.analyser.halfWidth ||
			this.analyser.projectMovement(previous.x,previous.z,x,z,0.8,true).corrected))
			return -1;
		this._lastCheckpointSample = {x:x,z:z};
	}

	if(color.r == 255 && color.g == 255 && color.b < 250)
		return color.b;
	if(!continuous || !previous || color.r != 255)
		return -1;

	// Endpoint-only checkpoint sampling misses a gate if a frame or a
	// delayed gameplay tick moves from before its 12m disc to beyond it.
	// Consider only the *next* gate and certify the entire movement stays
	// on the road; a shortcut through the old city must never earn a gate.
	var gate = this.analyser.route.checkpoints[this.nextCheckPointIndex];
	if(!gate) return -1;
	var dx=x-previous.x,dz=z-previous.z,length2=dx*dx+dz*dz;
	if(!isFinite(length2) || length2<=0) return -1;
	var t=Math.max(0,Math.min(1,
		((gate.x-previous.x)*dx+(gate.z-previous.z)*dz)/length2));
	var nearX=previous.x+t*dx-gate.x;
	var nearZ=previous.z+t*dz-gate.z;
	if(nearX*nearX+nearZ*nearZ>=144) return -1;
	// The segment was already certified above, including short frames.
	return this.nextCheckPointIndex;
}