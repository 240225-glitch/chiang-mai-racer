# tools

## obj2json.py

把 Wavefront OBJ + MTL 转成 `cmr-static-v1` JSON，供 Three.js `r50dev` 使用。
无第三方依赖。

```bash
python tools/obj2json.py <input.obj> <output.json> \
  --name <model-name> \
  --license CC0-1.0 \
  --author <author> \
  --target-length 5.28 \
  --center \
  --merge-untextured
```

### 参数

| 参数 | 说明 |
| --- | --- |
| `--name` | 模型名，写入 JSON |
| `--license` / `--author` | 许可与作者，写入 JSON |
| `--scale` | 统一缩放 |
| `--target-length` | 按最长包围盒边缩放到指定米数 |
| `--rotate-x` / `--rotate-y` | 旋转（度），用于修正 Z-up 等 |
| `--center` | X/Z 居中，最低点落到 Y=0 |
| `--merge-untextured` | 默认开启；把无贴图材质合并成一个顶点色 mesh |
| `--no-merge-untextured` | 保留每个无贴图材质为独立 mesh（调试用） |
| `--double-sided` | 双面渲染，适合树叶 / 布料 |
| `--pretty` | 输出带缩进的 JSON |

### 约定

- 1 unit = 1 m
- +Y 向上
- +Z 车头
- 贴图复制到输出目录的 `textures/`
- 输出只包含转换产物，不包含源 `.obj` / `.mtl`

### 示例

```bash
python tools/obj2json.py assets-src/kenney/race-future.obj \
  assets/cars/kenney-race-future/model.json \
  --name kenney-race-future --license CC0-1.0 --author Kenney \
  --target-length 4.4 --center --merge-untextured
```

## model-preview.html

在旧版 Three.js `r50dev` 里预览转换后的模型。

```bash
python -m http.server 8080 --bind 127.0.0.1
```

打开：

- <http://127.0.0.1:8080/tools/model-preview.html>
- <http://127.0.0.1:8080/tools/model-preview.html?model=kenney>

功能：拖拽旋转、滚轮缩放、自动旋转、显示面数/尺寸/许可。

## 已知兼容性问题

- **`THREE.Color(r, g, b)` 在 r50 中无效**：构造函数只接受一个十六进制参数。顶点色必须用 `color.setRGB(r, g, b)`，并且要写入 `Face3.vertexColors`，只写 `geometry.colors` 不会生效。
- **贴图必须是 2 的幂**（256 / 512 / 1024 / 2048），否则 WebGL 1 下无法生成 mipmap。
- **没有 InstancedMesh**：重复道具要合并几何，不能靠实例化。
- **没有 glTFLoader**：所有新资产必须先跑本脚本。

## 新增车辆流程

1. 下载 CC0 原始包到 `assets-src/`（已被 `.gitignore` 忽略）
2. 检查 `LICENSE`
3. 跑 `obj2json.py`
4. 用 `model-preview.html` 验证尺寸、朝向、颜色
5. 把 `LICENSE.txt` 复制到 `assets/cars/<name>/`
6. 更新 `CREDITS.md` 与 `docs/ASSETS.md`
7. 提交 `assets/` 下的转换产物，不提交 `assets-src/`
