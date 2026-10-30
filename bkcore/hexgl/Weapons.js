/*
 * HexGL local combat extension.
 * Bullets, shells and vehicle armor for the local split-screen mode.
 * The weapon meshes are plain Three.js primitives so the game keeps its
 * original no-external-asset setup.
 */

var bkcore = bkcore || {};
bkcore.hexgl = bkcore.hexgl || {};

bkcore.hexgl.Weapons = function(opts)
{
	this.scene = opts.scene;
	this.document = opts.document || document;
	this.players = opts.players || [];
	this.projectiles = [];
	this.effects = [];
	this.time = 0;

	this.config = {
		bullet: {
			speed: 2400,
			cooldown: 0.09,
			life: 1.0,
			damage: 0.02,
			hitRadius: 30,
			aimCone: 8 * Math.PI / 180,
			size: 1.6
		},
		shell: {
			speed: 1250,
			cooldown: 1.3,
			life: 2.4,
			damage: 0.16,
			hitRadius: 58,
			aimCone: 14 * Math.PI / 180,
			size: 4.4
		}
	};

	this.geometries = {
		bullet: new THREE.SphereGeometry(1.0, 6, 6),
		shell: new THREE.SphereGeometry(1.0, 9, 9),
		flash: new THREE.SphereGeometry(1.0, 8, 8)
	};

	this.materials = {
		bullet: [
			new THREE.MeshBasicMaterial({ color: 0x69e9ff, blending: THREE.AdditiveBlending, transparent: true, opacity: 0.95, depthWrite: false }),
			new THREE.MeshBasicMaterial({ color: 0xffb15c, blending: THREE.AdditiveBlending, transparent: true, opacity: 0.95, depthWrite: false })
		],
		shell: [
			new THREE.MeshBasicMaterial({ color: 0xbaf8ff, blending: THREE.AdditiveBlending, transparent: true, opacity: 0.95, depthWrite: false }),
			new THREE.MeshBasicMaterial({ color: 0xffd06a, blending: THREE.AdditiveBlending, transparent: true, opacity: 0.95, depthWrite: false })
		]
	};

	this.states = [];
	for(var i = 0; i < this.players.length; i++)
	{
		this.states.push({
			index: i,
			controls: this.players[i].controls,
			bulletCooldown: 0,
			shellCooldown: 0,
			hitFlash: 0,
			shots: 0,
			hits: 0
		});
	}
};

bkcore.hexgl.Weapons.prototype.reset = function()
{
	for(var i = 0; i < this.projectiles.length; i++)
		this.scene.remove(this.projectiles[i].mesh);
	for(var j = 0; j < this.effects.length; j++)
		this.scene.remove(this.effects[j].mesh);

	this.projectiles.length = 0;
	this.effects.length = 0;
	this.time = 0;

	for(var k = 0; k < this.states.length; k++)
	{
		this.states[k].bulletCooldown = 0;
		this.states[k].shellCooldown = 0;
		this.states[k].hitFlash = 0;
		this.states[k].shots = 0;
		this.states[k].hits = 0;
	}
};

bkcore.hexgl.Weapons.prototype.getState = function(index)
{
	return this.states[index] || null;
};

bkcore.hexgl.Weapons.prototype.update = function(dt)
{
	var dtSec = dt * 16.6 / 1000;
	if(dtSec < 0 || dtSec > 0.2) dtSec = Math.min(0.2, Math.max(0, dtSec));

	this.time += dtSec;

	for(var i = 0; i < this.states.length; i++)
	{
		var state = this.states[i];
		var controls = state.controls;

		state.bulletCooldown = Math.max(0, state.bulletCooldown - dtSec);
		state.shellCooldown = Math.max(0, state.shellCooldown - dtSec);
		state.hitFlash = Math.max(0, state.hitFlash - dtSec);

		if(!controls)
			continue;

		var canFire = controls.active && !controls.destroyed && !controls.falling;
		var wantBullet = canFire && (controls.key.bullet || controls.bulletRequest);
		var wantShell = canFire && controls.shellRequest;

		if(wantBullet && state.bulletCooldown <= 0)
		{
			this.fire(state, 'bullet');
			state.bulletCooldown = this.config.bullet.cooldown;
		}

		if(wantShell && state.shellCooldown <= 0)
		{
			this.fire(state, 'shell');
			state.shellCooldown = this.config.shell.cooldown;
		}

		// Requests are one-shot inputs triggered by touch/UI. Bullets can also
		// be held down, while shells always require a fresh press.
		controls.bulletRequest = false;
		controls.shellRequest = false;
	}

	this.updateProjectiles(dtSec);
	this.updateEffects(dtSec);
};

