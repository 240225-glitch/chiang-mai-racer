# 引擎与资产管线

> 目标：在不重写游戏的前提下，让 CC0 低模车辆与清迈地图跑在 Three.js `r50dev` 上。

## 1. 现状

| 项目 | 值 |
| --- | --- |
| 渲染库 | `libs/Three.dev.js`，`THREE.REVISION = "50dev"` |
| 备用版本 | `libs/Three.r53.js` |
| 模块方式 | 全局 `THREE` + 普通 `<script>`，无打包 |
| 几何 API | `THREE.Geometry` / `THREE.Face3`（旧版） |
| 加载器 | 无 `GLTFLoader`、无 `OBJLoader`、无 `FBXLoader` |
| 实例化 | 无 `InstancedMesh` |
| 材质 | `MeshLambertMaterial` / `MeshPhongMaterial`，无 PBR |
| 目标 | WebGL 1，桌面浏览器 |

### 实现状态（2026-10-30）

- ✅ `tools/obj2json.py`：OBJ + MTL → `cmr-static-v1`，支持三角化、缩放、旋转、居中、材质合并、纹理复制。
- ✅ `bkcore/threejs/StaticModelLoader.js`：运行时加载，构建 `THREE.Geometry` + `MeshPhongMaterial`。
- ✅ `tools/model-preview.html`：独立预览页，支持拖拽旋转 / 滚轮缩放。
- ✅ 已转换并验证两辆车：
  - Grab3D Race Car：19,440 tris，2 materials / 2 meshes，1.92 × 1.02 × 5.28 m
  - Kenney `race-future`：2,068 tris，1 material / 1 mesh，1.99 × 1.38 × 4.40 m
- ✅ 在 `Cityscape.js` 接入两辆车：保持原物理根节点并异步添加 CC0 车身，加载失败回退飞船。
- ✅ 修复 r50 `THREE.Color('#RRGGBB')` 显示黑色的问题，转换为数值十六进制。
- ☑ Chrome 148 headless SwiftShader 8 场景冒烟通过；⬜ 真实 GPU 完整驾驶、碰撞、氮气及首屏加载耗时验收。

### r50 兼容性要点

- `THREE.Color(r, g, b)` **不生效**：r50 的构造函数只接受一个十六进制参数。
  顶点色必须用 `color.setRGB(r, g, b)`，并写入 `Face3.vertexColors`；
  只写 `geometry.colors` 不会被渲染器使用。
- `THREE.UV` 仍存在（现代版本已改为 `Vector2`），加载器使用 `THREE.UV`。
- `THREE.ImageUtils.loadTexture` 可用；没有 `TextureLoader`。
- 没有 `InstancedMesh`，重复几何必须合并。

### M2 赛道的方向与双人起点（2026-10-31）

- tools/build_moat_blockout.py 根据路线起点前后点计算切线方向（局部 +Z 为车头），输出 spawn.yaw_rad 与 [x,y,z,w] 四元数。
- ShipControls.reset() 读取可选 rotation.w；原 Cityscape 未提供 w 时仍使用 1，避免旧赛道受影响。
- ChiangMaiMoat.js 将两车沿道路法线分开，而不是沿世界 X 分开；路段方向变化时依然并排。
- gate_mesh 用局部道路法线生成旋转门框，避免 GeoJSON 斜向路段与轴对齐门框相互错位。
- GeoJSON 导入时离线执行简单闭环/自交/坐标范围验证，不在浏览器帧循环中计算拓扑。

### 关键代码位置

| 文件 | 职责 |
| --- | --- |
| `index.html` | 入口、HUD、脚本加载顺序 |
| `bkcore/hexgl/HexGL.js` | 主循环、模式切换、结算 |
| `bkcore/hexgl/Gameplay.js` | 圈数、检查点、计时 |
| `bkcore/hexgl/ShipControls.js` | 车辆物理、氮气、碰撞、血量 |
| `bkcore/hexgl/tracks/Cityscape.js` | 当前赛道生成（占位） |
| `bkcore/threejs/RenderManager.js` | 渲染器、后期、画质 |

### 硬限制

1. **不能直接加载 glTF**。所有新资产必须离线转换。
2. **不能逐栋建筑建 mesh**。约 10,694 栋建筑必须合并。
3. **不能使用现代材质/光照**。PBR、IBL、实时阴影都要避免或降级。
4. **不能引入构建步骤**。保持「双击 `index.html` / 静态服务器即可运行」。

---

## 2. 方案选择

| 方案 | 内容 | 风险 | 结论 |
| --- | --- | --- | --- |
| A. 保留 r50dev + 离线转换 | 自建 OBJ → JSON 管线 | 低 | ✅ 采用 |
| B. 升级现代 Three.js | 直接用 glTF / PBR | 高，需重写大量旧 API | 暂不采用 |
| C. 混合 | 保留 r50dev，只替换静态地图 | 中 | 作为 A 的补充 |

**决策：A + C**。先建立转换管线，地图按区块烘焙成合并几何；如果后期确实需要 PBR，再单独评估升级。

---

## 3. 转换管线

```text
原始资产 (.fbx / .obj / .glb / .blend)
        │
        ├─ Blender（可选）：清理、减面、合并、烘焙、统一朝向
        │
        ▼
   .obj + .mtl + .png
        │
        ▼
 tools/obj2json.py
   ├─ 解析 OBJ / MTL
   ├─ 三角化
   ├─ 统一 Y-up、+Z 车头
   ├─ 按材质分组
   ├─ 可选：按区块合并
   └─ 输出 .json
        │
        ▼
 bkcore/threejs/StaticModelLoader.js
   ├─ 解析 JSON
   ├─ 构建 THREE.Geometry
   ├─ 构建材质（Lambert / Phong）
   └─ 返回 THREE.Object3D
```

### 3.1 资产约定

| 项目 | 约定 |
| --- | --- |
| 单位 | 1 unit = 1 m |
| 上方向 | +Y |
| 车头方向 | +Z |
| 原点 | 车辆：地面中心；建筑：底面中心 |
| 贴图 | PNG / JPG，边长 2 的幂（256 / 512 / 1024 / 2048） |
| UV | OBJ 标准，原点左下 |
| 材质数 | 单车 ≤ 4，单建筑 ≤ 2 |

### 3.2 JSON 格式（`cmr-static-v1`）

```json
{
  "format": "cmr-static-v1",
  "name": "race-future",
  "bounds": { "min": [-0.9, 0, -2.1], "max": [0.9, 1.1, 2.1] },
  "materials": [
    {
      "name": "body",
      "color": "#c8322b",
      "map": "textures/cars/race-future/body.png",
      "shininess": 40,
      "specular": "#333333",
      "transparent": false,
      "opacity": 1,
      "doubleSided": false
    }
  ],
  "meshes": [
    {
      "material": 0,
      "positions": [0, 0, 0, 1, 0, 0, 0, 1, 0],
      "normals": [0, 0, 1, 0, 0, 1, 0, 0, 1],
      "uvs": [0, 0, 1, 0, 0, 1],
      "indices": [0, 1, 2]
    }
  ]
}
```

设计要点：

- `positions` / `normals` / `uvs` 用扁平数组，避免大量对象。
- `indices` 用三的倍数；加载时写入 `THREE.Face3`。
- 每个 `mesh` 对应一个材质，保证 draw call 可控。
- `colors` 为可选顶点色数组（每顶点 3 个分量）；加载器会写入 `Face3.vertexColors`。
- `bounds` 用于碰撞与相机，不依赖运行时计算。

### 3.3 运行时加载器

新增 `bkcore/threejs/StaticModelLoader.js`：

```js
THREE.StaticModelLoader = function () {};

THREE.StaticModelLoader.prototype.load = function (url, callback) {
  var xhr = new XMLHttpRequest();
  xhr.open('GET', url, true);
  xhr.onreadystatechange = function () {
    if (xhr.readyState !== 4) return;
    if (xhr.status !== 200 && xhr.status !== 0) return;
    var data = JSON.parse(xhr.responseText);
    callback(THREE.StaticModelLoader.build(data));
  };
  xhr.send(null);
};

THREE.StaticModelLoader.build = function (data) { /* ... */ };
```

构建逻辑：

1. `new THREE.Geometry()`
2. 写入 `vertices`、`faces`、`faceVertexUvs[0]`
3. `geometry.computeFaceNormals()`（或使用 JSON 法线）
4. `geometry.computeBoundingSphere()`
5. 每个 `mesh` 建一个 `THREE.Mesh`，同一材质复用
6. 返回 `THREE.Object3D` 容器

