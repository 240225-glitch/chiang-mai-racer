/*
 * Opt-in CC0 vehicle visuals on the unmodified HexGL physics root.
 * Keep the legacy ship geometry visible until the model is ready; failures
 * never block driving. Browser globals only (Three.js r50dev).
 */
var bkcore = bkcore || {};
bkcore.hexgl = bkcore.hexgl || {};

bkcore.hexgl.VehicleModels = (function () {
    var variants = {
        grab3d: 'assets/cars/grab3d-race-car/model.json',
        kenney: 'assets/cars/kenney-race-future/model.json'
    };

    function options(search) {
        search = search || '';
        return {
            legacy: /(?:^|[?&])ship=1(?:&|$)/.test(search),
            primary: /(?:^|[?&])car=kenney(?:&|$)/.test(search) ? 'kenney' : 'grab3d'
        };
    }

    function attach(shipObject, controls, camera, variant, loader) {
        var url = variants[variant];
        if (!url || !loader || !shipObject || !shipObject.ship) return;

        loader.load(url, function (model) {
            // Geometry is centered around ground level. The old height-map
            // physics root floats heightBias (4m) above the road.
            model.position.set(0, -controls.heightBias, 0);
            shipObject.ship.add(model);
            shipObject.legacy.visible = false;
            shipObject.vehicleModel = model;
            shipObject.variant = variant;

            var bounds = model.modelData && model.modelData.bounds;
            if (bounds && bounds.min && bounds.max) {
                var width = bounds.max[0] - bounds.min[0];
                controls.repulsionVScale = Math.max(1.2, Math.min(2.0, width * 0.75));
            }
            if (camera) {
                camera.yoffset = 4.5;
                camera.zoffset = 13;
                camera.viewOffset = 7;
            }
        }, function (error) {
            // Leave the fallback visible if a texture/JSON/model fails.
            if (typeof console !== 'undefined' && console.warn)
                console.warn('Vehicle load failed, using original ship:', url, error);
        });
    }

    function attachShips(ships, controls, cameras, twoPlayer, search, loader) {
        var config = options(search);
        if (config.legacy) return;
        var other = config.primary === 'grab3d' ? 'kenney' : 'grab3d';
        for (var i = 0; i < ships.length && i < (twoPlayer ? 2 : 1); i++) {
            attach(ships[i], controls[i], cameras[i], i === 0 ? config.primary : other, loader);
        }
    }

    return { attachShips: attachShips, options: options };
})();
