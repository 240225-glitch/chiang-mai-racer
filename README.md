# Chiang Mai Racer · 清迈古城竞速

> 一个开源的 3D 街机竞速游戏：把泰国清迈古城护城河环线做成可玩的赛道。
> 基于 [HexGL](https://github.com/BKcore/HexGL)（MIT）继续开发。

**English** — Chiang Mai Racer is an arcade racer based on HexGL. The optional ?track=moat mode combines a 6.49 km OSM-derived outer road, 19 moat-water polygons, four mapped city gates, 815 roadside building footprints and a procedural Wat Chedi Luang landmark blockout. The default Cityscape remains available. OSM-derived data is ODbL; road width, building heights and 3D landmark appearance are stylized. Headless WebGL tests pass; real-GPU and field verification remain pending.

---

## 项目状态

| 模块 | 状态 |
| --- | --- |
| 单人计时、同屏双人分屏、氮气、1/3/5 圈、暂停/重开、最佳成绩、中文结算 | ✅ 已完成并有回归验证 |
| 车辆资产选型 | ✅ 已完成，确定「全低模 CC0」路线 |
| 清迈地图方案 | ✅ 已确定「古城护城河环线」，全长约 6.54 km |
| 旧版 Three.js 资产转换管线 | ✅ 原型完成：OBJ → JSON + 运行时加载器 + 预览页 |
| 清迈赛道 | 🚧 M2 OSM 外圈道路（6.49 km、90 ways）、19 块水体、4 座城门、815 栋临街建筑和 Wat Chedi Luang 低模地标已接入 ?track=moat；真实 GPU 与现场核验待完成 |
| 新车辆接入主游戏 | ✅ Cityscape 已接入 Grab3D / Kenney CC0 车型并通过 headless WebGL 冒烟；真实 GPU 和目标设备试玩待完成 |

> 默认游戏仍使用 Cityscape；访问 ?track=moat 可进入清迈古城 M2/M3 开发测试模式。该模式包含 OSM 道路、水体、城门节点、815 栋临街建筑和 Wat Chedi Luang 低模地标。道路宽度、建筑高度和建筑/地标三维外观有程序化示意成分；headless WebGL 冒烟通过，但真实 GPU、实地路况和人工完整驾驶尚未验收。数据来源见 [OSM 记录](docs/OSM-PROVENANCE.md)。

## 目标

1. 用清迈古城护城河环线替换现有 Cityscape 赛道。
2. 使用 CC0 低多边形车辆，保证许可干净、性能可控。
3. 保留并完善现有玩法：单人计时、同屏双人、氮气、圈数、暂停/重开、最佳成绩、中文结算。
4. 在旧版 Three.js（`r50dev`）上建立可复用的 OBJ → 自定义 JSON 资产管线。
5. 所有第三方资产在 [CREDITS.md](CREDITS.md) 中可追溯。

## 为什么是清迈古城

- 护城河环线是天然闭环：约 **6.54 km**，方形旧城，外圈顺时针、内圈逆时针，1948 年形成。
- 地标密集：Tha Phae Gate、Wat Chedi Luang、Wat Chiang Man、Wat Phra Singh、四座城门。
- 地形平坦（约 310 m 海拔），适合现有街机手感，不需要重写物理。
- 1 / 3 / 5 圈制与现有圈数系统天然匹配。

详细赛道设计见 [docs/MAP-DESIGN.md](docs/MAP-DESIGN.md)。

## 快速开始

需要 Python 3（仅用于启动静态服务器）和现代浏览器（WebGL）。

```powershell
python -m http.server 8080 --bind 127.0.0.1
```

然后打开 <http://127.0.0.1:8080/>。要测试清迈赛道，请打开 <http://127.0.0.1:8080/?track=moat>。

Windows 也可以直接双击 `start-game.bat`。

## 车辆选择与回归测试

Cityscape 现已接入两款 CC0 模型（加载失败保留原飞船）：
- 默认主车 Grab3D，双人第二辆 Kenney `race-future`。
- URL `?car=kenney`：主车换 Kenney；URL `?ship=1`：强制显示原飞船。
- `node tests/regressions.js`：验证驾驶/计圈关键逻辑与车型装载回退。仍需浏览器实机验收。

## 模型预览

资产管线自带一个独立预览页，用来验证转换后的车辆尺寸、朝向与材质：

- <http://127.0.0.1:8080/tools/model-preview.html>
- <http://127.0.0.1:8080/tools/model-preview.html?model=kenney>

当前已转换两辆 CC0 车：

| 资产 | 面数 | 尺寸（m） |
| --- | --- | --- |
| Grab3D Race Car | 19,440 | 1.92 × 1.02 × 5.28 |
| Kenney `race-future` | 2,068 | 1.99 × 1.38 × 4.40 |

转换脚本与格式说明见 [tools/README.md](tools/README.md) 与 [docs/ENGINE.md](docs/ENGINE.md)。

## 操作方式

### 单人模式

| 按键 | 作用 |
| --- | --- |
| `↑` | 加速 |
| `↓` | 刹车 / 后退 |
| `←` `→` | 左右转向 |
| `A` / `Q` | 左侧空气刹车 |
| `D` / `E` | 右侧空气刹车 |
| `空格` / `Shift` | 释放氮气 |
| `P` / `Esc` | 暂停 / 继续 |
| `R` | 暂停或结算时重新开始 |

### 双人模式（左右分屏）

| 玩家 1 | 玩家 2 | 作用 |
| --- | --- | --- |
| `W` / `S` | `↑` / `↓` | 加速 / 刹车 |
| `A` / `D` | `←` / `→` | 左右转向 |
| `Q` / `E` | — | 空气刹车 |
| `左 Shift` | `空格` | 释放氮气 |

- 氮气初始为半管，释放一次消耗半管，比赛中缓慢回充。
- 驶过红色加速带会立即获得推进，并补充 25% 氮气。
- 双人模式任意玩家先完成选定圈数即获胜；一方赛车损毁则另一方获胜。
- 双人成绩不写入最佳成绩记录。
- **赛后回放**：单人正常完赛后点击「观看回放」，可暂停/播放、拖动进度条、查看时间并返回成绩页；拖动会自动暂停，回放时可用空格播放/暂停、Esc 返回成绩页。主菜单也可观看当前赛道上次有效的单人完赛回放（无需再比赛一次），退出返回主菜单；损坏或不存在的回放不会显示入口。仅保存最近一次成功完赛的本地回放，不是视频文件；双人/损毁赛局不生成回放。

更完整的玩法说明见 [README-zh.md](README-zh.md)。

## 技术栈与限制

| 项目 | 说明 |
| --- | --- |
| 渲染 | Three.js **r50dev**（`libs/Three.dev.js`），另附 `libs/Three.r53.js` |
| 语言 | 原生 JavaScript，无构建步骤 |
| 资源格式 | 旧版 Three.js JSON / 自定义 JSON / PNG 贴图；**不支持 glTF** |
| 本地服务 | `python -m http.server` |
| 目标平台 | 桌面浏览器，WebGL 1 |

已知硬限制：

- 没有 `GLTFLoader` / `OBJLoader`，新资产必须先离线转换。
- 没有 `InstancedMesh`，古城约 **10,694 栋建筑**必须按区块合并，控制 draw call。
- 旧版 `Geometry` API 与现代 Three.js 不兼容，升级引擎等于整体重构。

详细方案见 [docs/ENGINE.md](docs/ENGINE.md)。

## 资产来源（摘要）

| 资产 | 来源 | 许可 | 用途 |
| --- | --- | --- | --- |
| HexGL 代码与素材 | [BKcore/HexGL](https://github.com/BKcore/HexGL) | MIT | 游戏基础 |
| 低模车辆 | [Kenney Car Kit](https://kenney.nl/assets/car-kit) | CC0 1.0 | 主车 / 交通车 |
| 低模车辆 | [Quaternius Cars Pack](https://quaternius.com/packs/cars.html) | CC0 1.0 | 交通车 |
| 主赛车 | [Grab3D Race Car](https://grab3d.com/models/vehicles/race-car/) | CC0 1.0 | 玩家主车 |
| 地图数据 | [OpenStreetMap](https://www.openstreetmap.org/) | ODbL 1.0 | 道路 / 建筑 / 水系 |
| 地图转换 | [OSM2World](https://osm2world.org/) | MIT | OSM → 3D |
| 地形 | [Mapzen Terrain Tiles](https://registry.opendata.aws/terrain-tiles/) | 开放数据，按来源署名 | 高程 |
| 地标模型 | Sketchfab（Wat Chedi Luang 等） | CC BY 4.0 | 古城地标 |

完整清单、面数与下载状态见 [docs/ASSETS.md](docs/ASSETS.md)，署名要求见 [CREDITS.md](CREDITS.md)。

## 目录结构

```text
racing-game/
├─ index.html                 # 入口、HUD、脚本加载
├─ start-game.bat             # Windows 一键启动
├─ bkcore/
│  ├─ hexgl/
│  │  ├─ HexGL.js             # 主循环、模式、结算
│  │  ├─ Gameplay.js          # 圈数、检查点、计时
│  │  ├─ ShipControls.js      # 车辆控制、氮气、碰撞
│  │  ├─ Weapons.js           # 战斗系统雏形（暂缓）
│  │  └─ tracks/Cityscape.js  # 当前占位赛道
│  └─ threejs/                # 渲染管理
├─ geometries/                # 赛道几何
├─ textures/                  # 贴图（低清）
├─ textures.full/             # 贴图（全尺寸，可替换 textures/）
├─ assets/                    # 运行时资产（cmr-static-v1 JSON + 贴图）
├─ tools/                     # 转换脚本与模型预览页
├─ docs/                      # 设计、路线图、资产与参考文档
├─ CREDITS.md                 # 第三方署名
└─ LICENSE                    # MIT
```

## 路线图

| 里程碑 | 内容 |
| --- | --- |
| M0 | 调研、选型、建立公开仓库 |
| M1 | OBJ → 自定义 JSON 转换器 + 运行时加载器，先接入 1 辆 CC0 车 |
| M2 | 古城环线 blockout：道路、护城河、城墙、四座城门、碰撞 |
| M3 | 临街建筑合并已完成原型；Wat Chedi Luang 已有基于 OSM 占地轮廓的原创低模 blockout；其它地标与街景道具待做 |
| M4 | 车辆与对手：主车、交通车、简单 AI |
| M5 | 玩法整合：圈数、双人分屏、氮气、HUD、最佳成绩 |
| M6 | 打磨：光照、雾、远景、音效、性能与发布 |

详见 [docs/ROADMAP.md](docs/ROADMAP.md)。

## 参与贡献

- 欢迎 Issue / PR，尤其是低模车辆、清迈街景道具、性能优化。
- 提交资产前请确认许可为 **CC0 / CC BY 4.0** 或同等宽松许可，并在 `CREDITS.md` 中登记。
- 不接受来源不明、仅限个人使用、或带 NC 条款的资产进入主分支。

## 许可

- 根目录提供 MIT [LICENSE](LICENSE)，但部分原始 HexGL 源码文件头仍标注 CC BY-NC 3.0；授权冲突尚待核实，**暂不保证整个项目可按统一 MIT 许可商用**。详见 [CREDITS.md](CREDITS.md)。
- 第三方模型、贴图、音频、地图数据：归各自作者所有，按各自许可使用，详见 [CREDITS.md](CREDITS.md)。
- 本项目为非官方项目，与清迈市政府、泰国政府及相关品牌方无关联。

---

**参考方向**：HexGL 的街机速度感 + 清迈古城的真实街区尺度 + 低多边形、暖色调的 Lanna 视觉风格。完整参考链接见 [docs/REFERENCES.md](docs/REFERENCES.md)。

### M2 OSM 道路导入

默认从仓库内已署名的 OSM GeoJSON 生成道路：python3 tools/build_moat_blockout.py。要导入其他已验证的闭合 GeoJSON，使用 --geojson 参数；要生成旧版尺寸示意路线，使用 --schematic --out /tmp/chiangmai-schematic-preview。当前 OSM 道路为 2026-10-31 官方 API 快照衍生，来源和 ODbL 条款见 docs/OSM-PROVENANCE.md。


### M2 导入器安全与起跑方向

真实路线 GeoJSON 必须显式闭合（首尾相距 ≤0.1m），不能自交，坐标必须位于清迈古城附近；导入时检查长度和重采样偏差。斜向道路的起跑朝向、双人并排位置和检查点门框会根据路线切线自动旋转。上述功能有离线测试及 Chrome headless 冒烟验证；2026-10-31 已完成 OSM 实际外圈道路中心线导入，仍缺现场路段复核与实体 GPU 试玩。


### 清迈四座城门（M2/M3 占位）

已从同一 OSM 快照提取 Tha Phae、Chiang Mai、Suan Dok、Chang Phueak 四个历史城门节点，并将起跑线/检查点对齐到附近道路；四个程序化砖色低模城门与短墙已经在 ?track=moat 中显示。**城门建筑形制仅为原创示意，非真实建筑扫描或官方模型**。详细坐标、node ID 和 ODbL 来源见 docs/OSM-PROVENANCE.md；真实 GPU 和完整驾驶测试仍待完成。


### M3 临街建筑与 Wat Chedi Luang 地标（2026-10-31）

- 同一 OSM 快照筛选外环临街 80m 的 815 栋建筑轮廓，避开道路及历史城门；立面和屋顶合并为 2 个网格。
- 新增 Wat Chedi Luang：从同一 OSM XML 提取寺院范围、古塔、Pra Wihan Luang、城柱庙四个 way（243018795、93413945、93413944、441418807），生成 4 张原创低模网格。
- 当前赛道模型合计 13 meshes、12 materials、16,172 triangles；Wat Chedi Luang 新增约 230 triangles。
- OSM 没有提供三维模型或可靠高度；古塔 38.4m 的视觉高度、屋顶和立面均为游戏示意，不是历史建筑复原。776 栋临街建筑高度同样是示意估算。
- tools/osm_wat_chedi_luang.py 校验输入 XML 与道路数据的 SHA-256 一致后才导出地标平面轮廓。

真实 GPU 性能、现场核验和人工驾驶仍未完成。来源和 ODbL 署名见 docs/OSM-PROVENANCE.md。

### OSM 物理全圈与回放回归（开发验证）

在支持 Chrome 148 + Selenium + SwiftShader 的环境中，可运行 python3 tests/browser_smoke.py --physical-laps 1（或 3、5）。这会用**测试专用**路线跟随器连续调用真实车辆物理和 Gameplay 检查点，已验证 OSM 6.49 km 路线的 1/3/5 圈均可结算；并非人工驾驶或真实 GPU 性能证明。回放内存采样与末尾插值缺陷已修复，可用 node tests/racedata-regressions.js 验证。历史 HexGL 文件的 CC BY-NC 许可问题仍未解决。