> 注意：`r50dev` 的 `Geometry` 在首次渲染时才上传 GPU；大量顶点会有一次性卡顿，建议分帧加载或显示加载进度。

### 3.4 转换脚本

新增 `tools/obj2json.py`（Python 3，无第三方依赖）：

- 解析 `v` / `vt` / `vn` / `f` / `usemtl` / `mtllib`
- 支持 `f v/vt/vn`、`f v//vn`、`f v`
- 统一三角化（扇形）
- 按 `usemtl` 分组
- 读取 `.mtl` 的 `Kd` / `Ks` / `Ns` / `d` / `map_Kd`
- 输出 `cmr-static-v1`
- 可选参数：`--scale`、`--rotate-x`、`--merge`、`--center`

### 3.5 贴图

- 使用 `THREE.TextureLoader` 或手写 `Image` 加载。
- `texture.flipY = true`（默认），与 OBJ UV 对齐。
- `texture.wrapS = texture.wrapT = THREE.RepeatWrapping`。
- WebGL 1 下非 2 的幂贴图不能使用 mipmap，必须预处理。
- 大场景优先使用 atlas，减少材质切换。

---

## 4. 地图分块与合并

### 4.1 分块

- 区块大小：200 m × 200 m。
- 每个区块一个 JSON（`cmr-chunk-v1` 可复用 `cmr-static-v1` 的 `meshes` 数组）。
- 区块内按材质合并，目标每区块 ≤ 6 个 draw call。

### 4.2 加载策略

| 距离 | 策略 |
| --- | --- |
| 0–300 m | 完整区块 |
| 300–800 m | 低模区块 |
| > 800 m | 不加载 / 山体剪影 |

旧引擎没有异步 streaming 框架，先做「开局一次性加载 + 隐藏远处区块」的简单版本。

### 4.3 光照与烘焙

- 不使用实时阴影。
- 环境光 + 1 个方向光。
- AO / 明暗烘焙到顶点色或贴图。
- 车辆可用 `MeshPhongMaterial`，场景用 `MeshLambertMaterial`。

---

## 5. 车辆接入

1. 用 `obj2json.py` 转换主车。
2. 在 `Cityscape.js` 中把旧飞船作为可隐藏子节点，低模车以子节点挂在 `Object3D` 物理根节点上（不改碰撞地图/物理模型）。
3. 调整：
   - 车辆长度 → 碰撞半径
   - 相机高度 / 距离
   - 转向轴心
   - 车轮旋转（可选）
4. 保留原飞船作为 fallback（`?ship=1` 强制使用旧船；加载 JSON 失败自动回退；`?car=kenney` 切换主车）。

**尺寸基准**：

| 车型 | 长度 | 宽度 | 高度 |
| --- | --- | --- | --- |
| 赛车 | 4.2–5.3 m | 1.8–2.0 m | 1.0–1.2 m |
| 轿车 | 4.4–4.8 m | 1.8 m | 1.4 m |
| SUV | 4.6–5.0 m | 1.9 m | 1.7 m |
| Tuk-Tuk | 2.8–3.2 m | 1.4 m | 1.8 m |

> 转换脚本按包围盒自动缩放到目标长度，避免不同资产比例不一致。

---

## 6. 兼容性检查清单

- [ ] Chrome / Edge 最新版可运行
- [ ] Firefox 可运行
- [ ] 无 ES Module / 无 `import`
- [ ] 所有新脚本在 `index.html` 中按依赖顺序加载
- [ ] 不覆盖全局 `THREE` 现有方法
- [ ] 不引入构建工具
- [ ] 低画质下不加载大贴图
- [ ] 双人模式不增加额外 draw call 峰值

---

## 7. 备选：升级 Three.js

只有在以下情况才考虑：

- 低模方案无法达到目标画质。
- 需要 PBR / 实时阴影 / glTF 工作流。
- 愿意投入 1–2 周重构旧 API。

升级成本：

- `Geometry` → `BufferGeometry`
- `MeshFaceMaterial` → 多材质数组
- `shadowMapEnabled` → `shadowMap.enabled`
- 大量渲染器/材质 API 变更
- 后期处理链重写

**当前结论：不升级。**

## 2026-10-31 OSM 实际道路中心线

- 使用官方 OSM API 快照，按节点 ID 和单行方向拼接外环道路，6,492.2m，650 路线点，4,274 三角面（含 19 块 OSM 护城河多边形）。
- 默认生成器输入为 assets/tracks/chiangmai-moat/source-osm.geojson；--schematic 可恢复原始示意路线至独立目录。
- 原始 OSM 许可 ODbL，见 docs/OSM-PROVENANCE.md；游戏路宽和城门仍为示意，水面已导入 OSM water=moat 多边形，未完成真实 GPU 验收。


### M3 OSM 临街建筑低模管线（2026-10-31）

离线 tools/osm_roadside_buildings.py 从同一 OSM XML 快照提取赛道 80m 范围内建筑平面轮廓并保留 ODbL/way ID；tools/build_moat_blockout.py 将 815 栋建筑的立面和屋顶按约 350m 路段分块合并为 38 个 cmr-static-v1 网格，避免整圈巨型包围盒。立面通过顶点色得到暖白、赭黄、柚木等色调，并烘焙勒脚、木檐和窗框；屋顶使用原创红瓦攒尖/四坡/截顶四坡低模。r50dev 的旧版 THREE.Geometry 加载路径不变。多数建筑高度为视觉估算，非实测。真实 GPU 内存、帧率和更细 LOD 仍需验证。


### M2 急弯操控参数（2026-10-31）

- OSM 路线 index 400 约 55.388°、index 401 约 33.972°；旧 ShipControls 构造默认 angularSpeed=0.005，实际比赛由 tweakShipControls 改为 0.019/0.021；14m 清迈赛道需要单独调校。
- 只在 Cityscape.js 的 moatMode 分支为每辆车设置 angularSpeed=0.024 和 airAngularSpeed=0.030，避免改变原 Cityscape 游戏。
- tests/browser_smoke.py 使用真实 ShipControls.update(1) 在 Chrome SwiftShader 中验证 14 帧手刹转向的方向变化，且检查双人车辆一致、默认 Cityscape 普通难度仍为 0.019。
- 尚缺手动连续穿越急弯、完整整圈和真实 GPU 帧率验收。

- 2026-10-31 追加：tests/browser_smoke.py 的测试专用路线跟随器在 OSM 第 400/401 点连续急弯实际运行 301 次 ShipControls.update(1)，出现 3 次路肩修正，无坠落；转向幅度测试为 14 帧 68.2°。仅测试代码，不提供生产自动驾驶。

### 2026-10-31 回放性能与边界修复

- RaceData.tick() 原误将 rate++ 当作采样计数器，导致 rateState 恒为 1、每帧录制；现改为 rateState++，默认每两次调用录制一次。自动全圈 10495 物理帧（每 3 帧检查一次 Gameplay）产生 1750 条回放样本。
- RaceData.applyInterpolated() 修复末尾/单帧读取 data[seek+1] 导致的异常，钳制首尾与相同时间戳插值；import() 拒绝空、非法、非有限和时间逆序数据，并移除大数组 console.log。
- tests/racedata-regressions.js 覆盖这些回归；tests/browser_smoke.py 在旧版 Three.js r50dev 真实 WebGL 中验证回放边界与插值。
- M2 自动路线跟随 1/3/5 圈分别 10495/31489/52477 物理帧通过（SwiftShader，无真实 GPU）。人工驾驶、双人全圈和帧率仍未验收。


### 2026-10-31 M2 非活动车辆物理门控

ShipControls.update(dt) 原来即使 active=false 也执行 boosterCheck() 和位置积分；倒计时停在加速带上会自行前进/补充 nitro。现在仅当 collisionMap.projectInside 存在（M2 OSM 适配器）且 inactive 时跳过物理积分，避免改动原 Cityscape 行为。暂停时主循环本身停止，因此暂停/恢复不受此门控影响。Chrome SwiftShader 物理回归覆盖倒计时、氮气/加速带和双人胜者判定；仍需真实 GPU 与人工驾驶验收。


### 2026-10-31：静态模型输入验证

- StaticModelLoader.build() 现在先验证 cmr-static-v1：非空且有界的 materials/meshes，每个网格顶点和三角索引数量、整数索引范围、所有有限数值、法线/UV/顶点色数组长度。
- 已在旧版代码复现损坏 Face3(0,1,9) 可以在只有 3 个顶点时被构造，导致延迟至 GPU 上传才可能失败。修复后在加载阶段抛 StaticModelLoader 错误，交由已有 onError 回退逻辑处理。
- 保守上限：每网格 300,000 顶点、400,000 三角形；整个模型最多 500,000 顶点、256 网格、128 材料。超过需先离线简化/分块，不要直接增大浏览器内存上限。
- 当前 OSM 赛道与 Kenney/Grab3D 模型通过校验，Chrome 148 SwiftShader 17/17 场景通过。真实 GPU 性能尚未验收。


