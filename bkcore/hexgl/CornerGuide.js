/*
 * Optional game-only corner guidance for the OSM moat prototype.
 * Uses the loaded route centreline; no automatic steering, map edits or
 * modern Three.js APIs. This is not a real-world traffic warning system.
 */
var bkcore = bkcore || {};
bkcore.hexgl = bkcore.hexgl || {};

bkcore.hexgl.CornerGuide = (function() {
    function Guide(route, elements) {
        if (!route || !route.points || route.points.length < 3)
            throw new Error('CornerGuide: invalid route');
        this.points = route.points;
        // The OSM route is sampled every ~10m. A car inside the 14m road
        // remains within ~9m of a sample even between adjacent points.
        // Use a small allowance rather than accepting a stale sample up to
        // 30m away (which can belong to a different nearby road).
        var roadWidth = route.road_width_m > 0 ? route.road_width_m : 14;
        this.maxSampleDistanceSquared = Math.pow(roadWidth/2 + 4, 2);
        this.elements = elements || [];
        this.lastIndices = [-1, -1];
        this.tick = 0;
        this.distances = [0];
        this.segments = [];
        var n = this.points.length, i;
        for (i = 0; i < n; i++) {
            var a = this.points[i], b = this.points[(i+1)%n];
            var vx=b[0]-a[0],vz=b[1]-a[1];
            var length2=vx*vx+vz*vz;
            var d=Math.sqrt(length2);
            if (!(d > 0) || !isFinite(d)) throw new Error('CornerGuide: invalid segment');
            this.distances.push(this.distances[i]+d);
            // Precompute once: per-frame nearest-road queries use bounds to
            // skip far-away segments without sacrificing exact projection.
            this.segments.push({
                x:a[0],z:a[1],vx:vx,vz:vz,invLen2:1/length2,
                minx:Math.min(a[0],b[0]),maxx:Math.max(a[0],b[0]),
                minz:Math.min(a[1],b[1]),maxz:Math.max(a[1],b[1])
            });
        }
        this.length = this.distances[n];
        // Index each segment's padded bounds. Every segment within the HUD
        // road tolerance is guaranteed to appear in the current 80m cell.
        // This keeps exact segment projection cheap even in split-screen.
        this.buckets={};
        var cellSize=80,padding=Math.sqrt(this.maxSampleDistanceSquared);
        var insertions=0;
        for (i=0;i<n;i++) {
            var seg=this.segments[i];
            var x0=Math.floor((seg.minx-padding)/cellSize);
            var x1=Math.floor((seg.maxx+padding)/cellSize);
            var z0=Math.floor((seg.minz-padding)/cellSize);
            var z1=Math.floor((seg.maxz+padding)/cellSize);
            var cells=(x1-x0+1)*(z1-z0+1);
            if (!isFinite(cells) || cells>4096 || insertions+cells>100000)
                throw new Error('CornerGuide: spatial index too large');
            insertions+=cells;
            for (var x=x0;x<=x1;x++) for (var z=z0;z<=z1;z++) {
                var key=x+':'+z;
                (this.buckets[key] || (this.buckets[key]=[])).push(i);
            }
        }
        var candidates = [];
        for (i = 0; i < n; i++) {
            var before = this.points[(i+n-1)%n], at = this.points[i];
            var after = this.points[(i+1)%n];
            var ux = at[0]-before[0], uz = at[1]-before[1];
            var vx = after[0]-at[0], vz = after[1]-at[1];
            var angle = Math.atan2(ux*vz-uz*vx, ux*vx+uz*vz)*180/Math.PI;
            if (Math.abs(angle) >= 28) candidates.push({index:i,angle:angle});
        }
        candidates.sort(function(a,b) {
            return Math.abs(b.angle)-Math.abs(a.angle) || a.index-b.index;
        });
        this.turns = [];
        for (i = 0; i < candidates.length; i++) {
            var turn = candidates[i], keep = true;
            for (var j = 0; j < this.turns.length; j++) {
                var gap = Math.abs(this.distances[turn.index]-
                                   this.distances[this.turns[j].index]);
                if (Math.min(gap,this.length-gap) < 45) {keep=false;break;}
            }
            if (keep) this.turns.push(turn);
        }
    }

    Guide.prototype.hide = function() {
        for (var i=0;i<this.elements.length;i++)
            if (this.elements[i]) this.elements[i].style.display='none';
    };

    Guide.prototype.reset = function() {
        this.lastIndices=[-1,-1];
        this.tick=0;
        this.hide();
    };

    // Locate against continuous centreline segments, not just their sampled
    // endpoints. A car exactly on one road between two 10m samples can be
    // closer to a sample on an adjacent road, yielding the wrong warning.
    Guide.prototype.locate = function(x,z,player) {
        if (!isFinite(x) || !isFinite(z)) return null;
        var segments=this.segments;
        var key=Math.floor(x/80)+':'+Math.floor(z/80);
        var hits=this.buckets[key] || [];
        var previous=this.lastIndices[player],best=Infinity,index=-1,bestT=0;
        for (var j=0;j<hits.length;j++) {
            var i=hits[j],seg=segments[i];
            var t=Math.max(0,Math.min(1,
                ((x-seg.x)*seg.vx+(z-seg.z)*seg.vz)*seg.invLen2));
            var dx=x-seg.x-t*seg.vx,dz=z-seg.z-t*seg.vz;
            var d=dx*dx+dz*dz;
            // Prefer the previous segment at crossings, and a segment start
            // over the preceding segment's endpoint at shared vertices.
            var tied=Math.abs(d-best)<=1e-9;
            if (d<best-1e-9 || (tied &&
                ((i===previous && index!==previous) ||
                 (index!==previous && t<bestT-1e-9)))) {
                best=d;index=i;bestT=t;
            }
        }
        if (index<0 || best>this.maxSampleDistanceSquared) return null;
        this.lastIndices[player]=index;
        return {index:index,t:bestT};
    };

    // Retain the index-only API for existing callers and diagnostics.
    Guide.prototype.nearestIndex = function(x,z,player) {
        var position=this.locate(x,z,player);
        return position ? position.index : -1;
    };

    Guide.prototype.warningAt = function(index,t) {
        if (index<0) return null;
        var fraction=t===undefined ? 0 : t;
        var at=this.distances[index]+
               fraction*(this.distances[index+1]-this.distances[index]);
        var nearest=null;
        for (var i=0;i<this.turns.length;i++) {
            var turn=this.turns[i];
            var ahead=(this.distances[turn.index]-at+this.length)%this.length;
            if (ahead<=150 && (!nearest || ahead<nearest.distance))
                nearest={distance:ahead,// +Y is up and the car faces local +Z. Positive yaw
                         // steers LEFT, so the (x,z) cross sign is reversed:
                         // +Z to +X is left (negative cross product).
                         side:turn.angle>0?'右':'左',
                         index:turn.index};
        }
        return nearest;
    };

    // Turn arrows assume travel in the OSM route direction. When a car is
    // facing back along the road (for example after a spin), the same arrow
    // would describe the wrong turn. Hide it until the car faces forward.
    // r50 uses +Z as the vehicle's forward axis; read the physics dummy's
    // quaternion rather than the visual body tilt or current velocity.
    Guide.prototype.isWrongWay = function(index,quaternion) {
        if (!quaternion) return false;
        var q=quaternion;
        if (!isFinite(q.x) || !isFinite(q.y) || !isFinite(q.z) ||
            !isFinite(q.w)) return false;
        var fx=2*(q.x*q.z+q.w*q.y);
        var fz=1-2*(q.x*q.x+q.y*q.y);
        var seg=this.segments[index];
        var norm=Math.sqrt((fx*fx+fz*fz)/seg.invLen2);
        return norm>1e-6 && (fx*seg.vx+fz*seg.vz)/norm < -0.5;
    };

    Guide.prototype.update = function(controls,gameplays) {
        // At 60fps update DOM at 10Hz, while retaining smooth physics frames.
        if (++this.tick%6 !== 0) return;
        for (var i=0;i<this.elements.length;i++) {
            var el=this.elements[i],control=controls[i],game=gameplays[i];
            if (!el) continue;
            if (!control || !control.dummy || !control.dummy.position ||
                !control.active || !game || !game.active || game.step!==4) {
                el.style.display='none';
                continue;
            }
            var pos=control.dummy.position;
            var location=this.locate(pos.x,pos.z,i);
            var warning=location && !this.isWrongWay(location.index,control.dummy.quaternion)
                ? this.warningAt(location.index,location.t) : null;
            if (!warning) {el.style.display='none';continue;}
            el.textContent='急弯向'+warning.side+' · '+Math.round(warning.distance)+' 米';
            el.style.display='block';
        }
    };
    return Guide;
})();
