/*
 * Chiang Mai moat collision corridor for the legacy HexGL analyzers.
 * No external geometry or canvas pixel map is needed at runtime.
 *
 * Input (x,z) uses metres: +X east, +Z south. Existing ShipControls
 * expects an image-like getPixel/getPixelBilinear API. This adapter
 * supplies it while keeping the physics class unchanged.
 */
var bkcore = bkcore || {};
bkcore.hexgl = bkcore.hexgl || {};

bkcore.hexgl.MoatCollision = (function () {
    var WHITE={r:255,g:255,b:255};
    var OUTSIDE={r:0,g:0,b:0};
    var BOOST={r:255,g:0,b:0};
    var CHECKPOINTS=[
        {r:255,g:255,b:0},{r:255,g:255,b:1},
        {r:255,g:255,b:2},{r:255,g:255,b:3}
    ];
    var CELL=80;

    function Collision(route) {
        if (!route || !route.closed || !route.points || route.points.length < 4)
            throw new Error('MoatCollision: missing closed route');
        if (route.points.length > 10000)
            throw new Error('MoatCollision: too many road points');
        // Invalid width used to turn the entire world into drivable road:
        // distance > NaN is always false, and negative widths were squared.
        if (typeof route.road_width_m !== 'number' ||
            !isFinite(route.road_width_m) || route.road_width_m <= 0)
            throw new Error('MoatCollision: invalid road width');
        var validSegments=0;
        for(var p=0;p<route.points.length;p++) {
            var point=route.points[p],next=route.points[(p+1)%route.points.length];
            if(!point || point.length!==2 || !next || next.length!==2 ||
               !isFinite(point[0]) || !isFinite(point[1]) ||
               typeof point[0]!=='number' || typeof point[1]!=='number')
                throw new Error('MoatCollision: invalid road point');
            if(point[0]!==next[0] || point[1]!==next[1]) validSegments++;
        }
        if(!validSegments) throw new Error('MoatCollision: zero-length route');
        this.route=route;
        this.points=route.points;
        this.loaded=true;
        this.pixels={width:0,height:0}; // already in world metres
        this.halfWidth=route.road_width_m / 2;
        this.buckets={};
        this.boostPoints=[
            this.points[Math.floor(this.points.length*0.055)],
            this.points[Math.floor(this.points.length*0.38)],
            this.points[Math.floor(this.points.length*0.70)]
        ];
        var padding=this.halfWidth+12;
        // Queries within this padded index are guaranteed to include the
        // nearest segment; only distant queries need the global fallback.
        this.searchPaddingSquared=padding*padding;
        // Validate the complete index before allocating buckets. A finite
        // but corrupt coordinate or width can otherwise generate millions
        // of cells and freeze the tab before Cityscape fallback can run.
        var spans=[],bucketInsertions=0,measuredLength=0;
        for(var i=0;i<this.points.length;i++) {
            var a=this.points[i],b=this.points[(i+1)%this.points.length];
            var dx=b[0]-a[0],dz=b[1]-a[1];
            var segmentLength=Math.sqrt(dx*dx+dz*dz);
            if(!isFinite(segmentLength))
                throw new Error('MoatCollision: invalid segment length');
            measuredLength+=segmentLength;
            var x0=Math.floor((Math.min(a[0],b[0])-padding)/CELL);
            var x1=Math.floor((Math.max(a[0],b[0])+padding)/CELL);
            var z0=Math.floor((Math.min(a[1],b[1])-padding)/CELL);
            var z1=Math.floor((Math.max(a[1],b[1])+padding)/CELL);
            var cells=(x1-x0+1)*(z1-z0+1);
            if(!isFinite(cells) || cells>4096 ||
               bucketInsertions+cells>100000)
                throw new Error('MoatCollision: spatial index too large');
            bucketInsertions+=cells;
            spans.push([x0,x1,z0,z1]);
        }
        // The generator includes the complete closed-loop length. If one
        // sampled point is displaced, the centreline can cross the city
        // while start/checkpoints still look valid. Reject that mismatch.
        if(route.length_m !== undefined &&
           (typeof route.length_m!=='number' ||
            !isFinite(route.length_m) || route.length_m<=0 ||
            !isFinite(measuredLength) ||
            Math.abs(measuredLength-route.length_m)>
                Math.max(1,route.length_m*0.02)))
            throw new Error('MoatCollision: route length mismatch');
        for(var i=0;i<spans.length;i++) {
            var span=spans[i];
            for(var x=span[0];x<=span[1];x++)
                for(var z=span[2];z<=span[3];z++) {
                    var key=x+':'+z;
                    (this.buckets[key] || (this.buckets[key]=[])).push(i);
                }
        }
    }

    Collision.prototype.distanceSquared=function(x,z) {
        var key=Math.floor(x/CELL)+':'+Math.floor(z/CELL);
        var hits=this.buckets[key];
        var result=Infinity;
        // The bucket index is exact only within its construction padding.
        // Farther away, another segment in a neighbouring bucket may be
        // closer. Scan the whole route only for such off-road queries.
        for(var pass=0;pass<(hits ? 2 : 1);pass++) {
            var fullScan=pass===1 || !hits;
            var count=fullScan ? this.points.length : hits.length;
            for(var j=0;j<count;j++) {
                var i=fullScan ? j : hits[j];
                var a=this.points[i],b=this.points[(i+1)%this.points.length];
                var vx=b[0]-a[0],vz=b[1]-a[1];
                var length2=vx*vx+vz*vz;
                if(length2<1e-9) continue;
                var t=Math.max(0,Math.min(1,((x-a[0])*vx+(z-a[1])*vz)/length2));
                var dx=x-a[0]-t*vx,dz=z-a[1]-t*vz;
                var dist=dx*dx+dz*dz;
                if(dist<result) result=dist;
            }
            if(fullScan || result<=this.searchPaddingSquared) break;
        }
        return result;
    };

    // The original Cityscape collision bitmap treats a car a couple of
    // metres outside the road as a fall into empty space. On an OSM road,
    // that is an ordinary shoulder impact: clamp the physics root inside
    // the corridor, apply a speed penalty and let the player steer away.
    //
    // Use the spatial index on normal frames; only a car already far away
    // needs the full scan (e.g. a teleport or an unusually long frame).
    Collision.prototype.projectInside=function(x,z,margin) {
        if(!isFinite(x) || !isFinite(z))
            throw new Error('MoatCollision: non-finite vehicle position');
        var key=Math.floor(x/CELL)+':'+Math.floor(z/CELL);
        var hits=this.buckets[key];
        var best=Infinity,px=x,pz=z;
        // A populated bucket does not guarantee the globally nearest road
        // segment for a vehicle teleported well outside the road. When the
        // closest indexed segment exceeds the index padding, fall back to
        // a full scan instead of snapping the car to the wrong street.
        for(var pass=0;pass<(hits ? 2 : 1);pass++) {
            var fullScan=pass===1 || !hits;
            var count=fullScan ? this.points.length : hits.length;
            for(var j=0;j<count;j++) {
                var i=fullScan ? j : hits[j];
                var a=this.points[i],b=this.points[(i+1)%this.points.length];
                var vx=b[0]-a[0],vz=b[1]-a[1];
                var length2=vx*vx+vz*vz;
                if(length2<1e-9) continue;
                var t=Math.max(0,Math.min(1,
                    ((x-a[0])*vx+(z-a[1])*vz)/length2));
                var cx=a[0]+t*vx,cz=a[1]+t*vz;
                var dx=x-cx,dz=z-cz,dist=dx*dx+dz*dz;
                if(dist<best) {best=dist;px=cx;pz=cz;}
            }
            if(fullScan || best<=this.searchPaddingSquared) break;
        }
        if(best<=this.halfWidth*this.halfWidth)
            return {x:x,z:z,corrected:false,distanceSquared:best};
        // Do not use a fixed minimum inset: for a narrow imported road,
        // 0.5m can be farther than its half-width and recovery remains
        // outside the collision corridor on every subsequent frame.
        var allowance=Math.max(0,this.halfWidth-Math.max(0,margin||0));
        var length=Math.sqrt(best);
        return {
            x:px+(x-px)*allowance/length,
            z:pz+(z-pz)*allowance/length,
            corrected:true,
            distanceSquared:best
        };
    };

    // A physics step can jump between separate road ribbons even when both
    // endpoints are legal. Fixed-distance sampling misses gaps smaller than
    // its step size. Instead certify each swept interval using the fact that
    // distance to the nearest road segment is 1-Lipschitz: for endpoint
    // distances d0/d1 and interval length L, every interior distance is at
    // most (d0+d1+L)/2. Only subdivide intervals not proven to be on-road.
    // This detects narrow gaps without penalising ordinary centre-lane
    // frames. A 2cm proof tolerance avoids false shoulder hits from tiny
    // floating-point/geometry variations; this is not exact CCD.
    // Work is bounded; ambiguous pathological moves stop at the
    // last certified position rather than allowing a shortcut.
    Collision.prototype.projectMovement=function(startX,startZ,endX,endZ,margin,checkingRecovery) {
        var end=this.projectInside(endX,endZ,margin);
        if(!isFinite(startX) || !isFinite(startZ))
            throw new Error('MoatCollision: non-finite previous position');
        var dx=endX-startX,dz=endZ-startZ;
        var length=Math.sqrt(dx*dx+dz*dz);
        if(length===0) return end;
        // Short off-road steps usually need a gentle shoulder projection.
        // However the nearest projection can belong to a *different* road
        // across a sub-metre gap. Certify the swept path to the projected
        // point before accepting recovery, rather than teleporting there.
        // The internal check skips this branch to avoid recursion loops.
        if(end.corrected && length<=1 && !checkingRecovery) {
            var recovery=this.projectMovement(startX,startZ,end.x,end.z,margin,true);
            return recovery.corrected ? recovery : end;
        }
        // Any point on the path is at most L farther from the road than
        // the endpoint. Most normal frames are certified by this one check.
        var radius=this.halfWidth;
        if(!end.corrected && Math.sqrt(end.distanceSquared)+length<=radius)
            return end;
        // An invalid spawn/teleport is recovered by the endpoint adapter.
        var startDist=Math.sqrt(this.distanceSquared(startX,startZ));
        if(startDist>radius) return end;
        // Bound pathological teleports without an unbounded collision loop.
        if(!isFinite(length) || length>256)
            return {x:startX,z:startZ,corrected:true,distanceSquared:Infinity};
        var stack=[{t0:0,t1:1,d0:startDist,d1:Math.sqrt(end.distanceSquared),depth:0}];
        var safeX=startX,safeZ=startZ,checks=0;
        while(stack.length) {
            var part=stack.pop();
            var span=length*(part.t1-part.t0);
            if((part.d0+part.d1+span)*0.5<=radius+0.02) {
                safeX=startX+dx*part.t1;
                safeZ=startZ+dz*part.t1;
                continue;
            }
            if(part.depth>=20 || checks>=256)
                return {x:safeX,z:safeZ,corrected:true,distanceSquared:Infinity};
            var mid=(part.t0+part.t1)*0.5;
            var mx=startX+dx*mid,mz=startZ+dz*mid;
            var midSquared=this.distanceSquared(mx,mz);
            checks++;
            if(midSquared>radius*radius)
                return {x:safeX,z:safeZ,corrected:true,distanceSquared:midSquared};
            var midDist=Math.sqrt(midSquared);
            // LIFO: process the earlier half first, preserving the last
            // certified road position if a later interval is invalid.
            stack.push({t0:mid,t1:part.t1,d0:midDist,d1:part.d1,depth:part.depth+1});
            stack.push({t0:part.t0,t1:mid,d0:part.d0,d1:midDist,depth:part.depth+1});
        }
        return end;
    };

    Collision.prototype.getPixel=function(x,z) {
        var d=this.distanceSquared(x,z);
        if(d>this.halfWidth*this.halfWidth) return OUTSIDE;
        for(var i=0;i<this.route.checkpoints.length;i++) {
            var cp=this.route.checkpoints[i],dx=x-cp.x,dz=z-cp.z;
            if(dx*dx+dz*dz<144) return CHECKPOINTS[i];
        }
        for(var j=0;j<this.boostPoints.length;j++) {
            var p=this.boostPoints[j],bx=x-p[0],bz=z-p[1];
            if(bx*bx+bz*bz<144) return BOOST;
        }
        return WHITE;
    };

    Collision.prototype.getPixelBilinear=function(x,z) {
        return this.getPixel(x,z);
    };

    function HeightMap() {
        this.loaded=true;
        this.pixels={width:0,height:0};
    }
    HeightMap.prototype.getPixelFBilinear=function(x,z){ return 0; };
    HeightMap.prototype.getPixel=function(x,z){ return WHITE; };
    return {Collision:Collision,HeightMap:HeightMap};
})();