### 2026-10-31 r50dev 分块包围球与局部坐标

旧版 THREE.Geometry.computeBoundingSphere() 不是现代中心点半径算法：它直接对 geometry.vertices 取距 **(0,0,0)** 的最大长度，Mesh.boundRadius 再用于 frustum culling。全局 X/Z 坐标下即使将 815 栋建筑拆成 19 段，包围球仍会跨越约 1km，导致背面建筑无法有效剔除。

离线生成器现在按 350m 路程桶聚合建筑，每桶墙/顶各一 mesh，并在 cmr-static-v1 的 mesh 中增加可选 `offset: [x,y,z]`。positions 以该块包围盒中心为局部原点，StaticModelLoader.build() 在 THREE.Mesh.position.set(...) 中恢复世界位置。可选 offset 经过长度/有限数值验证；原车辆/Cityscape 资源不含 offset，行为不变。当前 19 块、38 个建筑网格、全部 OSM 场景 **76 meshes / 20 materials / 141,434 triangles**（含变形地面、远山、231 棵树和 109 盏路灯），建筑最大局部包围球半径约 201.68m。实际 GPU 帧率/绘制调用仍需量化；更细分块可能增加 CPU 和 draw calls。

### 2026-11-04 moat 暖色渲染与暗角

- `HexGL.initGameComposer()` 在 moat 且 `quality > 0` 时改用 `THREE.ShaderExtras.vignette`（`offset=0.9`、`darkness=0.22`），不再叠加蓝色六边形 `hexvignette`；Cityscape 仍使用原六边形暗角，低画质仍使用 screen pass。
- `Cityscape.js` 的 moat 光照改为 ambient `0xd2c2ad`、太阳 `0xfff0dc` 强度 `0.95`、暖色补光 `0xffcfa6` 强度 `0.55`、雾 `0xd9b88d` 从 `700` 到 `12000`。Cityscape 的 ambient/太阳/雾保持原值。
- Bloom 仍仅在高画质启用：moat `0.35`、Cityscape `0.8`。
- 建筑、屋顶、地面、远山和树冠通过每个顶点的 RGB 乘材质基色；r50 的 `Face3.vertexColors` 由 `StaticModelLoader` 生成，仍不需要额外材质槽。顶点色范围在离线校验中限制为 `[0,1]`。


### 2026-10-31：r50 建筑分块实际 draw-call A/B 测试

`tests/browser_smoke.py` 使用 Chrome 148 SwiftShader 的真实 `THREE.WebGLRenderer.render(scene,camera)`，同一场景同一摄像机在路线点 80、240、400、560 对比仅关闭/开启 38 个建筑网格的 `frustumCulled`。`renderer.info.render.calls` 分别从 49/49/52/43 降为 35/33/38/15；`renderer.info.render.faces` 同时减少。测试后恢复摄像机和网格剔除状态，完整 18/18 WebGL 场景通过。

**解释边界**：这是软件 WebGL 中真实绘制调用计数，不是 GPU 帧率；其它对象（例如赛车）仍参与绘制，不能将总调用数全部归因于建筑。更少的调用和三角面不自动等于更快 FPS，真实硬件/设备和首屏加载仍需测量。

### 2026-10-31 首屏加载性能基线（独立 Chrome 进程）

- 新增 `tests/browser_load_profile.py`：在本机静态 HTTP 服务上逐次启动**全新** Chrome 148 headless + SwiftShader，禁用 HTTP 缓存，实际点击开始与赛道选择并等待 `step-4` 游戏就绪；每赛道采样 3 次。每次重启 Chrome 是为了避免多次导航导致 JS heap 累积，造成无效的赛道间内存对比。
- 可复现：`python3 tests/browser_load_profile.py --samples 3 --out /tmp/cmr-load-profile.json`。本轮机器的原始数据存于 `docs/PERF-BASELINE-2026-10-31.json`，包括每次的就绪耗时、Resource Timing 字节数/条数、JS heap。
- **清迈 OSM（低画质）中位数**：4,493 ms 就绪、67 条资源、6,748,981 B 传输、48,429,425 B JS heap；**Cityscape（低画质）**：5,361 ms、79 条、7,393,065 B、78,740,616 B。
- 此处“就绪”包含首页/菜单交互直到 `step-4` 可见，不是纯 HTTP 加载时间；JS heap 不包含 WebGL 显存/所有浏览器进程内存；localhost 无网络 RTT，且软件渲染受 CPU 调度影响。样本量只有 3，**不能将该差值称为真实 GPU/用户设备加速或 FPS 提升**。后续需要实体 GPU 和用户设备重复测量。

### 2026-10-31 桥梁离线几何筛选

OSM 桥梁候选使用 Python 离线计算线段与水体多边形交点、并集重叠长度和边界穿越次数；13 条近水候选中 7 条 footway 几何跨水、6 条不与映射水体重叠。结果只写 GeoJSON 元数据，不进入 Three.js r50 运行时；未来低模桥梁需单独核验可通行性并遵守旧版引擎兼容要求。

### 2026-10-31 M3 桥梁距离算法修复

- 修复桥梁候选提取的**漏检风险**：此前只检查 OSM 道路节点和相邻节点中点到水体的距离；很长的线段可能从窄水面穿过，而三个采样点均远离水面，导致漏掉真实候选。现在计算完整道路每条线段到水体多边形边界的最小距离，并处理相交/线段在水内情况。
- 新增合成 200m 长线段穿越 2m 水面的回归，旧采样法会漏检；实际 2026-10-31 OSM 快照重算后仍是 **13 条近水候选、7 条 footway 几何跨水、6 条仅近水**，其中 3 条非跨水道路距离从 8.58→8.56m、5.33→5.30m、11.00→10.87m；way IDs 不变。
- 本改动仅修复**离线数据提取准确性**，没有添加车桥模型或改变赛道碰撞。仍未确认任何可驾驶护城河桥，禁止把 footway 候选直接作为车桥。

## 2026-10-31 r50 模型请求的失败终止语义

`bkcore/threejs/StaticModelLoader.js` 使用原生 XHR，设置 30 秒超时，并对 `error` / `timeout` / `abort`、HTTP 错误、解析/模型校验错误和同步 `send` 异常提供一次性 `onError`。避免重复事件二次初始化 Cityscape 回退；`file://` 读取仍允许 status=0 的有效 JSON。实际离线/弱网设备需另行验证。

### 2026-10-31 M3 岸线块与 r50 剔除

离线生成器在使用 OSM water=moat 多边形时，额外按 19 个水体环分别输出 `osm-moat-bank-XX`。每环 2 顶点/边、2 三角形/边，合计 268 条边/536 tris；局部顶点配合 `offset`（r50 靠原点的包围球）恢复原 OSM X/Z 世界位置。岸墙材料使用 r50 `MeshPhongMaterial` 支持的 `doubleSided`，不引入现代 Three.js 特性。默认地图共 68 meshes/16,708 tris；增加 draw calls 的代价必须在真实 GPU 另行评估。

岸墙高度 -0.45m 至 +0.18m 和石色为游戏原创示意，不是 OSM 实测三维信息。水体端部可能代表桥口/数据切割边界，不能把生成的端面当成真实实体墙；此网格没有碰撞，也不改变原有驾驶拓扑。

Chrome 148 + SwiftShader 的 18 个 WebGL 场景全部通过；含岸墙的新场景四处建筑剔除 draw calls 59→45、60→44、64→50、46→18。新增岸墙提高场景基础 draw calls，不得把建筑剔除差值当作整体优化或真实 GPU FPS。Python 41 项和 Node 四套回归通过。

### r50 水岸视觉网格端部处理（2026-10-31）

`tools/build_moat_blockout.py` 的 `water_bank_meshes` 保持每个水体多边形局部坐标和 `offset` 剔除方式，但跳过长条形水体的明显横向闭合短边，以免产生穿越水面的虚构墙。判定仅用于原创视觉网格，OSM 来源数据及物理碰撞不变；非正交/弧形端部仍需人工复核。

### 2026-10-31 r50 岸墙端部启发式修正

`is_water_polygon_end_cap` 先前仅测试短边与两侧长边近似正交，遗漏两侧长边方向。对同向长边形成的阶梯/凹角会误删合法墙段。现在还要求两条相邻长边单位方向点积 `< -0.9`（反向近似平行）；保留原正交和长度阈值。新增正反方向合成回归；默认 OSM 模型 SHA/网格和三角面规模不变，r50 渲染器代码未改。

