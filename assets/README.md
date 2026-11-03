# assets

运行时可用的转换产物。原始下载包放在 `assets-src/`，该目录已被 `.gitignore` 忽略。

## 目录

```text
assets/
  cars/
    grab3d-race-car/
      model.json          # cmr-static-v1
      textures/
        race-car_body_basecolor.jpg
      LICENSE.txt         # CC0
    kenney-race-future/
      model.json
      textures/
        colormap.png
      LICENSE.txt         # CC0
```

## 当前资产

| 资产 | 来源 | 许可 | 三角面 | 尺寸（m） |
| --- | --- | --- | --- | --- |
| Grab3D Race Car | <https://grab3d.com/models/vehicles/race-car/> | CC0 1.0 | 19,440 | 1.92 × 1.02 × 5.28 |
| Kenney `race-future` | <https://kenney.nl/assets/car-kit> | CC0 1.0 | 2,068 | 1.99 × 1.38 × 4.40 |

## 重新生成

```bash
python tools/obj2json.py assets-src/grab3d/race-car/race-car.obj \
  assets/cars/grab3d-race-car/model.json \
  --name grab3d-race-car --license CC0-1.0 --author Grab3D \
  --target-length 5.28 --center --merge-untextured

python tools/obj2json.py assets-src/kenney/race-future.obj \
  assets/cars/kenney-race-future/model.json \
  --name kenney-race-future --license CC0-1.0 --author Kenney \
  --target-length 4.4 --center --merge-untextured
```

## 注意

- `model.json` 是运行时格式，不要手工编辑。
- 贴图路径相对于 `model.json`。
- 新增资产必须同步更新 `CREDITS.md` 和 `docs/ASSETS.md`。
- 不要提交 `assets-src/` 里的原始压缩包。

## OSM 外圈赛道（ODbL）

- assets/tracks/chiangmai-moat/source-osm.geojson：2026-10-31 OSM 官方 API 提取的 90 个 way 的闭环中心线，数据许可 ODbL 1.0。
- road.json、route.json、route-data.js：使用 tools/build_moat_blockout.py 默认从 source-osm.geojson 再生成，约 6.49 km，4,274 tris（含 19 块 OSM 水体）；不要手工改生成产物。
- OSM 数据来源、原始 XML SHA 和重现方式：docs/OSM-PROVENANCE.md。
- 水面来自 OSM water=moat 多边形；路宽与检查点仍是游戏示意；第三方地图数据不是 CC0。

- source-water-osm.geojson：同一 2026-10-31 OSM API 快照提取的 19 块 water=moat 多边形（ODbL），生成器离线耳切三角化，230 个三角面。来源见 docs/OSM-PROVENANCE.md。


## M3 OSM 临街建筑（ODbL）

source-buildings-osm.geojson：2026-10-31 同一 OSM XML 快照提取的 815 栋临街建筑轮廓，含 OSM way ID、ODbL 许可、源 XML SHA。39 栋高度按 OSM 楼层标签推算，776 栋为可复现的游戏估算；不能标成 CC0、实测建筑高度或历史外观。road.json 新增合并立面/屋顶两张网格，默认全场景 9 meshes、15,942 tris（含游戏示意中心虚线）；来源和复现见 docs/OSM-PROVENANCE.md。
