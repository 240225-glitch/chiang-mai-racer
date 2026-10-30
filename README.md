# Chiang Mai Racer · 清迈古城竞速

> 一个开源的 3D 街机竞速游戏：把泰国清迈古城护城河环线做成可玩的赛道。
> 基于 [HexGL](https://github.com/BKcore/HexGL)（MIT）继续开发。

**English** — Chiang Mai Racer is an open-source arcade racing game set on the 6.54 km moat loop of Chiang Mai Old City, Thailand. It is a heavily modified derivative of HexGL (MIT). The project is currently in the asset-production phase: the playable build still uses the original Cityscape track as a placeholder while the Chiang Mai map and CC0 low-poly vehicles are being produced.

---

## 项目状态

| 模块 | 状态 |
| --- | --- |
| 单人计时、同屏双人分屏、氮气、1/3/5 圈、暂停/重开、最佳成绩、中文结算 | ✅ 已完成并有回归验证 |
| 车辆资产选型 | ✅ 已完成，确定「全低模 CC0」路线 |
| 清迈地图方案 | ✅ 已确定「古城护城河环线」，全长约 6.54 km |
| 旧版 Three.js 资产转换管线 | ✅ 原型完成：OBJ → JSON + 运行时加载器 + 预览页 |
| 清迈赛道 | 🚧 待制作，当前仍为 Cityscape 占位 |
| 新车辆接入主游戏 | 🚧 预览页已验证，待接入赛道 |

> 当前 `main` 分支可以直接运行，但跑的还是旧赛道。清迈内容会按 [路线图](docs/ROADMAP.md) 逐步替换。

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
cd racing-game
python -m http.server 8080 --bind 127.0.0.1
```

然后打开 <http://127.0.0.1:8080/>。

Windows 也可以直接双击 `start-game.bat`。

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
| M3 | 建筑合并与地标：Wat Chedi Luang、Wat Chiang Man、Wat Phra Singh、街景道具 |
| M4 | 车辆与对手：主车、交通车、简单 AI |
| M5 | 玩法整合：圈数、双人分屏、氮气、HUD、最佳成绩 |
| M6 | 打磨：光照、雾、远景、音效、性能与发布 |

详见 [docs/ROADMAP.md](docs/ROADMAP.md)。

## 参与贡献

- 欢迎 Issue / PR，尤其是低模车辆、清迈街景道具、性能优化。
- 提交资产前请确认许可为 **CC0 / CC BY 4.0** 或同等宽松许可，并在 `CREDITS.md` 中登记。
- 不接受来源不明、仅限个人使用、或带 NC 条款的资产进入主分支。

## 许可

- 代码：**MIT License**，原始版权归 Thibaut Despoulain（HexGL），修改部分归本项目贡献者。完整文本见 [LICENSE](LICENSE)。
- 第三方模型、贴图、音频、地图数据：归各自作者所有，按各自许可使用，详见 [CREDITS.md](CREDITS.md)。
- 本项目为非官方项目，与清迈市政府、泰国政府及相关品牌方无关联。

---

**参考方向**：HexGL 的街机速度感 + 清迈古城的真实街区尺度 + 低多边形、暖色调的 Lanna 视觉风格。完整参考链接见 [docs/REFERENCES.md](docs/REFERENCES.md)。