## 2026-10-31：桥梁清单识别水体断口附近的机动车道路（待核验）

- 以实际 HEAD `fff6a9f`、干净工作树和四份工程文档为起点。原有桥梁清单仅把 7 条与水体重叠的 footway 识别为跨水候选，忽略了 OSM 水体多边形可能在桥口断开：`bridge=yes` 机动车道路不一定与水面多边形直接相交。
- `tools/osm_bridge_inventory.py` 复用已测试的保守岸墙端部几何识别，计算 13 条候选道路至水体端部中点的整条线段最短距离；对 16m 内且没有水面重叠的机动车 `bridge=yes` 道路标记 `mapped_water_gap_motor_bridge_candidate`，仅用于**人工核查优先级**，不是已确认汽车桥，也不据此添加 3D 模型或碰撞。
- 同一 OSM 快照中 4 条 `secondary_link` 候选：26765842（9.01m）、696726366（5.35m）、698115427（14.80m）、698115429（11.10m）。原 7 条 footway 几何跨水候选不变，另 2 条仍为仅近水。保留 ODbL、OSM way ID、快照 SHA；新的端部距离和分类已写入 `source-bridges-osm.geojson`。
- 这解决的是**候选筛选盲点**，不是实地验证；端部阈值是保守的游戏数据审阅启发式。下一步核对这四条道路的桥面/方向、连接拓扑及是否跨越实际水面，再考虑原创低模。仍需真实 GPU/人工驾驶/HexGL 许可审查。

### 2026-11-01 M3 桥梁数据（仅离线分析）

`tools/osm_bridge_inventory.py` 现对同源 OSM 快照建立机动车道路节点倒排索引，记录桥梁候选首尾与其他 `highway` 机动车 way 的共享节点证据；再将相距 ≤30m 且道路方向近似平行（绝对点积 ≥0.85）的机动车候选分组为审阅位置。四条单向单车道 `secondary_link` way 形成两组；这既不等于两座已确认实体桥，也不能用于自动生成可驾驶碰撞桥。该步骤只输出 GeoJSON 元数据，不影响 Three.js r50dev 运行时模型或帧性能。

## 2026-11-01 离线桥梁/路线拓扑审计

osm_bridge_inventory.py 现在可读取同一 OSM 快照的闭合 source-osm.geojson，计算候选 bridge=yes 路段到路线中心线的全线段最短距离、几何交点去重、最近路线段与绝对方向点积。它仅写入 ODbL GeoJSON 审阅数据，不生成 Three.js r50 模型，不修改运行时碰撞或车辆物理。原始 OSM 共享节点/单向通行、真实道路连接和桥梁结构仍需独立验证。

### 2026-11-01：OSM 桥梁路网审阅算法（离线）

`tools/osm_bridge_inventory.py` 在 XML 中为机动车 `highway` way 建立 OSM 节点有向邻接表；`oneway=yes/-1` 和 `junction=roundabout` 按标签决定边方向。对同一快照的外圈 `osm_way_ids` 节点做多源 BFS，记录桥梁入口/出口最少节点边数；这些计数**不是米数或实际可驾驶证明**。未检查 turn restrictions、lane/access、实际道路与渲染中心线的连接；不参与运行时物理与渲染。


## 2026-11-01：M3 机动车桥梁通行标签与转弯限制审阅（不改变赛道）

- 基线为 b3b7e35，工作树干净；按本轮实际 Git 状态与同源 OSM XML 继续开发。
- osm_bridge_inventory.py 新增机动车通行标签的保守优先级审阅：motorcar > motor_vehicle > vehicle > access。对 private/no/permit 等限制、destination/customers 等有限通行及未知取值，从离线有向路网 BFS 排除；更具体的机动车标签可覆盖一般 access。没有显式限制的道路仍仅标为 untagged，不代表合法通车。非机动车 highway 标记 not_motor_road。
- 新增 type=restriction 关系审阅：统计原始 OSM XML 的限制关系，按桥梁 way 成员或 via 节点记录附近关系 ID。未实现转向限制约束的 BFS，条件限制与 via way 也仍待进一步核查；没有相邻限制关系不代表实际通行合法。
- 同源快照的 1035 条 MOTOR_ROADS way 中，933 条无机动车通行标签、53 条明确限制、34 条仅有限通行、15 条显式允许；路网 BFS 排除 87 条限制/有限通行 way（本快照没有未知值）。现有快照有 13 个 restriction relations，四条机动车桥候选未直接命中桥 way/via 节点；四条均无明确机动车 access 标签，之前的最短节点边数 2/20、29/2、3/29、19/3 不变。这是候选审阅，不是实体桥梁或实际驾驶权证明。
- 只更新离线桥梁 GeoJSON、Python 测试和文档，不修改 Three.js r50dev、M2 14m 游戏路宽、碰撞、车辆物理、路网或渲染。下一步应实现考虑转弯限制的状态图与现场桥梁核验；真实 GPU/手动驾驶和 HexGL 许可问题仍待解决。

### 2026-11-01 离线 OSM 转弯限制审计

桥梁候选分析在 Python 离线运行，不增加 Three.js r50dev 运行时依赖。路网 BFS 的状态包括节点和 incoming way（逆向搜索为 outgoing way），可执行无条件 via-node 的 `no_*` / `only_*` 转弯限制；条件和 via-way 规则明确列为未处理。原 OSM 快照 13 条关系中 7 条应用、6 条未应用；四条机动车桥候选最短节点边数不变。游戏物理和 WebGL 模型未修改，真实 GPU 和实际驾驶仍需验收。


## 2026-11-01 M3 条件转弯限制的指定时刻审计

- 从实际干净 HEAD `4bf31fe` 及四份工程文档继续；`tools/osm_bridge_inventory.py` 新增可选 `--audit-time HH:MM`，仅在明确给出**清迈当地时间**时解析纯每日时段（含逗号分隔、跨午夜），采用起点包含/终点不包含。工作日、节假日、例外车辆、复合条件或无效语法不做猜测，继续列为未处理。
- 默认**不提供时间**时仍保守保留 4 条条件限制未处理，不伪称全天可通行；给定 08:00 时同源 OSM 快照 13/13 条转弯限制纳入搜索（原 9 + 条件 4）；12:00 时 9 条生效、4 条被明确判定为时段外。审计样本在 `docs/M3-TIME-TURN-AUDIT-2026-11-01.json`，保留 ODbL 来源与 SHA。
- 四条机动车桥候选的最短节点边数在 08:00 与 12:00 都是 2/20、29/2、3/29、19/3；这只是**从任意路线节点开始/结束**的有向图统计，未考虑实际比赛行车方向、路口车道接续、实时交通规则或桥梁现场情况。
- 新增纯时段解析、早/午/晚边界、跨午夜、无效语法和有向搜索测试；只影响离线候选审计，**不修改游戏 Three.js r50dev、赛车物理或碰撞**。仍待真实 GPU、人工完整驾驶、桥梁现场核验及 HexGL CC BY-NC 许可冲突处理。

### 2026-11-01：离线条件单行道审计与 r50 隔离

`tools/osm_bridge_inventory.py` 的机动车 BFS 现保守处理 `oneway:conditional` 和未知方向：无时刻/无法解析时排除道路；给定本地 HH:MM 时只执行简单每日窗口，尊重原始 `oneway` 默认方向。这个改动仅影响离线 GeoJSON 桥梁审计，**不改变 Three.js r50dev、游戏运行时、碰撞或车辆操控**；真实 GPU 性能仍待实测。

### 2026-11-01 M3 离线图搜索边界

tools/osm_bridge_inventory.py 的 via-way only_* 限制不可直接对称反转：正向约束是指定 from 经过 via 只能驶入允许的 to；逆向遍历必须仅在来自非允许 to 时拒绝回到该 from，而不是把 to 错当成只能驶入 from。已增加正反向合成回归。该工具只生成 OSM 桥梁候选审计，不属于 Three.js r50 运行时。

### 2026-11-01 M3 离线强制转弯约束边界

桥梁审计的 `only_*` via-node 规则现在也约束跨越 via 节点但未拆分的同一 OSM way 直行，避免仅按 way ID 相等绕过限制。正反向 BFS 均验证；`no_u_turn` 同 way 回转仍明确不支持。该修改**只作用于 Python 离线数据审计**，不影响 Three.js r50dev、WebGL 资产、M2 路面或驾驶物理。

### 2026-11-01 M3 离线同 way 掉头限制