bkcore.hexgl.Weapons.prototype.fire = function(state, type)
{
	var config = this.config[type];
	var controls = state.controls;

	var forward = new THREE.Vector3(0, 0, 1);
	controls.dummy.quaternion.multiplyVector3(forward);
	forward.normalize();

	var muzzle = new THREE.Vector3(
		type == 'bullet' ? (state.shots % 2 == 0 ? -3.6 : 3.6) : 0,
		0.8,
		type == 'bullet' ? 6.0 : 7.0
	);
	controls.dummy.quaternion.multiplyVector3(muzzle);
	muzzle.addSelf(controls.dummy.position);

	var direction = new THREE.Vector3().copy(forward);
	var targetState = this.states[state.index === 0 ? 1 : 0];
	if(targetState && targetState.controls &&
		!targetState.controls.destroyed && !targetState.controls.falling)
	{
		var targetControls = targetState.controls;
		var toTarget = new THREE.Vector3().copy(targetControls.dummy.position).subSelf(muzzle);

		// Lead moving targets a little. currentVelocity is measured in world
		// units per rendered frame, so convert the projectile travel time back
		// to frames before applying it.
		var distance = toTarget.length();
		if(distance > 1)
		{
			var travelFrames = distance / Math.max(1, config.speed * 0.0166);
			toTarget.x += targetControls.currentVelocity.x * travelFrames;
			toTarget.y += targetControls.currentVelocity.y * travelFrames;
			toTarget.z += targetControls.currentVelocity.z * travelFrames;
			toTarget.normalize();
		}

		if(forward.dot(toTarget) >= Math.cos(config.aimCone))
			direction.copy(toTarget);
	}

	var mesh = new THREE.Mesh(
		this.geometries[type],
		this.materials[type][state.index]
	);
	mesh.position.copy(muzzle);
	if(type == 'bullet')
	{
		mesh.scale.set(config.size, config.size, config.size * 4.2);
		mesh.rotation.y = Math.atan2(direction.x, direction.z);
		mesh.rotation.x = -Math.asin(Math.max(-1, Math.min(1, direction.y)));
	}
	else
	{
		mesh.scale.set(config.size, config.size, config.size);
	}
	this.scene.add(mesh);

	this.projectiles.push({
		mesh: mesh,
		direction: direction,
		speed: config.speed,
		damage: config.damage,
		hitRadius: config.hitRadius,
		life: config.life,
		age: 0,
		owner: state.index,
		type: type
	});

	state.shots++;

	// Small muzzle flash helps read the firing direction in split-screen.
	this.spawnEffect(
		muzzle,
		state.index === 0 ? 0x9ff7ff : 0xffc77a,
		type == 'bullet' ? 3.0 : 9.0,
		type == 'bullet' ? 7.0 : 20.0,
		0.10
	);
};

