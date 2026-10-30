# 资产清单 / Assets

> 目标：**全低模 + 许可干净 + 旧引擎可加载**。
> 最后核对：2026-10-30

## 选型原则

1. 许可必须是 **CC0**，或至少 **CC BY 4.0**。
2. 单车面数目标：主车 ≤ 25k，交通车 ≤ 5k，道具 ≤ 10k。
3. 优先 FBX / OBJ / Blend，便于离线转换；glTF 仅作参考。
4. 不接受真实品牌商标、NC 条款、来源不明或仅限个人使用的资产。
5. 所有资产必须能在 Three.js `r50dev` 上以合并几何 + 简单材质运行。

---

## 1. 车辆

### 1.1 已选定（CC0）

| 资产 | 许可 | 面数 | 格式 | 状态 | 用途 |
| --- | --- | --- | --- | --- | --- |
| **Grab3D Race Car** | CC0 1.0 | 19,440 | GLB / FBX / Blend / OBJ | 待下载 | 主赛车（比例真实，约 1.92 × 5.28 × 1.02 m） |
| **Kenney Car Kit** | CC0 1.0 | `race-future` 约 2,068 | FBX / OBJ / glTF | ✅ 已下载验证 | 主车备选 / 对手车 |
| **Quaternius Cars Pack** | CC0 1.0 | 低模（8 辆） | FBX / OBJ / Blend | 待下载 | 交通车 / 对手车 |

**Kenney Car Kit 可用车型**（45+ 模型中与赛道相关的部分）：

- `race-future`、`race`：低模赛车，性能最好
- `sedan`、`sedan-sports`：民用车 / 对手车
- `hatchback-sports`：小型性能车
- `suv`、`suv-luxury`：SUV / 街景车
- `van`、`taxi`、`police`、`ambulance`：清迈街景氛围

> Kenney 包结构：`Models/FBX format/`、`Models/OBJ format/`、`Models/GLB format/`、`Textures/`、`License.txt`。
> 许可为 CC0，署名非强制。

### 1.2 半写实备选（CC BY 4.0，当前不采用）

| 资产 | 作者 | 面数 | 评价 |
| --- | --- | --- | --- |
| Mazda RX7 Stylised | SheldonJ99 | 5,737 | 面数最友好，风格化 |
| Mazda MX5 Race Car | Peter Stephan | 22,692 | 细节好，可接受 |
| HCR Race Car | oakar258 | 29,588 | 原创赛车，无品牌风险 |
| Generic passenger car pack | Comrade1280 | 69,312 | 交通车合集 |

这些资产需要 Sketchfab 登录下载，且面数/材质更复杂，与「全低模 CC0」决策不一致，暂不使用。

### 1.3 已排除

| 资产 | 原因 |
| --- | --- |
| Compact Race Car | 实际是经典 Mini，不是赛车 |
| 2024 Porsche 992 GT3 R（489,304 tris） | 面数过高 + 品牌商标风险 |
| Ford Capri Group B（220,101 tris） | 面数过高 + 品牌商标风险 |
| 任何 CC BY-NC 车辆 | 商用受限 |

### 1.4 车辆面数预算

| 类型 | 目标面数 | draw call |
| --- | --- | --- |
| 玩家主车 | ≤ 25k | ≤ 6 |
| 对手车 | ≤ 8k | ≤ 4 |
| 交通车 | ≤ 5k | ≤ 4 |
| 车轮（可复用） | ≤ 500 / 个 | 合并进车身 |

> 旧引擎没有 `InstancedMesh`，同屏多车时优先复用几何体与材质，靠位置/颜色变体区分。

---

## 2. 清迈地标