桥梁 OSM 审计的有向 BFS 在原（节点、way、via-way 上下文）状态中加入**上一节点**，因此能区分同一 OSM way 上的正常直行和在 via-node 原路 U 型折返。`no_u_turn` from/to 同 way 时只阻止折返；正反向测试均覆盖。此变化仅属于 `tools/osm_bridge_inventory.py` 离线分析，不改变 Three.js r50dev、游戏车辆物理、WebGL 或线上部署。真实 GPU/玩家驾驶/桥梁现场核验尚未完成。

### 2026-11-01：离线 via-node 关系拓扑校验

`turn_restriction_rules(..., ways=...)` 在路网审计中核对限制关系的 via-node 是否同时位于 from/to OSM way；不满足的关系列入 unhandled，避免无效 `only_*` 关系错误禁止直行。新增正反向回归，当前真实 OSM 快照未触发此类异常。该修复不进入 Three.js r50dev 浏览器运行时，不改变物理或 WebGL 资源。

### 2026-11-01：r50 离线急弯提示资产

`tools/build_moat_blockout.py` 离线计算相邻 OSM 路段转角，45m 内只选最大角度警示，在弯前约 30m、路外 10.4m 合并生成两种材质的预警牌和箭头。模型仍为旧版 `cmr-static-v1` / `THREE.Geometry`，只增加两个静态 draw calls（+54 tris），没有新增脚本依赖、逐帧路径搜索或物理碰撞。箭头板双面渲染以适配 r50；全部是原创游戏示意，不是 OSM 道路标志数据。

### 2026-11-01：r50 急弯牌离线避让

`sharp_turn_warning_meshes` 通过离线 `polygon_clearance`（射线法内外判断 + 点到多边形边距离）检查 OSM 护城河水面与临街建筑足迹，预留牌宽半径及余量；若转弯侧受阻尝试道路另一侧，两侧均受阻时返回空列表而不是空 Geometry。无浏览器运行时地理计算、无新增依赖或碰撞体；默认模型仍为 70 meshes / 16,738 tris，Three.js r50dev 未更改。

### 2026-11-01：r50 急弯提示离线前置

`SHARP_TURN_WARNING_LEAD_M=80.0` 将两个程序化游戏路牌沿赛道上游提前到约 89.96m / 88.48m，沿用 OSM 水体和建筑轮廓的 ≥1.6m 安全净距检查；只重建 `road.json` 中原有 2 个合并 mesh 的顶点，仍为 70 meshes / 16,738 tris，不添加任何运行时逻辑或 Three.js 新 API。Chrome 148 SwiftShader 18 场景和 Python 64 项回归通过；真实 GPU 和人工视角未验收。

### 2026-11-01：r50 预警牌可见性回归（离线 + 浏览器）

`warning_approach_sightlines` 只在 Python 离线模型生成时检查 30/50m 上游道路点与 2.75m 牌面的建筑足迹遮挡；不添加 Three.js 运行时射线检测、额外网格或碰撞。浏览器回归使用旧 r50 的 `THREE.Projector.projectVector` 与 `Vector3.addSelf`（注意不能当作现代 `Vector3.add` 单参数 API）验证前向道路摄像机的六个投影视点。默认 OSM 模型仍为 70 meshes / 16,738 tris；该检查不能代替真实设备追尾摄像机或人工驾驶视距验收。

### 2026-11-01 路肩恢复空间索引边界

`MoatCollision` 的 80m 格子只保证索引覆盖距离线段 `halfWidth+12m` 范围内的查询点。车辆大幅越界时，即使格子不为空，也不能把其中最近候选当作全局最近路段。`projectInside` 和 `distanceSquared` 现在仅在候选距离超过该 padding（或格子为空）时执行全路线回退扫描；正常路内帧仍使用索引。合成矩形回归在 `tests/moat-regressions.js`。

### 2026-11-01：r50 路线初始化容错

`MoatCollision` 在构造期校验路宽是有限正数、路径点为有限数值且至少存在有效线段，避免 NaN 路宽导致 `distanceSquared > halfWidth²` 恒为 false 而全地图可驾驶。`ChiangMaiMoat` 在构造 analyser 之前校验 spawn 四元数和四个检查点，缺失/损坏的路线脚本将别名回退到 Cityscape。正常 OSM 路线不添加逐帧开销，不升级 Three.js；Node 回归覆盖坏数据。

### 2026-11-01：M2 路线起点/检查点几何安全检查

`ChiangMaiMoat` 初始化 `MoatCollision` 后使用已有 `distanceSquared` 校验 spawn 与四个检查点离中心线不超过 `road_width_m/2 - 0.5m`，并要求 spawn 四元数平方模长约为 1（误差 ≤0.01）。拒绝数值合法但坐标在路外、或无效旋转的 `route-data.js`，使用原 Cityscape 回退。仅执行一次，不引入现代 Three.js API、每帧查询或新的渲染资产；浏览器回归覆盖损坏元数据 HTTP 200。

### 2026-11-01：r50 启动前空间索引预算

`MoatCollision` 构造时先完整预检路网的 80m bucket 范围（点数 ≤10000、单段格数 ≤4096、总插入 ≤100000），然后才填充 buckets；拒绝溢出的线段长度与 `length_m` 和闭环实长严重不符的路线。防止一个有限但巨大的损坏坐标冻结主线程，沿原 `ChiangMaiMoat` 的 Cityscape 回退路径恢复启动。默认 OSM 路线为 650 点、130 buckets / 1610 次插入；不增加逐帧计算、GPU draw calls 或 Three.js 新接口。


### 2026-11-01 M3 碰撞索引近路查询性能修复

`MoatCollision` 的 80m 网格按 `halfWidth+12m` padding 构建，必须同时设置 `searchPaddingSquared=padding*padding`，否则 `distanceSquared()` 与 `projectInside()` 对未定义阈值比较为 false，正常路内查询也退化为扫描全路线。现仅对超过 padding 的查询执行全线段回退；Node 回归对 650 点路线验证正常查询不再全表扫描、极端越界仍返回全局最近路段。微基准仅测 Node 查询耗时，非 GPU 性能。


### 2026-11-01：静态模型整体三角面预算

`StaticModelLoader` 除每个 mesh 的数组上限、总顶点上限外，新增**单个模型所有 mesh 合计最多 2,000,000 个三角面索引**（约 666,666 三角面）。此前只约束单 mesh 索引，数百个分别合法的 mesh 仍可造成 r50 `Face3` 大量分配和加载卡顿。校验在任何几何构造前完成；超限时交给现有 `onError` 回退。正常 `road.json` 50,214 索引、两辆测试车 58,320/6,204 索引，不受影响。这是损坏资产的安全预算，并非渲染性能验收。


### M3 长帧道路碰撞防穿透（2026-11-01）

`MoatCollision.projectMovement()` 用前后帧位置检查长步进是否跨越非道路区域。普通物理帧（位移 <= 路宽半径）仅执行终点投影；长步进按 <= 半径/2 间隔采样，最多 256 步，过长时保守保留合法起点。`ShipControls.collisionCheck()` 只对实现此方法的清迈碰撞适配器启用，不影响 Cityscape。解决端点均合法却跨越古城内部的穿透，**不能替代真实 GPU、手动驾驶或急弯调校验收**。

### 2026-11-01：ShipControls 重赛状态隔离

`ShipControls.reset()` 必须清除上局平滑角速度、旧撞击 `repulsionForce` / `repulsionAmount`、碰撞标志、速度缓存、上次碰撞位置、视觉倾斜及护盾延时。此前仅清除速度和输入，导致重赛首帧可能继承撞击力和转向。Node 污染状态回归和 Chrome r50 真实控制器重赛场景覆盖此契约；正常 M2 路线/物理参数、Cityscape 旧版出生旋转及 Three.js r50dev 不变。


### 2026-11-02：测试专用驾驶控制器的参数复现实验

`tests/corner_ab.py` 在 Chrome 148 headless SwiftShader/r50 上运行 392→408 和 558→578 两段急弯的 A/B（原预瞄 3 点、提前制动、预瞄 2 点），均使用真实 `ShipControls.update(1)` 和 `MoatCollision`，不绕过碰撞。每组从相同坐标/四元数/初速度重置，另复跑基线检测确定性。两组短批次基线 3+4 次路肩修正，预瞄 2 点时 0+0 次；提前制动为 4+5 次。该结论仅针对**测试专用跟随器**，不能推导出玩家手动驾驶一定更快或更容易。完整物理圈可用 `python3 tests/browser_smoke.py --follower-lookahead 2 --physical-laps 1` 对照（默认 3 点仍保持）。

`--follower-lookahead 2` 的完整单圈实测为 **10,399 帧、0 次路肩修正、1,734 条回放采样**，Chrome SwiftShader 24/24 场景通过；这仍不是玩家手动驾驶或生产控制器变更。

