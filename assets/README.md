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
