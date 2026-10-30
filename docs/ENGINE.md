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
2. 在 `ShipControls.js` 中把飞船模型替换为车辆模型。
3. 调整：
   - 车辆长度 → 碰撞半径
   - 相机高度 / 距离
   - 转向轴心
   - 车轮旋转（可选）
4. 保留原飞船作为 fallback（`?ship=1` 或配置开关）。

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