| 模型 | 作者 | 许可 | 面数 | 建议 |
| --- | --- | --- | --- | --- |
| [Wat Chedi Luang](https://sketchfab.com/3d-models/wat-chedi-luang-3296a81f50484797adcb53ba66183940) | SphereView360 Thailand | CC BY 4.0 | **2,151** | ✅ 首选，直接接入 |
| [Sutep Temple](https://sketchfab.com/3d-models/sutep-temple-chiangmai-thailand-67909b569d7f4c3e8efbb34744b8f3aa) | SphereView360 Thailand | CC BY 4.0 | 272,264 | 远景 / Doi Suthep 备选，需减面 |
| [Wat Chiang Man](https://sketchfab.com/3d-models/wat-chiang-man-chiangmai-35b45a11afca408abe7c03058df4bdf5) | SphereView360 Thailand | CC BY 4.0 | 1,201,802 | 需减到 ≤ 30k 才可用 |
| [Thai Lanna Buddhist Temple](https://sketchfab.com/3d-models/thai-lanna-buddhist-temple-6add9dac765b457796bb4160970f11ec) | kositsuwan | CC BY 4.0 | 487,454 | 未贴图，适合参考 / 重贴图 |

**建议**：

- Wat Chedi Luang 是性价比最高的地标，放在古城中心偏西，作为视觉锚点。
- 城门、城墙、护城河栏杆用程序化几何，不建议找扫描模型。
- Doi Suthep 只做远景剪影，不进入碰撞与近景。

---

## 3. 街景道具

| 道具 | 来源 | 许可 | 面数 | 说明 |
| --- | --- | --- | --- | --- |
| Thai Tuk-Tuk（LiDAR 扫描） | Sketchfab / JFN | CC BY 4.0 | 77,570 | 需减面到 ≤ 10k |
| Songthaew（红色双条车） | 暂无现成 CC0 模型 | — | — | 建议用 Kenney 皮卡改色 + 程序化车斗 |
| 泰国寺庙灯笼 / 旗帜 | 程序化 | 自有 | 低 | 用贴图与简单几何 |
| 热带树木 | Kenney Nature Kit 等 | CC0 | 低 | 待选型 |
| 电线杆 / 电线 | 程序化 | 自有 | 低 | 清迈街景特征 |

> Tuk-Tuk 辨识度极强，但 77,570 面不适合直接进旧引擎；如使用必须减面 + 烘焙贴图。

---

## 4. 地图数据

| 数据 | 来源 | 许可 | 用途 |
| --- | --- | --- | --- |
| OpenStreetMap 建筑 / 道路 / 水系 | <https://www.openstreetmap.org/> | ODbL 1.0 | 赛道与街区基础 |
| OSM2World | <https://osm2world.org/> | MIT | OSM → glTF / OBJ |
| Mapzen Terrain Tiles | <https://registry.opendata.aws/terrain-tiles/> | 开放数据 | 高程（古城基本平坦） |
| Sentinel-2 cloudless | <https://cloudless.eox.at/> | 2016 CC BY 4.0；2018–2025 CC BY-NC-SA | **默认不用**（商用限制） |

**提取范围**（古城核心）：

```text
bbox = 18.776, 98.974, 18.800, 99.001
建筑 way 数量 ≈ 10,694（Overpass，2026-10-30）
```

**注意**：

- OSM 数据是 ODbL，衍生数据库需按 ODbL 共享；游戏内必须署名。
- 不要直接把 Sentinel-2 影像烘进商用版本。
- 地形只用于远景山体，古城内部按平坦处理。

---

## 5. 下载与入库流程

```text
1. 从官方来源下载原始包
2. 解压到本地临时目录（不要提交进仓库）
3. 检查 License / README
4. 运行转换脚本 → 生成运行时可用的 JSON + PNG
5. 只提交转换产物与许可说明
6. 更新 CREDITS.md 与 docs/ASSETS.md
```

**目录建议**：

```text
assets-src/            # 原始下载包（.gitignore）
assets/
  cars/
    grab3d-race-car/
      model.json
      texture.png
  landmarks/
    wat-chedi-luang/
      model.json
      texture.png
tools/
  obj2json.py
```

> 仓库当前尚未创建 `assets/`；M1 阶段建立。

---

## 6. 资产验收清单

- [ ] 许可明确，且与 `CREDITS.md` 一致
- [ ] 面数在预算内
- [ ] 尺寸单位为米，Y-up，车头朝向统一
- [ ] 贴图为 PNG / JPG，尺寸为 2 的幂
- [ ] 材质数量 ≤ 4 / 模型
- [ ] 无外部依赖贴图路径
- [ ] 能在 `r50dev` 中加载并正确显示
- [ ] 已记录来源 URL、作者、许可版本