bkcore.hexgl.Weapons.prototype.updateProjectiles = function(dtSec)
{
	for(var i = this.projectiles.length - 1; i >= 0; i--)
	{
		var projectile = this.projectiles[i];
		var mesh = projectile.mesh;
		var oldX = mesh.position.x;
		var oldY = mesh.position.y;
		var oldZ = mesh.position.z;

		mesh.position.x += projectile.direction.x * projectile.speed * dtSec;
		mesh.position.y += projectile.direction.y * projectile.speed * dtSec;
		mesh.position.z += projectile.direction.z * projectile.speed * dtSec;
		projectile.age += dtSec;

		var remove = projectile.age >= projectile.life;
		if(!remove)
		{
			var targetIndex = projectile.owner === 0 ? 1 : 0;
			var targetState = this.states[targetIndex];
			var target = targetState ? targetState.controls : null;

			if(target && !target.destroyed && !target.falling)
			{
				var targetPos = target.dummy.position;
				if(this.segmentHitsSphere(
					oldX, oldY, oldZ,
					mesh.position.x, mesh.position.y, mesh.position.z,
					targetPos.x, targetPos.y, targetPos.z,
					projectile.hitRadius
				))
				{
					var hitPoint = new THREE.Vector3(
						mesh.position.x,
						mesh.position.y,
						mesh.position.z
					);
					var hit = target.applyDamage(projectile.damage);
					if(hit)
					{
						targetState.hitFlash = 0.32;
						this.spawnEffect(
							hitPoint,
							projectile.owner === 0 ? 0x9ff7ff : 0xffc77a,
							projectile.type == 'shell' ? 8.0 : 4.0,
							projectile.type == 'shell' ? 38.0 : 16.0,
							projectile.type == 'shell' ? 0.42 : 0.24
						);

						if(target.destroyed)
						{
							this.spawnEffect(
								targetPos,
								0xffdf80,
								12.0,
								70.0,
								0.75
							);
						}
					}
					remove = true;
				}
			}
		}

		if(remove)
		{
			this.scene.remove(mesh);
			this.projectiles.splice(i, 1);
		}
	}
};

bkcore.hexgl.Weapons.prototype.segmentHitsSphere = function(ax, ay, az, bx, by, bz, cx, cy, cz, radius)
{
	var abx = bx - ax;
	var aby = by - ay;
	var abz = bz - az;
	var acx = cx - ax;
	var acy = cy - ay;
	var acz = cz - az;
	var lengthSq = abx * abx + aby * aby + abz * abz;

	var t = 0;
	if(lengthSq > 0.000001)
		t = (acx * abx + acy * aby + acz * abz) / lengthSq;
	t = Math.max(0, Math.min(1, t));

	var dx = cx - (ax + abx * t);
	var dy = cy - (ay + aby * t);
	var dz = cz - (az + abz * t);

	return dx * dx + dy * dy + dz * dz <= radius * radius;
};

bkcore.hexgl.Weapons.prototype.spawnEffect = function(position, color, startScale, endScale, duration)
{
	if(this.effects.length > 90)
	{
		var oldest = this.effects.shift();
		this.scene.remove(oldest.mesh);
	}

	var material = new THREE.MeshBasicMaterial({
		color: color,
		blending: THREE.AdditiveBlending,
		transparent: true,
		opacity: 0.9,
		depthWrite: false
	});
	var mesh = new THREE.Mesh(this.geometries.flash, material);
	mesh.position.copy(position);
	mesh.scale.set(startScale, startScale, startScale);
	this.scene.add(mesh);

	this.effects.push({
		mesh: mesh,
		material: material,
		age: 0,
		duration: duration,
		startScale: startScale,
		endScale: endScale
	});
};

bkcore.hexgl.Weapons.prototype.updateEffects = function(dtSec)
{
	for(var i = this.effects.length - 1; i >= 0; i--)
	{
		var effect = this.effects[i];
		effect.age += dtSec;

		var ratio = Math.min(1, effect.age / effect.duration);
		var scale = effect.startScale + (effect.endScale - effect.startScale) * ratio;
		effect.mesh.scale.set(scale, scale, scale);
		effect.material.opacity = (1 - ratio) * 0.9;

		if(ratio >= 1)
		{
			this.scene.remove(effect.mesh);
			this.effects.splice(i, 1);
		}
	}
};