同轮 `--follower-lookahead 3` 复测：10,495 帧、9 次路肩修正、1,750 条回放采样，24/24 WebGL 通过；首次运行遇双人启动超时，改用 `--timeout 60` 后通过，根因仍待调查。


### 2026-11-02：M3 OSM 弯道导航 HUD（可关闭）

`bkcore/hexgl/CornerGuide.js` 使用已校验的 `MoatRouteData.points` 构建闭环累计距离，在初始化时找出绝对转角 >=28° 的路段并合并相距 <45m 的连续弯道。每位玩家按自身物理根节点位置在局部 ±12 个路线点搜索（超过 30m 才全局重定位），在 150m 内显示最近急弯方向和剩余距离，每 6 帧更新 DOM；不操作 `ShipControls` 的转向、速度、氮气或碰撞。旧版 r50 无新 API 依赖。

坐标约定：车辆前进方向为局部 +Z、世界 +Y 向上；物理中 `key.left` 增加正 yaw，故在 (x,z) 平面中叉积**负**对应左转、**正**对应右转（不能按通常的屏幕 XY 坐标直接套用符号）。`tests/corner-guide.js` 用合成四边形覆盖两个方向及跨圈预警。

只在有效清迈 OSM 路线、HUD 开启、非回放模式下实例化；菜单仅在真实 `moatMode` 显示选项，Cityscape/坏路线回退隐藏。暂停、重赛、单/双人结算均清理旧提示。此功能属于驾驶信息提示而非 AI 驾驶或真实交通标识，仍须人工试玩/真实 GPU 复核。


### M3 弯道导航最近点容差（2026-11-02）

`bkcore/hexgl/CornerGuide.js` 在真实 OSM 路线约 10m 采样间距下，使用 `road_width_m/2 + 4m` 作为导航定位样本容差（当前 11m）。前次路线点 ±12 的快速搜索若超过该容差，则全局重新捕获；仍在容差外则隐藏导航。旧 30m 容差可能将车辆错误附着到相距 12m 的另一条并行路或在路外显示警告。该逻辑仅用于 HUD 提示，不用于碰撞、车辆转向或物理；测试见 `tests/corner-guide.js` 和 `tests/browser_smoke.py`。


### 2026-11-02：M3 弯道 HUD 最近道路点选择

`CornerGuide.nearestIndex` 每 6 个物理帧执行一次，使用全部 650 个 OSM 采样点的最近点定位（双人分别缓存索引），而非仅凭上次索引前后 12 点的局部窗口是否落入 11m 容差。这样相距 8m 的并行道路也不会因旧窗口仍在容差内而显示错误方向。严格更近的点覆盖缓存，等距保留之前的索引以减少提示跳变；离路仍隐藏。Node 10,000 次定位单次微基准约 51.7ms，真实 GPU/帧率尚未测量。


### 2026-11-02：M3 弯道 HUD 连续路段投影与格索引

CornerGuide.locate(x,z,player) 以连续道路线段的最近正交投影定位，不再仅按 650 个采样端点距离定位。以段内 t 计算到下一个弯道的沿路距离，避免采样点之间的距离台阶和相邻并行道路误定位。为避免每 6 帧全线段投影，构造时建立 80m 空间格，按路宽容差扩张线段 AABB；查询只访问当前格候选段，超出容差直接隐藏提示。格预分配设置预算，防止异常路段造成无界分配。旧 nearestIndex 仍供测试/兼容使用。Node 合成并行道路和真实 OSM 250 点差分回归覆盖最近段正确性；此更改仅影响可选 HUD，不影响碰撞/赛车物理。


### M3 CornerGuide 朝向一致性（2026-11-02）

导航沿 OSM 单向路线计算未来转角，但玩家可能掉头逆行。现在读取 `ShipControls.dummy.quaternion`（物理朝向，而非倾斜车壳），将局部 +Z 旋转后的 XZ 前向与最近中心线线段切线点积比较；夹角超过 120° 时暂时隐藏正向左/右提示。避免旧版 Three.js r50dev 中 `THREE.Quaternion` API 版本差异，使用标量四元数公式；不改变碰撞、氮气、速度、转向或资产。缺少四元数的诊断/测试调用仍保留旧提示行为。


### M3 窄路肩间隙的短帧扫掠碰撞（2026-11-02）

- 原 `MoatCollision.projectMovement()` 仅对超过半路宽（7m）的移动沿路径采样；在两条 14m 道路带中心线相距 18m、非道路间隙 4m 的合成场景中，6m 移动的起终点都合法，旧实现会穿透。
- 现在对超过 1m 的移动按最多约 1m 间距离散采样；<=1m 的普通帧维持单次终点检查，超过 256 步的异常移动仍恢复到起点。此变更只涉及 M2/M3 `MoatCollision`，不改 Cityscape 或车辆操控。
- Node 测试先复现、修复后通过；这是有限间距的离散碰撞，仍可能遗漏亚米级非法间隙。


### 2026-11-02：OSM 道路扫掠碰撞的距离上界

`MoatCollision.projectMovement()` 不再仅以 1m 固定采样覆盖合法起终点的移动：道路距离函数满足 1-Lipschitz，对长度 `L`、端点道路距离 `d0,d1` 的移动区间，内部最大距离不超过 `(d0+d1+L)/2`；证明安全的区间直接通过，其余区间二分检测。普通中心车道帧用终点距离加位移长度直接快速证明。上限 256 次检测/20 层，2cm 数值容差；短帧普通路肩越界继续使用 `projectInside()` 回投，避免车辆在急弯反复卡住。此实现是有界近似而非严格 CCD，仍需真实 GPU 和人工驾驶测试。

### 2026-11-02：极窄路线的碰撞回投约束

`MoatCollision.projectInside(x,z,margin)` 回投点距最近道路中心线不得超过 `halfWidth`。原固定 `max(0.5, halfWidth-margin)` 对小于 1m 的正路宽违反此约束；现用 `max(0, halfWidth-max(0,margin))`，窄路可回到中心线。普通 14m 宽、0.8m margin 仍回投至 6.2m，保持既有赛车物理/氮气/Three.js r50dev 行为。Node 回归覆盖异常窄路与正常宽度。


### 2026-11-02 M3 短帧回投与连续扫掠

`MoatCollision.projectMovement` 的短帧 `projectInside` 回投可能选到邻近的另一条道路。现在通过内部 `checkingRecovery` 模式复用现有有界扫掠认证，只有回投路径合法才允许跳到回投点；普通同侧路肩仍按原规则回投。新增 Node 与真实 r50 `ShipControls` 浏览器回归，详见 `docs/WORK_CONTINUITY.md`。保留 2cm 数值容差与有限计算预算，不宣称精确 CCD。

### 2026-11-02 OSM 分析器坐标精度

旧 Cityscape `getPixel()` 使用整数位图像素，OSM `MoatCollision.getPixel()` 则以连续世界米为单位。Gameplay.checkPoint 和 ShipControls.boosterCheck 现在仅对位图分析器取整，对带 `projectInside` 的 OSM 分析器保留浮点坐标；斜向道路边缘的检查点/加速带已由 Node 与 Chrome r50 回归覆盖。保持 Three.js r50dev，不改碰撞走廊或车辆物理。

### 2026-11-02 M3 Gameplay 检查点扫掠补判

`Gameplay.checkPoint()` 在 MoatCollision 分析器下保存上次检查点采样米坐标；如果当前点未落入检查点圆盘，则计算上次点到当前点的线段与**下一个**检查点 12m 圆盘的最近距离。只有起点仍在合法道路上且 `MoatCollision.projectMovement(..., checkingRecovery=true)` 认证整段直线路径未越界，才返回检查点索引；这样可以修复帧率卡顿/逻辑抽样跳过圆盘而无法计圈的问题，不允许通过穿城捷径补得检查点。`Gameplay.start()` 清理采样状态，Cityscape 仍只使用原始整数位图。Node 与 Chrome r50 测试通过。直线段近似在复杂弯道可能保守漏判，仍需人工驾驶验证。

### 2026-11-02 M3 检查点直接命中的异常大步进验证

`Gameplay.checkPoint()` 原来只对终点未命中检查点圆盘的跨帧补判执行 `MoatCollision.projectMovement`；终点恰好落在圆盘内的非法跨城移动会直接计点。现在对 OSM **下一个检查点**的直接命中，当上次到当前采样的直线距离超过 24m（检查点半径 12m 的两倍）时检查起点仍在路内、整段直线未越界。正常短帧保留快速路径；Cityscape 位图不变。浏览器模拟传送检查点的测试必须同步设置测试用 `_lastCheckpointSample`，物理路线跟随器不能注入此状态。

