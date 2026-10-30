# Credits & Third-Party Licenses

本文件记录项目中使用的所有第三方代码、模型、贴图、音频与数据。
**提交新资产时请同步更新本文件。**

---

## 1. 已包含在仓库中的内容

### HexGL（游戏基础）

- 项目：[BKcore/HexGL](https://github.com/BKcore/HexGL)
- 作者：Thibaut Despoulain（BKcore）
- 许可：**MIT License**
- 版权：Copyright (c) 2015 Thibaut Despoulain
- 使用范围：引擎框架、渲染管线、赛道系统、车辆控制、贴图、音频、UI 基础

### Three.js（渲染库）

- 项目：[mrdoob/three.js](https://github.com/mrdoob/three.js)
- 许可：**MIT License**
- 仓库内版本：`r50dev`（`libs/Three.dev.js`）、`r53`（`libs/Three.r53.js`）

### 音频与贴图

- 来源：HexGL 原始资源（见上）
- 许可：**MIT License**（除非文件内另有说明）
- 包含：背景音乐、引擎声、风声、赛道贴图、飞船贴图、UI 图像

---

## 2. 已使用的车辆资产（CC0）

以下资产已选定为「全低模 CC0」路线，转换产物已提交到 `assets/cars/`。原始下载包不进入仓库。

| 资产 | 作者 / 来源 | 许可 | 面数 | 状态 |
| --- | --- | --- | --- | --- |
| Kenney Car Kit | [Kenney](https://kenney.nl/assets/car-kit) | **CC0 1.0** | `race-future` 约 2,068 | ✅ 已转换入库 |
| Grab3D Race Car | [Grab3D](https://grab3d.com/models/vehicles/race-car/) | **CC0 1.0** | 19,440 | ✅ 已转换入库 |
| Quaternius Cars Pack | [Quaternius](https://quaternius.com/packs/cars.html) | **CC0 1.0** | 低模（8 辆） | 待下载 |

**入库路径**：

- `assets/cars/kenney-race-future/` — `model.json`、`textures/colormap.png`、`LICENSE.txt`
- `assets/cars/grab3d-race-car/` — `model.json`、`textures/race-car_body_basecolor.jpg`、`LICENSE.txt`

CC0 不强制署名，但本项目仍在此登记，感谢作者。

CC0 不强制署名，但本项目仍在此登记，感谢作者。

**推荐用途**

- 主赛车：Grab3D Race Car（比例真实）或 Kenney `race-future`（性能优先）
- 对手 / 交通车：Kenney `sedan`、`sedan-sports`、`suv`、`van`、`taxi`
- 补充车流：Quaternius Cars Pack

---

## 3. 计划使用的地标与道具（CC BY 4.0）

以下 Sketchfab 模型**尚未下载、尚未包含在仓库中**，仅作为制作候选登记。
如最终使用，必须在下文「CC BY 署名格式」中保留完整署名。

| 模型 | 作者 | 许可 | 面数 | 用途 |
| --- | --- | --- | --- | --- |
| [Wat Chedi Luang](https://sketchfab.com/3d-models/wat-chedi-luang-3296a81f50484797adcb53ba66183940) | [SphereView360 Thailand](https://sketchfab.com/SphereView360_Thailand) | CC BY 4.0 | 2,151 | 古城核心地标 |
| [Sutep Temple, Chiangmai Thailand](https://sketchfab.com/3d-models/sutep-temple-chiangmai-thailand-67909b569d7f4c3e8efbb34744b8f3aa) | [SphereView360 Thailand](https://sketchfab.com/SphereView360_Thailand) | CC BY 4.0 | 272,264 | 远景 / Doi Suthep 备选 |
| [Wat Chiang Man](https://sketchfab.com/3d-models/wat-chiang-man-chiangmai-35b45a11afca408abe7c03058df4bdf5) | [SphereView360 Thailand](https://sketchfab.com/SphereView360_Thailand) | CC BY 4.0 | 1,201,802 | 北门地标（需大幅减面） |
| [Thai Lanna Buddhist Temple](https://sketchfab.com/3d-models/thai-lanna-buddhist-temple-6add9dac765b457796bb4160970f11ec) | [kositsuwan](https://sketchfab.com/kositsuwan) | CC BY 4.0 | 487,454 | 建模参考 / 可重贴图 |
| [Thai Tuk-Tuk / Auto Rickshaw (Scaniverse LIDAR)](https://sketchfab.com/3d-models/thai-tuk-tuk-auto-rickshaw-scaniverse-lidar-e85c469ae3074ba9a8ed7c15340c178b) | [JFN](https://sketchfab.com/db4) | CC BY 4.0 | 77,570 | 清迈街景道具 |
| [Mazda RX7 Stylised](https://sketchfab.com/3d-models/mazda-rx7-stylised-898e9be8c8964f6298188a2901216e80) | [SheldonJ99](https://sketchfab.com/sheldonj99) | CC BY 4.0 | 5,737 | 半写实备选（当前不采用） |
| [Mazda MX5 Race Car](https://sketchfab.com/3d-models/mazda-mx5-race-car-0274225dde57412289e22a2f0febd847) | [Peter Stephan](https://sketchfab.com/Peter.Stephan) | CC BY 4.0 | 22,692 | 半写实备选（当前不采用） |
| [HCR Race Car](https://sketchfab.com/3d-models/hcr-race-car-1a35afde483f49f69a4a3c1da2df63e3) | [oakar258](https://sketchfab.com/oakar258) | CC BY 4.0 | 29,588 | 半写实备选（当前不采用） |
| [Generic passenger car pack](https://sketchfab.com/3d-models/generic-passenger-car-pack-20f9af9b8a404d5cb022ac6fe87f21f5) | [Comrade1280](https://sketchfab.com/comrade1280) | CC BY 4.0 | 69,312 | 交通车备选 |
| [2024 Porsche 992 GT3 R](https://sketchfab.com/3d-models/2024-porsche-992-gt3-r-b76c9b2ae2d548c3869426eac4ab8a19) | [Dave Love SketchFab](https://sketchfab.com/Tyler_Dave) | CC BY 4.0 | 489,304 | **不采用**：面数过高 + 品牌商标风险 |
| [Ford Capri Group B](https://sketchfab.com/3d-models/ford-capri-group-b-a8821371a98a4ccbad0beee12fd4f3e9) | [Tiaan.Pretorius](https://sketchfab.com/Tiaan.Pretorius) | CC BY 4.0 | 220,101 | **不采用**：面数过高 + 品牌商标风险 |

### CC BY 4.0 署名格式

使用上述任一模型时，在游戏制作名单与 `CREDITS.md` 中保留：

```text
"<模型名称>" by <作者>, licensed under CC BY 4.0.
Source: <Sketchfab URL>
License: https://creativecommons.org/licenses/by/4.0/
```

---

## 4. 地图数据与工具链

| 数据 / 工具 | 来源 | 许可 | 署名要求 |
| --- | --- | --- | --- |
| OpenStreetMap | <https://www.openstreetmap.org/> | **ODbL 1.0** | 必须署名 `© OpenStreetMap contributors`，衍生数据库按 ODbL 共享 |
| OSM2World | <https://osm2world.org/> | **MIT**（代码） | 保留版权声明；官网渲染图另为 CC BY-SA 2.0 |
| Blender | <https://www.blender.org/> | GPL | 工具本身不进入游戏产物 |
| BlenderGIS | <https://github.com/domlysz/BlenderGIS> | GPL | 工具本身不进入游戏产物 |
| Mapzen Terrain Tiles | <https://registry.opendata.aws/terrain-tiles/> | 开放数据（SRTM / GMTED 等） | 按 <https://github.com/tilezen/joerd/blob/master/docs/attribution.md> 署名 |
| Sentinel-2 cloudless | <https://cloudless.eox.at/> | 2016：CC BY 4.0；2018–2025：**CC BY-NC-SA 4.0** | 商用需另行授权；本项目默认不使用 |

### OSM 署名

游戏内制作名单、`README.md` 与发布页面需显示：

```text
Map data © OpenStreetMap contributors, available under the Open Database License (ODbL).
https://www.openstreetmap.org/copyright
```

---

## 5. 明确排除的资产

| 资产 | 原因 |
| --- | --- |
| `Compact Race Car`（Sketchfab） | 实际为经典 Mini，不是赛车，不符合主车定位 |
| Porsche / Ford 等真实品牌车型 | 商标与品牌授权风险；面数也不适合当前引擎 |
| 任何 CC BY-NC / 仅限个人使用 / 来源不明的模型 | 不符合开源与商用要求 |
| RenderHub「Chiang Mai Thailand 40km」 | 商业授权，非开源 |

---

## 6. 游戏内制作名单建议

发布版本应在制作名单中至少包含：

```text
Chiang Mai Racer
Based on HexGL by Thibaut Despoulain (MIT)

Vehicles: Kenney Car Kit (CC0), Quaternius (CC0), Grab3D (CC0)
Map data © OpenStreetMap contributors (ODbL)
3D conversion: OSM2World (MIT)
Terrain: Mapzen / SRTM / GMTED

Landmark models: see CREDITS.md (CC BY 4.0)
```

---

## 7. 许可原文

- MIT：<https://opensource.org/licenses/MIT>
- CC0 1.0：<https://creativecommons.org/publicdomain/zero/1.0/>
- CC BY 4.0：<https://creativecommons.org/licenses/by/4.0/>
- ODbL 1.0：<https://opendatacommons.org/licenses/odbl/1-0/>
