 /*
 * HexGL
 * @author Thibaut 'BKcore' Despoulain <http://bkcore.com>
 * @license This work is licensed under the Creative Commons Attribution-NonCommercial 3.0 Unported License. 
 *          To view a copy of this license, visit http://creativecommons.org/licenses/by-nc/3.0/.
 */

var bkcore = bkcore || {};
bkcore.hexgl = bkcore.hexgl || {};

bkcore.hexgl.RaceData = function(track, mode, shipControls)
{
	this.track = track;
	this.mode = mode;
	this.shipControls = shipControls;

	this.rate = 2; // 1 / rate
	this.rateState = 1;

	this.data = [];
	this.last = -1;
	this.seek = 0;

	this._p = new THREE.Vector3();
	this._pp = new THREE.Vector3();
	this._np = new THREE.Vector3();
	this._q = new THREE.Quaternion();
	this._pq = new THREE.Quaternion();
	this._nq = new THREE.Quaternion();
}

bkcore.hexgl.RaceData.prototype.tick = function(time)
{
	if(this.rateState == 1)
	{
		var p = this.shipControls.getPosition();
		var q = this.shipControls.getQuaternion();
		this.data.push([
			time,
			p.x, p.y, p.z,
			q.x, q.y, q.z, q.w
		]);
		++this.last;
	}
	else if(this.rateState == this.rate)
	{
		this.rateState = 0;
	}
	
	// Advance the sampling counter, not the sampling interval. The old
	// code incremented rate forever and captured every physics frame,
	// roughly doubling replay memory for the default 1-in-2 setting.
	this.rateState++;
}

bkcore.hexgl.RaceData.prototype.applyInterpolated = function(time)
{
	// A replay can be empty or contain a single frame (e.g. after an
	// immediate crash). Never dereference data[seek+1] at the final frame.
	if(this.last < 0 || !this.data.length ||
		typeof time != 'number' || !isFinite(time))
		return false;
	// Keep the common case (a normal frame within the current interval)
	// O(1). Large replay jumps and rewinds instead use an upper-bound binary
	// search, so scrubbing a 200k-frame recording cannot stall the UI.
	// Upper bound also consistently picks the LAST pose at an exact time
	// when paused/legacy recordings contain duplicate timestamps.
	if(this.seek < 0 || this.seek > this.last ||
		this.data[this.seek][0] > time ||
		(this.seek < this.last && this.data[this.seek+1][0] <= time))
	{
		var lo = 0, hi = this.last+1;
		while(lo < hi)
		{
			var mid = Math.floor((lo+hi)/2);
			if(this.data[mid][0] <= time) lo = mid+1;
			else hi = mid;
		}
		this.seek = Math.max(0, lo-1);
	}

	var prev = this.data[this.seek];
	this._pp.set(prev[1], prev[2], prev[3]);
	this._pq.set(prev[4], prev[5], prev[6], prev[7]).normalize();

	// Clamp the replay at its first and last recorded frames.
	if(this.seek == this.last || time <= prev[0])
	{
		this.shipControls.teleport(this._pp, this._pq);
		return true;
	}

	var next = this.data[this.seek+1];
	this._np.set(next[1], next[2], next[3]);
	this._nq.set(next[4], next[5], next[6], next[7]).normalize();

	// Legacy replays can contain equal timestamps (paused or high-FPS
	// frames); avoid division by zero and invalid quaternion positions.
	var span = next[0]-prev[0];
	var t = span > 0 ? Math.max(0, Math.min(1, (time-prev[0])/span)) : 1;
	this._p.copy(this._pp).lerpSelf(this._np, t);
	this._q.copy(this._pq).slerpSelf(this._nq, t);
	this.shipControls.teleport(this._p, this._q);
	return true;
}

bkcore.hexgl.RaceData.prototype.reset = function()
{
	this.seek = 0;
}

bkcore.hexgl.RaceData.prototype.export = function()
{
	return this.data;
}

// Persist a validated timeattack capture when the finish screen calls us.
// A replay must never
// overwrite a previous good recording, and storage quota/private-mode
// failures must not interrupt the race results screen.
bkcore.hexgl.RaceData.prototype.save = function(storage)
{
	if(this.mode != 'timeattack' || !storage ||
		typeof storage.setItem != 'function') return false;
	try
	{
		// Reuse the same validation and snapshot rules as replay import:
		// corrupted physics samples must not replace a playable recording.
		var validated = new bkcore.hexgl.RaceData(this.track, 'replay', this.shipControls);
		validated.import(this.data);
		// The viewer and menu require a nonnegative, positive-duration
		// recording with at least two poses. Do not replace the last
		// watchable race with a valid but unusable partial capture.
		if(validated.last < 1 || validated.data[0][0] < 0 ||
			validated.data[validated.last][0] <= validated.data[0][0])
			return false;
		storage.setItem('race-'+this.track+'-replay', JSON.stringify(validated.data));
		return true;
	}
	catch(e)
	{
		return false;
	}
}

bkcore.hexgl.RaceData.prototype.import = function(imp)
{
	// Replays come from localStorage. Reject empty, truncated or malformed
	// saves before they can crash the renderer during playback.
	if(!Array.isArray(imp) || imp.length < 1 || imp.length > 200000)
		throw new Error('Invalid replay frame count');
	var previousTime = -Infinity;
	var validated = new Array(imp.length);
	for(var i=0;i<imp.length;i++)
	{
		var frame=imp[i];
		if(!Array.isArray(frame) || frame.length != 8)
			throw new Error('Invalid replay frame at '+i);
		for(var j=0;j<8;j++)
			if(typeof frame[j] != 'number' || !isFinite(frame[j]))
				throw new Error('Non-finite replay value at '+i);
		// r50 Quaternion.slerpSelf assumes unit quaternions. A damaged
		// localStorage frame with a zero or over-length orientation can
		// otherwise produce NaN rotations during WebGL replay.
		var qNorm2=frame[4]*frame[4]+frame[5]*frame[5]+
			frame[6]*frame[6]+frame[7]*frame[7];
		if(!isFinite(qNorm2) || Math.abs(qNorm2-1)>0.02)
			throw new Error('Invalid replay quaternion at '+i);
		if(frame[0] < previousTime)
			throw new Error('Replay timestamps are out of order');
		previousTime=frame[0];
		// Keep a validated snapshot: callers may still mutate the parsed
		// localStorage array after import and bypass these checks otherwise.
		validated[i]=frame.slice(0);
	}
	this.data=validated;
	this.last=validated.length-1;
	this.seek=0;
}