### 2026-11-02 M3 OSM 检查点可信采样

`Gameplay.checkPoint()` 对 `MoatCollision` 的每个游戏逻辑采样调用 `projectMovement(previous.x, previous.z, x, z, 0.8, true)`，而不是只对 >24m 的终点命中或跨帧补判扫掠。只有认证成功才推进 `_lastCheckpointSample`，拒绝的终点停留也不会在下一帧自动成为可信起点；跨帧圆盘检测复用已认证的路径。该校验与车辆物理碰撞独立，不更改 Three.js r50dev 或 Cityscape 像素检查点。额外 CPU 成本、急弯长帧直线近似和异常跳跃后的恢复策略仍需后续实测。

### 2026-11-02 r50 回放时间游标兼容性

`bkcore/hexgl/RaceData.js` 的 `applyInterpolated(time)` 原先只递增 `seek`，导致调用方在同一份回放中倒退时间时错误地保留未来帧的位置。现允许游标回退后继续原有 `THREE.Vector3.lerpSelf` / `THREE.Quaternion.slerpSelf` 插值；不引入新 Three.js API，不修改车体物理。`tests/racedata-regressions.js` 先复现失败后修复，`tests/browser_smoke.py` 使用真实 r50 WebGL 验证末帧→中间→首帧定位。该兼容性修复不意味着已有可交互回放拖动界面。

## 2026-11-02 r50 回放四元数输入边界

`RaceData.import` 从 localStorage 读取旧版八字段回放帧。即使四元数分量均有限，零长度或过大模长也可能使 r50 `Quaternion.slerpSelf` 的 `acos(dot)` 接收到无效输入。现在校验每帧四元数平方模长与 1 的差不超过 0.02，并在插值前对四元数归一化，允许微小旧数据舍入误差。Node 回归先复现无校验缺陷；Chrome 148 r50 实际回放验证损坏帧拒绝和正常归一化。未修改 Three.js r50dev。

### 2026-11-02 · r50 回放输入边界

- `bkcore/hexgl/RaceData.js` 导入外部回放帧时先验证时间、数值和单位四元数，再对每帧进行浅复制（帧内均为数字），避免调用方事后篡改输入数组绕过校验。保持旧版 `THREE.Quaternion` 插值方式不变。

### 2026-11-02 · RaceData seek 复杂度与重复时间戳语义

`RaceData.applyInterpolated(time)` 之前通过两条 `while` 逐帧移动 `seek`，从 65,536 帧回放末尾跳回起点为 O(N)，且重复时间戳在不同 seek 历史下可能返回不同姿态。现当时间仍在当前半开区间 `[data[seek].time, data[seek+1].time)` 时保留 O(1) 快速路径，否则通过 upper_bound 二分找到 `<= time` 的最后一帧（O(log N)）；同一时间戳以最后记录帧为准，时间恰好落在最后帧即钳制到最后帧。拒绝非有限时间以避免向旧 r50 插值传入 NaN；不修改引擎依赖、赛车物理或道路。

### 2026-11-02 · r50 回放持久化接线

`HexGL.displayScore` 在单人 FINISH 后调用 `RaceData.save(localStorage)`；`RaceData.save` 创建独立验证快照，复用 import 的时间单调、有限坐标与单位四元数约束，只有通过才向 `race-<track>-replay` 写入 JSON。写入失败返回 false，成绩页照常展示；原 replay 模式只读取、不覆盖存档，双人和损毁不保存。旧 Three.js r50dev 插值与物理逻辑未改。

### 2026-11-02 · r50 赛后回放界面

`HexGL.openReplay` 在已完成的单人比赛中校验并导入 `race-<track>-replay`，使用同一个 Three.js r50dev 场景与 `RaceData.applyInterpolated` 更新车体姿态；`Cityscape.buildScenes` 的通用渲染循环在 `ctx.replayViewer` 非空时跳过 `ShipControls.update(dt)`，但继续更新追踪相机和画面。回放时间轴独立于 Gameplay 倒计时/比赛计时，拖动会暂停，播放到末尾会停在最后姿态；Esc/按钮退出恢复成绩页；回放期间暂时隐藏底部氮气 HUD，避免覆盖时间轴的点击区域。坏 JSON 不能进入回放，结束和返回不会覆盖录制。此 UI 不是跨会话回放列表或视频导出，也未验证真实 GPU。

## 2026-11-02：跨页面回放入口的 r50dev 兼容约束

- `launch.js` 在主菜单按赛道名称读取最近一次 `race-<track.name>-replay`，复用 `RaceData.import()` 校验并缓存同一存档的有效性。仅在单人且有至少两帧、正时间跨度的有效记录时显示入口。
- `HexGL.openReplay(fromMenu)` 复用同一个 r50dev 场景/轨迹插值，菜单入口不要求此前的完赛结果；仍禁止双人回放。`HexGL.update()` 回放分支跳过 `Gameplay.update()`，不会调用驾驶物理；菜单回放关闭时刷新页面以释放旧 WebGL 资源，赛后回放保持返回成绩页。
- 不引入现代 Three.js API 或打包依赖；存档仍为原有 JSON 帧数组，不能视为视频或长期多版本录像库。

### 2026-11-02 · r50 回放持久化的可观看性约束

`RaceData.import()` 保留对单帧及重复时间戳历史数据的安全解析/插值；但 `RaceData.save()` 在验证并快照后要求 `last >= 1`、`firstTime >= 0`、`lastTime > firstTime`，否则返回 false 且不调用 `storage.setItem`。这样 `HexGL.displayScore()` 不会把上一次有效录像替换成主菜单/播放器均拒绝的部分录制。Node 回归覆盖三类边界及保留旧存档；不引入新 Three.js API。

### 2026-11-03 · 旧版 WebAudio 加载的可选依赖

`bkcore.Audio.addSound` 原先在 HTTP 404、网络错误或 `decodeAudioData` 失败时不完成回调，导致 `bkcore.threejs.Loader.progress.loaded` 无法达到 total、`launch.js` 等不到 `onLoad`。现采用 15 秒看门狗和单次完成保护；失败音效安全静音，`play/stop/volume` 不再对缺失 buffer/gain 解引用。保留旧 HTMLAudioElement 回退和 file:// status 0 + 有效响应。`Loader.loadSound` 补传 `usePanner` 标志，沿用现有 WebAudio panner 而不引入现代 API。Node 回归与 Chrome 故意 404 场景验证；浏览器超时诊断显示 pending 资源。本修复只覆盖已证实的音频死锁路径，不代表所有历史偶发超时均已解决。

### 2026-11-03 · r50 图片加载失败兼容

`THREE.ImageUtils.loadTexture` 在 r50dev 返回 `THREE.Texture`，异步失败回调不会自动通知 `bkcore.threejs.Loader` 完成。现在 `Loader.loadTexture` 失败时使用 2×2 白色 Canvas 替换 `texture.image` 并设置 `needsUpdate=true`，`Loader.loadImage` 则为 HUD 返回 192×25 透明 Canvas，保持 1920:250 宽高比和 `drawImage` 可用性。`updateState` 只计入一次完成事件，避免加载回调重复执行。此策略针对普通贴图与 HUD 图片；不等于天空盒立方贴图、旧 JSON 几何或碰撞图的所有错误均已处理。

### 2026-11-03 · r50 天空盒六面加载保护

`THREE.ImageUtils.loadTextureCube` 在当前 r50dev 只有六面全成功的完成回调，没有失败回调。为兼容 WebGL 1 的 cubemap 完整性约束，`bkcore.threejs.Loader.loadTextureCube` 直接使用相同的 `new THREE.Texture(images, new THREE.CubeRefractionMapping())`、`flipY=false`；每张图片安装 `onload/onerror`，统一 15 秒超时。任何一面失败后全部六面替换为尺寸一致的 2×2 Canvas，并标记 `needsUpdate`。正常六面保留原图，晚到事件不重复计数。没有改动 Three.js r50dev 源文件。


### 2026-11-03 · 旧版 JSONLoader 的无错误回调缺陷

r50dev `THREE.JSONLoader.loadAjaxJSON` 对非 200、空响应、解析异常或无响应缺乏可靠失败完成回调。`bkcore.threejs.Loader.loadGeometry` 现使用受控 XHR（15 秒超时、onerror/onabort、一次性完成），成功仍通过 `JSONLoader.createModel` 构造原始 r50 `THREE.Geometry`；失败时报告资源名并返回空 `THREE.Geometry`，避免可选旧几何拖住整个加载界面。Node `tests/geometry-failures.js` 与 Chrome 故意 404 booster 的真实 WebGL 场景通过；Chrome SwiftShader 完整 35/35。缺失的模型不可见，不能替代核心道路/碰撞数据；`bkcore.ImageData` 核心分析图的故障处理仍待单独设计。Three.js r50dev 文件未修改。


