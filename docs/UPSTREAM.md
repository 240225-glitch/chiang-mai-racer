# 上游项目：HexGL

本项目是 [HexGL](https://github.com/BKcore/HexGL) 的衍生版本。
上游代码与素材采用 **MIT License**，原始版权归 **Thibaut Despoulain（BKcore）** 所有。

本仓库保留了上游的 Git 历史，以便追溯来源。`upstream` remote 指向上游仓库，`origin` 指向本项目的 GitHub 仓库。

---

## 原始 README（上游）

```text
HexGL
=========

Source code of HexGL, the futuristic HTML5 racing game by Thibaut Despoulain

## Branches
  * Master - Public release (stable).

## License

Unless specified in the file, HexGL's code and resources are now licensed under the MIT License.

## Installation

	cd ~/
	git clone git://github.com/BKcore/HexGL.git
	cd HexGL
	python -m SimpleHTTPServer
	chromium index.html

To use full size textures, swap the two textures/ and textures.full/ directories.

## Note

The development of HexGL is in a hiatus for now until I find some time and interest to work on it again.
That said, feel free to post issues, patches, or anything to make the game better and I'll gladly review and merge them.
```

---

## 本项目的改动

### 已完成

- 移除 Google Analytics 统计与外链 favicon，支持完全离线运行
- 菜单、提示、制作名单汉化
- 增加中文键位提示与 `start-game.bat` 启动脚本
- 新增氮气系统、加速带补氮气
- 新增 1 / 3 / 5 圈选择与休闲 / 竞技难度
- 新增暂停 / 继续 / 重新开始
- 新增本地最佳成绩（按赛道 + 难度 + 圈数）
- 增强版结算页：总用时、最佳单圈、每圈成绩、历史最佳
- 新增同屏双人分屏：双相机、双 HUD、双氮气面板、胜负判定
- 赛道在 X / Z 方向放大 1.5 倍，移除城市高楼
- 检查点改为发光立式光环
- 提高转向响应，降低操控难度
- 修复暂停 / 重开后计时与状态恢复问题

### 进行中

- 用清迈古城护城河环线替换 Cityscape 占位赛道
- 建立 OBJ → 自定义 JSON 资产管线
- 接入 CC0 低模车辆

### 已暂缓

- 战斗系统（`bkcore/hexgl/Weapons.js`）
- Doi Suthep 登山赛道

---

## 为什么保留上游历史

- MIT 许可要求保留原始版权声明。
- 保留历史便于对比上游改动、回溯 bug。
- 上游仍可能更新，保留 `upstream` remote 方便合并。

## 如何同步上游

```bash
git fetch upstream
git merge upstream/master
```

> 注意：本项目对 `HexGL.js`、`Gameplay.js`、`ShipControls.js`、`Cityscape.js` 等文件改动较大，合并时需手工解决冲突。
