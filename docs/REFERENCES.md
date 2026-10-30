# 参考资料 / References

按主题整理，方便后续制作与署名核对。

---

## 1. 上游项目与引擎

| 名称 | 链接 | 说明 |
| --- | --- | --- |
| HexGL | <https://github.com/BKcore/HexGL> | 本项目基础，MIT |
| HexGL 官网 | <http://hexgl.bkcore.com/> | 原版可玩 Demo |
| Three.js | <https://github.com/mrdoob/three.js> | 渲染库，MIT |
| Three.js r50 源码 | <https://github.com/mrdoob/three.js/tree/r50> | 当前引擎对应版本参考 |
| Three.js r53 源码 | <https://github.com/mrdoob/three.js/tree/r53> | 仓库内备用版本 |

---

## 2. 地图数据与工具

| 名称 | 链接 | 许可 / 备注 |
| --- | --- | --- |
| OpenStreetMap | <https://www.openstreetmap.org/> | ODbL 1.0 |
| OSM 版权说明 | <https://www.openstreetmap.org/copyright> | 署名要求 |
| Overpass API | <https://overpass-api.de/> | 按 bbox 提取 OSM 数据 |
| OSM2World | <https://osm2world.org/> | MIT，OSM → glTF / OBJ |
| OSM2World 源码 | <https://github.com/tordanik/OSM2World> | Java |
| Blender | <https://www.blender.org/> | GPL，建模 / 减面 / 烘焙 |
| BlenderGIS | <https://github.com/domlysz/BlenderGIS> | GPL，Blender 地理数据插件 |
| Mapzen Terrain Tiles | <https://registry.opendata.aws/terrain-tiles/> | AWS 开放数据 |
| Mapzen 署名说明 | <https://github.com/tilezen/joerd/blob/master/docs/attribution.md> | 高程数据署名 |
| Sentinel-2 cloudless | <https://cloudless.eox.at/> | 2018–2025 为 CC BY-NC-SA，商用注意 |

### 环线参考

| 名称 | 链接 | 说明 |
| --- | --- | --- |
| The moat loop — Roads of Chiang Mai | <https://motdang.net/roads/rings/moat-loop/> | 6.54 km、1948 年单行体系 |
| Chiang Mai（Wikipedia） | <https://en.wikipedia.org/wiki/Chiang_Mai> | 城市背景 |
| Wat Chedi Luang（Wikipedia） | <https://en.wikipedia.org/wiki/Wat_Chedi_Luang> | 地标背景 |

---

## 3. 车辆资产

### CC0（当前路线）

| 名称 | 链接 | 许可 | 面数 |
| --- | --- | --- | --- |
| Kenney Car Kit | <https://kenney.nl/assets/car-kit> | CC0 1.0 | `race-future` 约 2,068 |
| Kenney Car Kit（OpenGameArt 镜像） | <https://opengameart.org/content/car-kit> | CC0 1.0 | 同上 |
| Quaternius Cars Pack | <https://quaternius.com/packs/cars.html> | CC0 1.0 | 8 辆低模 |
| Grab3D Race Car | <https://grab3d.com/models/vehicles/race-car/> | CC0 1.0 | 19,440 |

### CC BY 4.0（备选）

| 名称 | 链接 | 面数 |
| --- | --- | --- |
| Mazda RX7 Stylised | <https://sketchfab.com/3d-models/mazda-rx7-stylised-898e9be8c8964f6298188a2901216e80> | 5,737 |
| Mazda MX5 Race Car | <https://sketchfab.com/3d-models/mazda-mx5-race-car-0274225dde57412289e22a2f0febd847> | 22,692 |
| HCR Race Car | <https://sketchfab.com/3d-models/hcr-race-car-1a35afde483f49f69a4a3c1da2df63e3> | 29,588 |
| Generic passenger car pack | <https://sketchfab.com/3d-models/generic-passenger-car-pack-20f9af9b8a404d5cb022ac6fe87f21f5> | 69,312 |

> Sketchfab 下载需要登录；批量获取需要 API token。

---

## 4. 清迈地标资产

| 名称 | 链接 | 作者 | 许可 | 面数 |
| --- | --- | --- | --- | --- |
| Wat Chedi Luang | <https://sketchfab.com/3d-models/wat-chedi-luang-3296a81f50484797adcb53ba66183940> | SphereView360 Thailand | CC BY 4.0 | 2,151 |
| Sutep Temple | <https://sketchfab.com/3d-models/sutep-temple-chiangmai-thailand-67909b569d7f4c3e8efbb34744b8f3aa> | SphereView360 Thailand | CC BY 4.0 | 272,264 |
| Wat Chiang Man | <https://sketchfab.com/3d-models/wat-chiang-man-chiangmai-35b45a11afca408abe7c03058df4bdf5> | SphereView360 Thailand | CC BY 4.0 | 1,201,802 |
| Thai Lanna Buddhist Temple | <https://sketchfab.com/3d-models/thai-lanna-buddhist-temple-6add9dac765b457796bb4160970f11ec> | kositsuwan | CC BY 4.0 | 487,454 |
| Thai Tuk-Tuk（LiDAR） | <https://sketchfab.com/3d-models/thai-tuk-tuk-auto-rickshaw-scaniverse-lidar-e85c469ae3074ba9a8ed7c15340c178b> | JFN | CC BY 4.0 | 77,570 |

---

## 5. 许可文本

| 许可 | 链接 |
| --- | --- |
| MIT | <https://opensource.org/licenses/MIT> |
| CC0 1.0 | <https://creativecommons.org/publicdomain/zero/1.0/> |
| CC BY 4.0 | <https://creativecommons.org/licenses/by/4.0/> |
| ODbL 1.0 | <https://opendatacommons.org/licenses/odbl/1-0/> |

---

## 6. 视觉与玩法参考方向

- **速度感**：HexGL 原版的低空飞行、隧道、加速带与氮气节奏。
- **城市尺度**：清迈古城真实街区比例，护城河、城墙、城门构成边界。
- **美术风格**：低多边形 + 暖色 Lanna 色板（陶土红、柚木棕、金色寺顶、热带绿）。
- **车辆风格**：Kenney / Quaternius 的扁平色块与简洁轮廓，避免高模 PBR。
- **氛围道具**：Tuk-Tuk、Songthaew、寺庙灯笼、电线、热带树木。
- **HUD**：沿用现有中文 HUD，新增赛道名与地标提示。

---

## 7. 待补充

- [ ] 清迈街景照片参考（需使用可商用 / 自摄素材）
- [ ] Songthaew 低模参考
- [ ] 城门与城墙尺寸测绘
- [ ] 护城河宽度与桥梁位置
- [ ] 泰国本地化文本（赛道名、地标名）