### 2026-11-03 · ImageData 物理分析图 fail-closed 加载协议

`bkcore.coffee/ImageData.js` 与对应 CoffeeScript 源码现在支持可选第三参数 `errorCallback(reason)`：对图片 onerror、15 秒超时、零尺寸、Canvas 上下文、像素缓冲长度异常或 `getImageData` 异常均一次性失败，保持 `loaded=false`、`pixels=null` 并标记 `failed=true`。成功回调仅在像素可读后触发，超时及迟到事件不能反转结果。
`bkcore.threejs.Loader.loadAnalyser` 在故障时报告资源名、登记 `progress.failed/failures`、只触发一次 `onFatal(name)`，然后结算该资源的进度；`updateState` 在任何核心 analyser 故障后即使全部资源完成也不调用 `onLoad`，防止 `HexGL.init` 使用缺失的碰撞/高度图。浏览器 `launch.js` 的 onFatal 在加载页显示中文错误和重试按钮。仅 Cityscape 资源清单使用此位图分析器；正常 M2 OSM 赛道仍由 MoatCollision/HeightMap 处理物理。该策略不是图像内容真实性校验，也不等于真实 GPU 验收。

### 2026-11-03 · r50 可选图片无响应与迟到事件

`Loader.loadTexture`/`loadImage` 除了 404 降级，还须覆盖浏览器既不触发 `onload` 也不触发 `onerror` 的挂起请求。两者现在各有 15 秒 watchdog，成功/失败/超时共用一次性完成回调，及时清除定时器；超时材质使用 `Texture.image` 的 2×2 Canvas 并设置 `needsUpdate`，HUD 使用 192×25 透明 Canvas。Node 回归覆盖挂起、迟到回调与精确计数；`tests/browser_visual_timeouts.py` 使用本地延迟 HTTP 图片请求验证真实 Chrome SwiftShader WebGL 15 秒后正常启动与重开。不修改 Three.js r50dev 源码或核心碰撞分析图的 fail-closed 策略。

浏览器测试诊断额外捕获启动按钮点击阶段的 JS `error/unhandledrejection`，用于区分 r50 WebGL 上下文创建异常与资源计数死锁。第二轮完整 Chrome SwiftShader 37/37 通过，但第一轮 `window.hexGL` 未创建的偶发超时仍待定位。

## 2026-11-03：旧 r50 几何的必需/可选资源语义

`bkcore/threejs/Loader.js` 的资源清单支持可选 `requiredGeometries` 映射；当前 Cityscape 低/高画质都将 `track.cityscape` 标为 true。加载失败、模型空顶点或零面时通过 `progress.failed/failures` 与 `onFatal` 安全停止，继续推进计数用于诊断，但不触发 `onLoad`；可选模型继续使用空 `THREE.Geometry`。这与 Cityscape 碰撞/高度分析图的 fail-closed 策略一致，避免在缺少道路或物理资源时开始比赛。Node `tests/required-geometry.js` 覆盖 404、空模型、超时、迟到回调、两种画质和可选资源；Chrome 完整 38/38 场景通过。

**维护注意**：实际浏览器执行的是 `launch.js`，仓库中的 `launch.coffee` 仍是早期版本，未同步 M2/M3 逻辑；未经完整迁移与回归，禁止直接用旧 CoffeeScript 重编译覆盖 `launch.js`。真实 GPU/WebGL 性能及旧 HexGL CC BY-NC 授权问题仍未解决。


### 2026-11-03 · StaticModelLoader 独立看门狗

`THREE.StaticModelLoader.load` 仍保留 `xhr.timeout=30000`，但为不派发超时/网络事件的浏览器/协议增加独立 30 秒 JS `setTimeout`；成功、解析失败、网络故障、原生超时及看门狗都由单次 `finish()` 结算并清理定时器。M2 `road.json` 触发 `onError` 后调用已有完整 Cityscape 回退；同一加载器的可选车辆模型也不会永久挂起。Node `tests/static-loader-watchdog.js` 和 Chrome SwiftShader `tests/browser_road_timeout.py` 验证了静默挂起、迟到事件、坏 JSON、HTTP 恢复和可玩回退；不涉及升级 Three.js r50dev 或改变物理。


### 2026-11-03 · M2 道路模型语义校验

`THREE.StaticModelLoader.build` 负责 `cmr-static-v1` 的通用几何有效性；`ChiangMaiMoat.load` 另外要求 `road.json` 的 `race-asphalt` 符合当前路线生成器契约：每个中心线点两侧各一顶点、每段两个三角面，左右边界中点与路线中心线匹配、宽度与 `road_width_m` 匹配，r50 Geometry 实际具有可绘制面。无论 HTTP 是否成功，缺失或错位路面都走完整 Cityscape 回退。保持旧版 Three.js r50dev 和独立 MoatCollision 物理逻辑不变；离线生成器修改道路拓扑/顶点排列时，须同步维护此契约和回归。

### 2026-11-03 · r50 OSM asphalt strip 的拓扑契约

`StaticModelLoader.validate` 只校验面索引范围，无法判断合法索引是否连接了正确的道路顶点。`ChiangMaiMoat.validRoadModel` 因此在检查每个截面中点/宽度之外，验证 `tools/build_moat_blockout.py::strip_mesh` 的每段两个三角形索引 `[a,a+1,b,a+1,b+1,b]`（`a=2*i,b=2*((i+1)%n)`）。否则在创建比赛前回退 Cityscape，避免错误网格在 WebGL 绘制跨城巨面。若未来更改离线三角化规则，必须同步更新此契约与 Node/Chrome 回归；未修改旧版 Three.js r50dev。
验证：Node 12 套、Python 65/65、Chrome 148 SwiftShader 40/40（错接索引回退）；真实 GPU 仍待测。

### 2026-11-03 · r50 静态模型 offset 与 M2 道路语义校验

`THREE.StaticModelLoader.build()` 支持对任意 mesh 的本地顶点再应用 `mesh.offset`，而 `ChiangMaiMoat.validRoadModel()` 之前只检查 JSON 顶点中点/宽度/三角拓扑，未把渲染后的平移算入。当前 `race-asphalt` 是世界米坐标，故校验拒绝非零 offset，并按离线 `strip_mesh` 法线逐点确认左右边缘及平坦示意高度 +0.08m；可选其他建筑 mesh 的 offset 不受影响。保持旧 Three.js r50dev 不变，未来真实高程或道路生成格式变化时必须同步修改契约与回归。

Node 12 套、Python 65/65 与 Chrome 148 SwiftShader **41/41** 通过，新增浏览器用真实 r50 `StaticModelLoader` 构建 HTTP 200 非零 offset 道路并确认回退；不升级旧引擎。

### 2026-11-03 · r50 道路网格唯一性与材质语义

`StaticModelLoader.validate` 只保证通用 `cmr-static-v1` 结构合法；多个名为 `race-asphalt` 的 mesh 或将合法道路设置为透明，仍能通过通用验证并构造 r50 Geometry。`ChiangMaiMoat.validRoadModel` 现额外检查 JSON 中恰好一个同名网格、构建后 `Object3D.children` 中恰好一个对应网格，且道路使用 `road` 材质、不启用透明、opacity≥0.95；否则回退完整 Cityscape。此校验与路面中心线/截面/三角索引/offset 约束并列，未来改变生成器的道路材质约定必须同步更新。未修改 Three.js r50dev 库。

验证：Python 65/65、Node 12 套、Chrome 148 SwiftShader **43/43**；道路唯一性/材质回退在真实 r50 模型加载路径上通过。`transparent` 判断使用与加载器一致的 truthy 语义（`!!`）。

### 2026-11-03 · ShipControls M2 冻结与氮气边沿状态

Cityscape 旧 `nitroCheck` 即使 inactive 仍先更新 `nitroKeyPrev` 并清空一次性 `nitroRequest`。M2 为冻结倒计时车辆而提前 return，漏掉这两项输入状态维护，导致预先按住的键或触摸请求在比赛开始后被当作新指令。`ShipControls.update` 的 M2 inactive 分支现在仅同步键位边沿并清除待发请求，保留冻结物理与 Cityscape 行为。`tests/regressions.js` 和 `tests/browser_smoke.py` 覆盖倒计时按住、排队触摸和正式比赛重新按下；不改氮气加速度/时长/消耗值及 Three.js r50dev。
