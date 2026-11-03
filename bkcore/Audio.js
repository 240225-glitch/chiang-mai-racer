var bkcore = bkcore || {};

bkcore.Audio = {};
bkcore.Audio.sounds = {};

bkcore.Audio.init = function(){
	if(window.AudioContext||window.webkitAudioContext){
		bkcore.Audio._ctx = new (window.AudioContext||window.webkitAudioContext)();
		bkcore.Audio._panner = bkcore.Audio._ctx.createPanner();
		bkcore.Audio._panner.connect(bkcore.Audio._ctx.destination);
	}
	else {
		bkcore.Audio._ctx = null;
	}

	bkcore.Audio.posMultipler = 1.5;
};

bkcore.Audio.init();

// Audio is optional. A missing file, failed decoder, or stalled request
// must not keep the asset loader (and the entire race) on the loading screen.
bkcore.Audio.addSound = function(src, id, loop, callback, usePanner) {
    var ctx = bkcore.Audio._ctx;
    var audio = ctx
        ? {src:null, gainNode:null, bufferNode:null, loop:loop, failed:false}
        : new Audio();
    var settled = false;
    var watchdog = null;
    bkcore.Audio.sounds[id] = audio;

    function finish(failed) {
        if (settled) return;
        settled = true;
        if (watchdog !== null) clearTimeout(watchdog);
        if (failed) {
            audio.failed = true;
            console.warn('Optional audio unavailable: ' + src);
        }
        if (typeof callback === 'function') callback(!failed);
    }

    // Covers an XHR that never finishes and a decoder that never calls back.
    watchdog = setTimeout(function() { finish(true); }, 15000);

    if (ctx) {
        var xhr = new XMLHttpRequest();
        xhr.responseType = 'arraybuffer';
        xhr.onload = function() {
            if (settled) return;
            // Local file:// loading may return status 0 with valid bytes.
            if ((xhr.status !== 0 && (xhr.status < 200 || xhr.status >= 300)) ||
                !xhr.response) {
                finish(true);
                return;
            }
            try {
                ctx.decodeAudioData(xhr.response, function(buffer) {
                    if (settled) return;
                    try {
                        var gain = ctx.createGain();
                        gain.connect(usePanner === true
                            ? bkcore.Audio._panner : ctx.destination);
                        audio.src = buffer;
                        audio.gainNode = gain;
                        finish(false);
                    } catch (error) {
                        finish(true);
                    }
                }, function() { finish(true); });
            } catch (error) {
                finish(true);
            }
        };
        xhr.onerror = xhr.onabort = xhr.ontimeout = function() {
            finish(true);
        };
        xhr.timeout = 15000;
        try {
            xhr.open('GET', src, true);
            xhr.send(null);
        } catch (error) {
            finish(true);
        }
    } else {
        // HTMLAudioElement fallback (older Safari / no Web Audio API).
        audio.addEventListener('canplay', function() {
            if (settled) return;
            audio.pause();
            audio.currentTime = 0;
            finish(false);
        }, false);
        audio.addEventListener('error', function() { finish(true); }, false);
        audio.addEventListener('abort', function() { finish(true); }, false);
        audio.preload = 'auto';
        audio.autoplay = true; // preserve the legacy fallback behaviour
        audio.loop = loop;
        try {
            audio.src = src;
        } catch (error) {
            finish(true);
        }
    }
};

bkcore.Audio.play = function(id) {
    var ctx = bkcore.Audio._ctx;
    var audio = bkcore.Audio.sounds[id];
    if (!audio || audio.failed) return false;
    if (ctx) {
        if (!audio.src || !audio.gainNode) return false;
        var sound = ctx.createBufferSource();
        sound.connect(audio.gainNode);
        sound.buffer = audio.src;
        sound.loop = audio.loop;
        audio.gainNode.gain.value = 1;
        audio.bufferNode = sound;
        sound.start ? sound.start(0) : sound.noteOn(0);
    } else {
        if (audio.currentTime > 0) {
            audio.pause();
            audio.currentTime = 0;
        }
        audio.play();
    }
    return true;
};

bkcore.Audio.stop = function(id) {
    var ctx = bkcore.Audio._ctx;
    var audio = bkcore.Audio.sounds[id];
    if (!audio || audio.failed) return false;
    if (ctx) {
        if (!audio.bufferNode) return false;
        var bufferNode = audio.bufferNode;
        audio.bufferNode = null; // stop() cannot be called twice on a source
        try {
            bufferNode.stop ? bufferNode.stop(ctx.currentTime) :
                bufferNode.noteOff(ctx.currentTime);
        } catch (error) {
            // The source may have already finished naturally.
        }
    } else {
        audio.pause();
        audio.currentTime = 0;
    }
    return true;
};

bkcore.Audio.volume = function(id, volume) {
    var ctx = bkcore.Audio._ctx;
    var audio = bkcore.Audio.sounds[id];
    if (!audio || audio.failed) return false;
    if (ctx) {
        if (!audio.gainNode) return false;
        audio.gainNode.gain.value = volume;
    } else {
        audio.volume = volume;
    }
    return true;
};

bkcore.Audio.setListenerPos = function(vec){
	if(bkcore.Audio._ctx){
		var panner = bkcore.Audio._panner;
		var vec2 = vec.normalize();
		panner.setPosition(
			vec2.x * bkcore.Audio.posMultipler,
			vec2.y * bkcore.Audio.posMultipler,
			vec2.z * bkcore.Audio.posMultipler
		);
	}
};

bkcore.Audio.setListenerVelocity = function(vec){
	if(bkcore.Audio._ctx){
		var panner = bkcore.Audio._panner;
		//panner.setVelocity(vec.x, vec.y, vec.z);
	}
};