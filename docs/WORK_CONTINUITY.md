# 周期任务的连续开发交接

更新时间：2026-10-31

## 权威位置和保护范围

- 上游公共仓库：https://github.com/240225-glitch/chiang-mai-racer
- 服务器 SentinelX 主机：RainYun-YK446zN9
- 已存在四个基础提交：b5f3568（旧游戏 bug 修复）、dd1dac9（M1 车辆）、f422e80（M2 示意赛道）、ce6fe1f（GeoJSON 导入）。每轮以实际 git log 为准。
- **后续真实工作目录：/var/lib/sentinelx/chiang-mai-racer-dev**。这是 SentinelX 服务用户可读写的持久隔离 Git 工作副本，不能误认为 /tmp 目录。
- GitHub 当前连接读取允许、推送不允许。任何本地提交应继续保存在此目录，可导出 patch/zip，但不能假称已推送。
- **严禁覆盖 /www/wwwroot/gta.jizhang.org**：这是另一套已部署游戏，不是该仓库。
- 每次运行开始先检查 git status、git log、交接文档和最新自动化测试，避免覆盖其他轮次的新改动。

## 实际工程进度

- M0：文档与路线规划完成。
- M1：r50 模型管线、两辆 CC0 汽车接入、原飞船回退、回归测试通过；WebGL 浏览器实机待验收。
- M2：已生成示意 6,579.7 米护城河环线模型；默认 Cityscape 保留，?track=moat 代码路径已接入，包括碰撞走廊、4 个检查点、3 个加速带和专用物理参数；真实道路 OSM 导入及浏览器实机待完成。
- M3–M6：尚未进入。

## 本地复现

    cd /var/lib/sentinelx/chiang-mai-racer-dev
    python3 tools/build_moat_blockout.py
    python3 -m unittest discover -s tests -p 'test_*.py' -v
    node tests/regressions.js
    node tests/moat-regressions.js
    git diff --check

## 下一批任务

- 首要：获取和验证 OSM 古城外圈顺时针道路、标记 ODbL 许可、将实际路段替换示意圆角矩形。
- 同时：WebGL 实际浏览器检查；检查加载失败时是否可玩、碰撞和绕圈（单人/双人）是否正常。
- 之后：删除 M2 对 Cityscape 多余大资源的依赖，按 M2 和 M3 验收清单逐步补场景。
- 持续修复发现的 bug，新增回归测试并提交；不要因单个小任务成功自动停止整轮工作，更不要停止周期任务。

- 2026-10-31 补充：M2 生成器已支持 --geojson 导入闭合 LineString，方向修正、长度验证和 SHA-256 来源标识。Overpass 请求超时，默认资产仍为示意路线。后续优先导入真实 OSM 外环道路，并记录来源许可。

## 本轮 2026-10-31 浏览器验收与回归

- 发现 launch.js 将 URL 参数当字符串，导致 ?players=1 仍是单人、?hud=1 反而关闭 HUD。已转换为有范围校验的数字参数，并将首页最佳成绩键按赛道隔离。
- tests/launch-options.js：Node VM 测试 URL 模式、HUD、画质、圈数、无效参数及成绩键。
- tests/browser_smoke.py：Google Chrome 148 + Selenium + SwiftShader，运行本地 HTTP WebGL 测试，7 个场景全部通过：预览、M2 单人键盘加速及模拟完整一圈、M2 双人独立 HUD/检查点、M2 高画质、M2 极高画质、默认 Cityscape、M2 资源 404 回退。
- 注意：这是无 GPU 的 headless WebGL 冒烟测试，不等于用户设备完整试玩/手感或 60fps 验收。不能标记 M1/M2 全部完成。
- 本轮发现并修复 M2 重复下载 Cityscape 的无关贴图、旧道路网格、分析图：改为先加载 M2 road.json，再用精简清单加载旧版必要的天空、飞船、HUD 和音频。低画质加载项从 28 降到 15，较高画质为 17。M2 道路加载失败时仍使用原 Cityscape 完整资源并可玩。7 个 headless WebGL 测试重新通过。

- OSM 取数尝试：2026-10-31 Overpass private.coffee 超时，nchc.org.tw DNS 解析失败；不要伪称已导入真实道路。下一轮可尝试其他公开 OSM 数据快照/网络条件，仍须核对许可与道路拓扑。


## 2026-10-31 续轮：严格 GeoJSON 及斜向起跑修复

- 本轮开始已核对实际 git log/status 和 WORK_CONTINUITY、ROADMAP、M2-BLOCKOUT、ENGINE，基线为 ffd16d1（ahead 7），工作区干净。
- GeoJSON 导入器拒绝大于 0.1m 的不闭合缺口、自交、极短段、非法经纬度、偏离古城 3km 的路径；检查重采样路径长度变化。
- 赛道元数据现在输出起点切线 yaw 和完整 quaternion；ShipControls.reset 保持旧版缺省 w=1 兼容；M2 双人发车沿道路法线偏移 2.8m，四组门框按切线旋转。
- 测试：Python 几何 10 项通过；node tests/regressions.js、tests/moat-regressions.js、tests/launch-options.js 通过；Chrome 148 SwiftShader 7 场景通过，增加双人出生点位置和方向验证。
- Overpass 数据重试：kumi.systems、private.coffee、overpass-api.de 均在 11s 读超时，nchc.org.tw DNS 失败。未获取真实 OSM，不得标记 M2 完成。
- 下一步：继续合法 OSM 取数/拓扑拼接、真实道路数据测试；实机 GPU、全圈手动驾驶和性能；必要时做独立可测试的导入管线与地标原型。
- GitHub 仍未验证可推送；以本地提交为准，严禁触碰无关线上 gta.jizhang.org。


### 本轮新增浏览器回归（8 场景）

tests/browser_smoke.py 增加第 8 场景：HTTP 测试服务器仅在内存里覆盖 road.json 和 route-data.js 为旋转 45° 的合成赛道；验证 M2 两车均在 14 米道路走廊内、与道路法线并排、首车经过真实 ShipControls 物理加速后沿新路线切线前进。无需修改真实资产。最初一次测试失败仅因为仍处于倒计时，已增加等待 gameplay.step==4；随后失败是前一个预期 404 日志未清空，已隔离测试日志。最终 8/8 通过。尚不等于真实 OSM 或 GPU 实机驾驶。

## 2026-10-31：真实 OSM 外圈道路导入

- 官方 OSM API /map 小范围 bbox=98.977,18.780,98.994,18.797 成功返回 10,955,870 字节 XML（40941 nodes，1426 road ways）。原始 XML 仅暂存 /tmp/chiang-mai-racer-osm-20261031.xml，SHA-256 63cda4fd16cdc4c20421f68de0055538b2fd104d4c9d3a0a8f5239324b4b8934。
- 新增 tools/osm_outer_ring.py：按 OSM 单行方向与共享节点拼接外圈道路，236 节点、90 ways、5 条具名道路、原始 6,497.5 m，重采样后 6,492.2 m、650 点。结果入库 assets/tracks/chiangmai-moat/source-osm.geojson；生成器默认使用此来源，--schematic 仍可单独生成旧示意。
- 生成 road.json、route.json、route-data.js 并加入 ODbL 来源/哈希/日期；index.html 和预览页加 OSM 署名，游戏赛道名称更新为 OSM prototype。CREDITS、README、ROADMAP、ENGINE、M2、MAP-DESIGN、assets/README 更新。
- 这是真实 OSM 道路**中心线**，但统一 14m 游戏路宽、护城河条带与门框仍为程序化示意；需人工逐段核实 90 ways/交通方向和城门坐标、真实 GPU/手动驾驶测试。下一轮继续性能与街景，绝不触碰线上 gta.jizhang.org。

- **新发现的许可风险**：9 个原始 bkcore/hexgl JS 文件头标注 CC BY-NC 3.0，与仓库根目录 MIT LICENSE/CREDITS 说明冲突。已在 CREDITS/README 明示，不擅自移除旧声明。后续应核实上游许可证历史与商业使用权限。

- **本轮最终验证**：14 项 Python 单测通过；node tests/regressions.js、tests/moat-regressions.js、tests/launch-options.js 通过；Chrome 148 SwiftShader 8/8 headless WebGL 冒烟通过（含真实 OSM 来源/署名断言、双人、模拟计圈、资源失败回退及旋转合成路线）。首次重跑遇短暂 Selenium 超时/连接重建，重新执行后 8/8 通过。真实 GPU/手动整圈仍未测。

- **M2 OSM 水体继续推进**：新增 tools/osm_moat_water.py、source-water-osm.geojson（19 块真实 OSM water=moat 多边形）、标准库耳切三角化与同源 SHA 验证。水面 230 tris、赛道总 4,274 tris（原 5,344）；17 项 Python 测试、Node 回归、8 个 Chrome SwiftShader WebGL 冒烟场景通过。道路 14m 游戏宽度仍非实测，岸墙/桥梁/水位与真实 GPU 待做。


## 2026-10-31 续轮：M2/M3 四城门定位和原型

- 本轮先核对干净的 git status，HEAD a6aab8d，工作树领先 origin/main 13 个提交；以最新文件为准。
- 原始 OSM XML 已包含四个 historic=city_gate 节点（Tha Phae、Chiang Mai、Suan Dok、Chang Phueak）。新增 tools/osm_city_gates.py 和 source-gates-osm.geojson，保留同一快照 SHA、ODbL、四个 node ID。
- 发现并修复原检查点与四座真实城门错位问题：原四分点并不在历史城门附近；现在用最近赛道中心线点定位，起跑点重新锚定 Tha Phae，运行时碰撞检查点和金色可视拱门同步对齐。
- 新增单网格合并的四座原创程序化城门/短城墙低模，明确不代表真实历史建筑形制；没有修改物理碰撞走廊或将建筑误标为 CC0。
- 新增 5 项 Python 回归：OSM 节点和 SHA、道路/检查点/模型对应、伪造数据拒绝、示意路线隔离；Python 总 22 项、Node 3 套和 Chrome 148 SwiftShader 8 场景通过。
- M2 OSM 默认模型现 6 meshes、4,514 triangles，原 5 meshes、4,274 triangles；真实 GPU 帧率/手动绕圈/道路现场复核仍未完成。下一轮继续修复可验证 Bug、低模街景与真实驾驶/性能验收。


## 2026-10-31 续轮：M3 临街建筑 OSM 低模

- 本轮先核对 HEAD 47ac264、git status 干净、四份交接/引擎/路线图文档，未覆盖先前改动。
- 同一官方 OSM XML SHA-256 63cda4fd16cdc4c20421f68de0055538b2fd104d4c9d3a0a8f5239324b4b8934 含 6,290 条带 building 标签的闭合 way；新增 tools/osm_roadside_buildings.py 只筛选离赛车中心线 80m 内的建筑，排除靠道路中心线 <12m 和历史城门 <27m 的轮廓，每 50m 路段最多 10 栋、总量不超过 900。
- 新增 assets/tracks/chiangmai-moat/source-buildings-osm.geojson（ODbL，815 栋 OSM 轮廓/way IDs）。其中 39 栋高度来自 OSM building:levels，776 栋高度为 6.5–10m 的游戏估算，不能称为实测高度。
- tools/build_moat_blockout.py 将临街立面和屋顶分别合并为 2 个网格（共 8 meshes、15,292 tris），默认路线仍 6,492.2m；保留 --schematic 不导入 OSM 建筑。
- 新增 5 项 Python 单测；27 项 Python、Node 三套回归及 Chrome 148 SwiftShader 8 场景通过。尚无真实 GPU 帧率/现场验证。M3 仍远未完成，后续需优化遮挡、桥梁、建筑外观与标志性地标。
- 保护范围：未改线上 gta.jizhang.org；本地 Git 提交和实际状态以每轮 git log 为准，不能声称已推送 GitHub。

## 2026-10-31 续轮：M2 道路越界修复与路面可读性

- 本轮开始核对 git status/log、WORK_CONTINUITY、ROADMAP、M2-BLOCKOUT、ENGINE，基线 ed903c0（领先远端 16 提交），工作区干净。以本轮实际提交为准。
- 修复发现的实际玩法缺陷：旧 Cityscape 碰撞在 14m OSM 赛道上离开路缘约数米就会调用 fall()，导致小幅越界直接跌落。MoatCollision 新增基于空间索引的 projectInside()，ShipControls.collisionCheck() 仅对 M2 将车体投影回路内、降低速度、取消 boost/nitro，并限制撞击音效/伤害频率。Cityscape 仍走旧碰撞路径。reset() 清除碰撞冷却。
- 新增游戏示意虚线中心标记（不是 OSM 实测道路标线）：离线生成、一个合并网格，增加 650 tris；OSM 默认场景由 8 meshes/15,292 tris 增至 9 meshes/15,942 tris。
- 新增 1 项 Python 标线几何测试与 Node 碰撞边界测试，Chrome 148 SwiftShader 增加真实 ShipControls.collisionCheck 越界回弹场景。28 项 Python、Node 三套回归、Chrome 9/9 WebGL 场景通过。
- 待做：OSM 急弯驾驶手感（当前路线上单点转角最大约 55 度）、连续手动整圈/真实 GPU、桥梁和城墙的历史外观校准、分块可见性优化。不能宣称这些已完成。
- 未部署线上 gta.jizhang.org，未推送 GitHub；每轮先核对实际工作树与最新提交。


## 2026-10-31 续轮：M2 急弯转向参数与无 GPU 浏览器物理回归

- 本轮先核对 git status/log 与 WORK_CONTINUITY、ROADMAP、M2-BLOCKOUT、ENGINE；实际基线为 9c01a55，工作区干净，领先远端 18 提交。
- 通过 route.json 计算确认 OSM 重采样中心线最急顶点转角 55.388°（index 400），紧邻 index 401 另有 33.972°；index 565/566 约 38°。旧版 ShipControls 构造默认 0.005 rad/frame，实际经 HexGL.tweakShipControls 覆盖为普通难度 0.019、困难 0.021；需要针对 14m 清迈赛道进一步校准。
- 仅对 M2 清迈车辆设置 angularSpeed=0.024、airAngularSpeed=0.030；两辆车均应用，Cityscape 普通难度仍保持 0.019。浏览器测试新增实际 ShipControls.update(1) 的手刹+转向 14 帧测量（大于 57° 且不超过约 83°），并检查双人两辆车参数和旧赛道不受影响。
- 这是物理转向能力的自动化回归，不等于已经手动驾驶穿越 55°+34° 连续急弯，也不等于完成整圈、真实 GPU 或实际设备手感验收。
- 下一步：实测急弯穿越成功率、连续整圈、碰撞频率和 GPU 帧率；必要时调低弯道速度或在游戏中加入弯道提示，但不要未经验证大改真实 OSM 路线。

- 浏览器实测追加第 11 个场景：使用测试专用前视控制器连续调用真实 ShipControls.update(1)，从 OSM 路线 index 392 驶过 400/401 急弯至 index >=408，301 帧、3 次路肩回弹、无跌落/损毁；设置最多 12 次回弹回归阈值。该控制器仅在测试脚本中，不是生产 AI，也不等于人工驾驶完整圈。11/11 Chrome SwiftShader WebGL 场景通过，手刹 14 帧转向实测 68.2°。

## 2026-10-31 续轮：真实 OSM 全圈物理测试与回放修复

- 本轮开始先核对 git status/log 和 WORK_CONTINUITY、ROADMAP、M2-BLOCKOUT、ENGINE；实际 HEAD e516290，工作区干净，领先 origin/main 19 个提交。禁止用用户提示中的旧 ffd16d1 覆盖当前成果。
- 发现 bkcore/hexgl/RaceData.js 的实质性 Bug：tick() 原本错误地执行 this.rate++，而非 this.rateState++，导致每帧录制而不是每两次采样一次，造成回放数据不必要膨胀。已修复并加入 Node 回归。
- 发现 applyInterpolated() 在 seek==last 或只有一个记录时仍访问 data[seek+1]，会在回放末尾抛异常；现修复首尾边界、空数据和时间戳相同等情况。import() 增加非法/空回放校验并移除整个录制数组的 console.log。
- tests/racedata-regressions.js 新增回放采样率、单帧、首尾插值、坏数据拒绝等测试。Node 原有三套回归仍通过。
- tests/browser_smoke.py 新增测试专用路径跟随控制器，不瞬移、不手工修改 checkpoint 进度：真实调用 ShipControls.update(1)，让车辆沿 OSM 6,492.2m 外圈依次经过四组检查点；在 Chrome 148 + SwiftShader 上分别验证 1/3/5 圈：10495/31489/52477 帧、9/27/45 次路肩修正、1750/5249/8747 条回放采样，全部正常结算且无跌落/损毁。
- 另增加真实 Three.js r50 回放插值/终点边界 WebGL 验证；完整 headless 浏览器场景现为 13/13。Python 28 项通过。
- 这是无 GPU 的自动化测试专用路线跟随器，不是正式游戏 AI，不等于人工驾驶/双人全圈/真实 GPU 性能验收；急弯仍平均每圈 9 次路肩修正，后续需改善弯道手感和驾驶路线。
- 未推送 GitHub，未触碰 gta.jizhang.org。每轮继续先核对当前实际 HEAD、工作树与文档。


## 2026-10-31 续轮：倒计时加速带修复、氮气与双人物理竞速

- 开始核对实际 git status/log 和 WORK_CONTINUITY、ROADMAP、M2-BLOCKOUT、ENGINE；基线 7b1307c，工作区干净，领先 origin/main 21 个提交。未依据用户消息中陈旧的 ffd16d1 回滚。
- 新增浏览器回归首先复现真实 Bug：M2 车辆处于 inactive（倒计时/赛后）且停在加速带时，20 帧内竟自行移动 10.968m，boost 从 0.15 升至 0.1984、nitro 从 0.5 升至 0.75。根因是 ShipControls.update() 无论 active 状态都调用 boosterCheck() 并应用位移。
- 修复：仅 M2 赛道碰撞适配器存在时，inactive 车辆提前返回，不再位移、消耗或获得氮气/加速；暂停期间渲染主循环停止，恢复后 active 赛车仍可正常运行；Cityscape 原行为不变。
- 新增 Chrome SwiftShader 真实物理氮气测试：触发后获得加速，正确扣除 nitroCost，继续更新不会重复扣费；驶入 OSM 加速带仅首次获得 0.25 nitro，停留不重复领取。
- 新增双人同时 OSM 全圈物理测试：两车均真实调用 ShipControls.update(1) 且分别通过检查点，P2 延迟 240 帧起跑，P1 约 10495 帧完成并触发胜者 0，P2 当时已到路线点 634，随后两车及 Gameplay 均正确停止；测试专用跟随器不是生产 AI。
- 验证：28 项 Python 测试、4 套 Node 回归通过；Chrome 148 headless SwiftShader 增至 16/16 场景通过，包含 5 圈 52477 帧/45 次路肩修正和双人实际物理竞速。
- 仍未验收：人工驾驶、真实 GPU、现场核对路宽/道路交通方向、许可冲突；每圈平均 9 次路肩修正，M2/M3 尚未最终完成。
- 禁止部署无关 gta.jizhang.org；GitHub 连接仍可能只读，提交仅保存在本地。


## 2026-10-31：M1/M2 静态模型输入校验与 WebGL 回归

- 本轮开始已核对实际 git status/log 和四份工程文档；最新基线 242480d（M3 Wat Chedi Luang 地标），工作区干净，领先 origin/main 24 提交。用户消息中的 ffd16d1 为旧状态，不得回滚。
- 复现静态加载器真实缺陷：带 indices:[0,1,9] 的三顶点模型在 THREE.StaticModelLoader.build() 中不报错，而是创建引用不存在顶点的 Face3，可能到 WebGL 上传时才异常；其他负索引、NaN、错长 UV/法线也未提前拒绝。
- bkcore/threejs/StaticModelLoader.js 新增在 r50 Geometry 分配前执行的模型结构与上限校验：材料/网格数量、顶点/索引计数、整数且在范围内的索引、有限坐标、法线/UV/颜色长度。损坏的赛道模型现在可沿已有 onError 路径回退到 Cityscape，而不是把坏三角面交给 GPU。
- tests/regressions.js 新增正常/损坏模型断言，先在未修复代码中观察到真实失败，再修复并复测。
- 测试：Python 33/33、Node 四套回归通过；Chrome 148 + SwiftShader 17/17 WebGL 冒烟通过（包含 10,495 帧的 OSM 一圈真实物理测试、双人、Wat Chedi Luang 地标渲染、默认旧赛道和 404 回退）。
- 当前 M3 已有 Wat Chedi Luang 地标模型（源自 242480d）；本轮未重建该地标，未推送 GitHub，未触碰 gta.jizhang.org。
- 下一轮建议：进一步测试损坏 JSON 的真实浏览器回退、真实 GPU 性能与用户手动驾驶；继续分块可见性优化、桥梁与许可风险处理。

- 追加浏览器回归：用本地测试 HTTP 服务器返回 200 OK 但包含越界 Face3 索引的 road.json，确认在 Three.js 几何上传前拒绝，并完整回退到 Cityscape。Chrome SwiftShader 17/17 场景通过。\n

## 2026-10-31 续轮：M3 临街建筑分块与旧版 r50 视锥剔除

- 开始时已核对 git status/log 与 WORK_CONTINUITY、ROADMAP、M2-BLOCKOUT、ENGINE；本轮基线为 3847958，工作区干净，领先 origin/main 25 提交。不得用用户消息中的 ffd16d1 覆盖。
- 发现实际性能结构缺陷：原 815 栋 OSM 建筑只合并为 2 个覆盖整圈的 mesh，且 Three.js r50dev 的 Geometry.computeBoundingSphere() 使用**局部原点到顶点的最大距离**，即使直接按道路分块、保留全局坐标，也无法得到小包围球，无法有效剔除背后的建筑。
- tools/build_moat_blockout.py 将临街建筑按最近赛道里程分成 19 个约 350m 区段，每段墙体/屋顶各 1 mesh，共 38 个建筑 mesh；每块顶点重新以局部中心为原点，offset 恢复世界位置。StaticModelLoader 支持可选 [x,y,z] offset 并校验非法值；旧车模型和 Cityscape 无 offset 时不受影响。
- 默认 OSM 场景从 13 meshes 变为 49 meshes，三角面仍为 16,172；建筑块最大局部半径约 201.68m。road.json 由 833,457 字节降至 764,789 字节（未压缩 JSON 大小），不代表帧率/加载速度已有实测提升。
- 已补 Python 世界空间几何保持/三角面数/分块局部半径、Node loader offset/非法 offset，以及 Chrome r50 mesh.boundingSphere/frustumCulled 回归。Python 33 项、Node 4 套已通过；浏览器验收结果以本轮最终测试记录为准。
- 性能权衡：可见块的 draw call 数可能高于原 2 个大建筑 mesh；实际收益需真实 GPU 帧率/绘制调用实测。OSM ODbL 来源未变，未修改 gta.jizhang.org，GitHub 未推送。

- **本轮最终浏览器验收**：Chrome 148 + SwiftShader 17/17 WebGL 场景通过；新增断言确认 r50 Geometry.boundingSphere.radius <250m 且建筑块 frustumCulled=true。自动物理 OSM 1 圈 10,495 帧/9 次路肩修正、双人物理竞速、Nitro、原 Cityscape、损坏模型回退均通过。此项仍不等于真实 GPU 或人工手动驾驶验收。


## 2026-10-31 续轮：M3 建筑分块的实际 WebGL 绘制调用验证

- 本轮先核对 Git 工作树干净、HEAD `19c95a4`、四份 WORK_CONTINUITY/ROADMAP/M2-BLOCKOUT/ENGINE 文档；以实际工作树为准。
- 前轮仅验证 38 个建筑网格的包围球半径和 `frustumCulled=true`，未证明 r50 渲染器真的跳过绘制。本轮在 `tests/browser_smoke.py` 新增**真实 WebGLRenderer.render()** 的 A/B 测试：对同一场景、同一镜头，在 OSM 路线索引 80/240/400/560，分别开启和临时关闭 38 个建筑网格的视锥剔除；测试结束后恢复剔除标志和摄像机状态。
- Chrome 148 + SwiftShader，`renderer.info.render.calls` 的关闭→开启结果：`49→35`、`49→33`、`52→38`、`43→15`；`faces` 为 `16172→12686`、`16172→10423`、`35684→31755`、`15558→7501`。**四个取景点均确实减少绘制调用和三角面**，不是只设置了剔除标志。取景点 400 含镜头可见的其他动态对象，绝对 faces 与静态地图三角面数不必相同。
- 完整验证：Python 33/33，Node 四套回归，Chrome headless WebGL **18/18**（新增 1 个真实绘制调用对比）；OSM 自动物理整圈仍为 10495 帧/9 次路肩修正。`git diff --check` 通过。
- 这是**无独立 GPU 的 SwiftShader 静态镜头对比**，证明视锥剔除实际生效，但**不证明真实设备 FPS、帧耗时、首屏或内存改善**。下一轮继续做可重复的加载耗时与真实 GPU 采样，并推进桥梁、人工驾驶、许可审查。未修改线上 `/www/wwwroot/gta.jizhang.org`，未推送远端。

## 2026-10-31 续轮：首次可复现首屏加载与 JS heap 测量

- 开始核对 `git status/log` 与 WORK_CONTINUITY、ROADMAP、M2-BLOCKOUT、ENGINE；实际基线 `cfba312`，工作区干净，领先远端 29 提交；没有用旧版 `ffd16d1` 回滚。
- 新增 `tests/browser_load_profile.py`：本地静态 HTTP 服务、Chrome 148 headless SwiftShader、禁用 HTTP 缓存、每次独立浏览器进程，真实进入游戏就绪屏。最初复用 Chrome 时 JS heap 逐次累积，识别并修正了**测试测量污染**，没有将其当作游戏内存泄漏。
- 清迈 OSM 低画质 3 次中位数：4,493.4ms 就绪、67 资源、6,748,981 B 传输、48,429,425 B JS heap；Cityscape：5,361.4ms、79 资源、7,393,065 B、78,740,616 B。逐次数据见 `docs/PERF-BASELINE-2026-10-31.json`；无网络 RTT/真实 GPU，不能推出设备 FPS、显存或实际用户首屏速度。
- 下轮优先真实 GPU/人工驾驶验证；继续 OSM 桥梁/岸墙与 CC BY-NC 许可审查。无线上部署、无远端推送，保留本地小型提交。

## 2026-10-31 续轮：M3 桥梁 OSM 候选盘点（不冒充建模完成）

- 在本轮首屏性能提交 `0be58a9` 之后继续分析服务器保留的 OSM XML（SHA-256 与 source-water-osm.geojson 一致）；发现周边有多个 `bridge=yes` 的 OSM way，但部分距已绘制水体较远，不能把所有桥标签直接当护城河桥梁。
- 新增 `tools/osm_bridge_inventory.py`，按真实节点坐标、路段中点与 19 块水体最短距离 ≤12m 选出 **13 条候选**，保留 way ID/highway/ODbL/原始坐标/快照 SHA 于 `source-bridges-osm.geojson`。该数据**尚未接入模型或碰撞**，不宣称真实桥宽/跨水拓扑已核验。
- 新增 `tests/test_osm_bridges.py` 的 3 项回归（真实候选文件、点到多边形距离、合成桥梁过滤与混用快照拒绝），Python 总计 **36/36 通过**；此前本轮完整 Node 四套及 Chrome SwiftShader 18/18 已通过，桥梁清单不影响游戏资产。
- 下一步：逐个核对候选桥梁与水面关系，按已核验路段生成低模桥面和栏杆；仍需真实 GPU、手动驾驶及原 HexGL 许可核查。未部署线上 gta.jizhang.org、未推送远端。

## 2026-10-31 续轮：桥梁候选跨水拓扑分类（未建模）

- 已核对 git status/log 和四份必读文档：起始 HEAD 033391e，工作区干净、领先远端 31 提交；未覆盖旧改动。
- 原先 13 条 bridge=yes 候选仅依据距水体 12m 内筛选，不能区分岸边道路与跨水道路。本轮增加线段/水体边界交点裁剪、并集内长度与穿越次数测量，岸边共线和切点不计。
- 相同 OSM 快照中，7 条 footway 几何上穿过已映射水体且两端在水体外，标记 geometric_water_crossing_candidate；另 6 条近水但无水面重叠，标记 nearby_unconfirmed。仅是地图几何证据，不代表真实桥宽/高程、车辆通行或现场确认。
- GeoJSON 增加交集长度、边界穿越次数、分类，保留 13 条来源和 ODbL。新增切线、共边、分段、相邻水面并集回归；Python 38/38、Node 五套通过。无 3D 模型、无碰撞修改、无线上部署或远端推送。
- 完整验证：Chrome 148 SwiftShader WebGL 18/18 场景通过；Python 38/38、Node 五套回归通过；使用原始 OSM XML 重新生成桥梁 GeoJSON 与提交文件字节完全一致（cmp 通过）；git diff --check 通过。游戏运行时资源未变。
- 下一步：现场/地图核对桥梁真实性及通行属性，优先寻找可驾驶车桥，再制作程序化低模；真实 GPU、人工驾驶和 HexGL 许可仍未验收。

### 2026-10-31 M3 桥梁距离算法修复

- 修复桥梁候选提取的**漏检风险**：此前只检查 OSM 道路节点和相邻节点中点到水体的距离；很长的线段可能从窄水面穿过，而三个采样点均远离水面，导致漏掉真实候选。现在计算完整道路每条线段到水体多边形边界的最小距离，并处理相交/线段在水内情况。
- 新增合成 200m 长线段穿越 2m 水面的回归，旧采样法会漏检；实际 2026-10-31 OSM 快照重算后仍是 **13 条近水候选、7 条 footway 几何跨水、6 条仅近水**，其中 3 条非跨水道路距离从 8.58→8.56m、5.33→5.30m、11.00→10.87m；way IDs 不变。
- 本改动仅修复**离线数据提取准确性**，没有添加车桥模型或改变赛道碰撞。仍未确认任何可驾驶护城河桥，禁止把 footway 候选直接作为车桥。

## 2026-10-31 续轮：模型请求超时回退与浏览器计时稳健性

- 本轮以 `cacd20e` 干净工作树为起点，先核对 git status/log 与四份工程文档。
- `StaticModelLoader.load` 过去没有 XHR timeout/onerror/onabort，网络连接长期不响应时可能永远停在加载界面。现在为模型请求设置 30s 超时，网络错误/取消/同步 send 异常均走已有 `onError`，用 one-shot 状态防止 readyState 和 error 事件重复触发赛道回退；HTTP 404、无效 JSON、模型几何校验和 file:// status=0 兼容分支保留。
- Node 新增失败事件/超时/HTTP/send 回归；原有 404/损坏模型 Cityscape 回退场景仍应保持。
- Chrome SwiftShader 旋转合成赛道的驾驶断言从固定等待 2 秒改为等待**实际沿切线移动超过 2 米**，避免软件渲染忙碌时帧数不足造成误报；并未改变生产驾驶物理。
- 仍需真实 GPU、人工驾驶、可驾驶护城河桥梁核验和 HexGL CC BY-NC 许可处理；不能宣称完成 M3 或推送 GitHub。

## 2026-10-31 续轮：M3 护城河岸线视觉原型

- 从实际 HEAD `b773c2f` 的干净工作树开始，核对 git log/status 与 WORK_CONTINUITY、ROADMAP、M2-BLOCKOUT、ENGINE；未使用旧 ffd16d1 快照。
- `tools/build_moat_blockout.py` 新增 `water_bank_meshes`：沿已有 19 块 OSM 水体多边形边缘生成 19 个独立低模岸墙块，每块顶点局部重定位并通过 r50 StaticModelLoader `offset` 恢复坐标，避免整个 6.5km 河岸共用一个巨大剔除包围球。增加 536 个三角面；默认 OSM 赛道由 49 meshes/16,172 tris 变为 68 meshes/16,708 tris。
- 岸墙高度 -0.45 至 +0.18m、石色均为原创视觉估算，**OSM 仅提供水岸平面轮廓，不包含实测高程/墙体材料**。此层不进入物理碰撞，不制造可驾驶桥梁；`--schematic` 不包含 OSM 岸墙。
- 新增几何/局部偏移测试并更新依赖网格数的既有测试，浏览器检查岸墙数量。仍需真实 GPU 帧率、人工驾驶及岸墙/桥梁现场核验，尤其不能将水面多边形端部误认为真实挡墙。

- 本轮实际验证：Python 41/41、Node 四套、Chrome 148 SwiftShader WebGL 18/18；OSM 一圈物理驾驶仍为 10495 帧/9 次路肩修正。新版场景四点建筑剔除 draw calls 为 59→45、60→44、64→50、46→18（关→开建筑剔除）。与旧场景不能直接当作同配置 GPU 性能比较。重复生成 road.json SHA-256 为 b2fb912441ac104ed8a070e6a3635ad33383cc7a18bbae5d07ea3b2abdef389b。

## 2026-10-31 续轮：岸墙误封闭水面端部修复

- 本轮从干净的 `9958f8e` 开始，核对 `git status/log` 和四份工程文档。发现上轮 `water_bank_meshes` 无条件沿 OSM 水体多边形所有边造墙，导致部分被桥/道路分割的水面端部出现**横跨护城河的虚构挡墙**。
- 新增 `is_water_polygon_end_cap`：仅对 8–28m 的短边，且两端相邻边均长于该边 3 倍、接近正交的明显长条形闭合端部，跳过视觉岸墙。19 块水体共识别 12 条明确端部，去除 24 个三角面；保留其他模糊/圆弧边界，避免过度推断。此规则只改变原创视觉岸墙，不修改 OSM 水体、路线、车辆碰撞或桥梁通行。
- 新增正反方向长条水体与方形边界测试；仍需现场核实模糊端部及桥梁结构，不能将几何启发式视为真实岸墙测绘。
- 本轮实际回归：Python 42/42，Node 四套，Chrome 148 SwiftShader WebGL 18/18；单人完整物理圈 10,495 帧/9 次路肩修正。最新场景 68 meshes / 16,684 tris，其中岸墙 512 tris；未测真实 GPU、人工驾驶，未修改线上其他游戏。

## 2026-10-31 续轮：M3 岸墙端部误判回归

- 本轮先核对实际 `git status/log` 和四份工程文档，起始 HEAD `b1ce409`，工作区干净，领先远端 39 提交；未覆盖其它轮次工作。
- **先复现真实算法误判**：`is_water_polygon_end_cap` 仅检查短边与两条长边近似正交，未验证两条长边是否反向。合成的 L 形阶梯岸线中，两条长边同向延伸，20m 连接边被错误视为跨水人工端部，视觉墙被删掉（12 tris 应有却只剩 10 tris）。
- 修复为要求相邻长边方向点积 `< -0.9 * length_product`，只将反向、近似平行的双岸闭合边视为端部；同向的阶梯/凹角岸线不再错误断开。新增正反环方向回归。
- 同一 OSM 快照重建默认地图仍为 68 meshes / 16,684 tris，保留原 12 条可信端部排除；不改变道路、OSM 数据、水面、物理碰撞或赛车参数。该规则仍为视觉启发式，未现场核验。
- Python 全套 42/42、Node 四套回归、Chrome 148 SwiftShader WebGL 18/18 通过；OSM 自动物理一圈 10,495 帧/9 次路肩修正。真实 GPU、人工驾驶、车桥核验、HexGL 非商业许可问题仍未完成。未触碰线上 gta.jizhang.org。

## 2026-10-31：桥梁清单识别水体断口附近的机动车道路（待核验）

- 以实际 HEAD `fff6a9f`、干净工作树和四份工程文档为起点。原有桥梁清单仅把 7 条与水体重叠的 footway 识别为跨水候选，忽略了 OSM 水体多边形可能在桥口断开：`bridge=yes` 机动车道路不一定与水面多边形直接相交。
- `tools/osm_bridge_inventory.py` 复用已测试的保守岸墙端部几何识别，计算 13 条候选道路至水体端部中点的整条线段最短距离；对 16m 内且没有水面重叠的机动车 `bridge=yes` 道路标记 `mapped_water_gap_motor_bridge_candidate`，仅用于**人工核查优先级**，不是已确认汽车桥，也不据此添加 3D 模型或碰撞。
- 同一 OSM 快照中 4 条 `secondary_link` 候选：26765842（9.01m）、696726366（5.35m）、698115427（14.80m）、698115429（11.10m）。原 7 条 footway 几何跨水候选不变，另 2 条仍为仅近水。保留 ODbL、OSM way ID、快照 SHA；新的端部距离和分类已写入 `source-bridges-osm.geojson`。
- 这解决的是**候选筛选盲点**，不是实地验证；端部阈值是保守的游戏数据审阅启发式。下一步核对这四条道路的桥面/方向、连接拓扑及是否跨越实际水面，再考虑原创低模。仍需真实 GPU/人工驾驶/HexGL 许可审查。

## 2026-11-01：M3 机动车桥候选道路连接与并行分组

- 本轮先核对实际干净工作树与 HEAD `7be2d67`，阅读 WORK_CONTINUITY、ROADMAP、M2-BLOCKOUT、ENGINE；保留本地领先远端的 42 个提交，没有回退到旧提示中的 `ffd16d1`。
- 复核同一 2026-10-31 官方 OSM XML 快照：4 条 `bridge=yes / highway=secondary_link` 候选全部带 `oneway=yes`、`lanes=1`、`surface=asphalt`；每条两端 OSM 节点均与其他机动车道路 way 共享（不是仅几何靠近）。新增共享节点连接证据和邻接 way IDs，供后续检查道路拓扑/方向。
- 4 条机动车候选实际上形成 **2 组相距较近且方向平行的道路审阅位置**：`26765842 + 696726366` 和 `698115427 + 698115429`。这是空间聚类，不等于确认两座实体桥，也不代表已核验机动车合法通行或与赛车路线连通。
- `source-bridges-osm.geojson` 新增 OSM 原始方向/车道/路面标签、两端道路节点邻接、`motor_bridge_review_site` 和聚类算法/阈值说明；保留原 13 条候选、7 条跨水步行道路和 ODbL 来源。没有生成桥梁 3D，也没有修改碰撞/物理/线上网站。
- 新增并行反向道路、垂直交叉道路、远距离道路和共享节点测试。后续优先检查两组候选与实际赛道的交通方向和空间交叉，再考虑程序化模型；人工驾驶、真实 GPU 与 HexGL 许可仍待解决。
- 验证：Python **45/45**、Node **4 套**、Chrome 148 SwiftShader WebGL **18/18**，原始 XML 重新生成桥梁 GeoJSON 与提交文件字节一致，`git diff --check` 通过；自动物理驾驶一圈仍 10,495 帧/9 次路肩修正。浏览器结果为软件渲染，非真实 GPU。

## 2026-11-01：M3 机动车桥与赛车路线几何关系核验（仅离线审计）

- 本轮先核对实际干净 Git 工作树 117a907、最新提交及四份工程文档；没有使用旧 ffd16d1 覆盖。
- osm_bridge_inventory.py 新增与同一 OSM 快照的 source-osm.geojson 闭合赛车中心线逐线段距离、交点去重、最近路线段索引及绝对方向点积。输入来源 SHA 不匹配或路线未闭合时拒绝生成；新增合成相交、平行近距、共享路线顶点去重和来源不一致测试。
- 四条 secondary_link 机动车桥候选距赛车中心线分别 8.10m、7.22m、11.04m、9.18m，交点均为 0，方向绝对点积 0.032、0.014、0.052、0.048（近似垂直）。这只能证明地图几何上的接近，不能证明与赛车道路拓扑连通、可合法驾车通过或确认真实桥梁；禁止因此将桥面接入赛道。
- 路线几何交点按坐标去重，避免路线共享顶点被计为两个交点；同一快照候选仍为 13 条/2 个机动车审阅位置。source-bridges-osm.geojson 已重建，未改变运行时地图、赛车碰撞或实体桥梁。
- 待办：依据原始 OSM 共享节点/单向路网进一步核对桥头与环线的真实连接，再结合现场/影像审查决定是否建模；真实 GPU、人工驾驶和 HexGL CC BY-NC 许可问题仍待验收。

## 2026-11-01：M3 桥梁单向路网可达性审计

- 本轮先核对 `git status/log`、WORK_CONTINUITY、ROADMAP、M2-BLOCKOUT、ENGINE；基线 `9ba14a9`，工作树干净，未回退旧快照。
- `osm_bridge_inventory.py` 从同一 OSM XML 中按道路共享节点构建有向机动车路网，考虑 `oneway=yes/-1` 及 roundabout 的隐式单向，分别以已入库外圈路线 90 个 OSM way 的节点为起点，计算路线→桥入口、桥出口→路线的最短**图边数**。不把几何接近误当作道路连接，也不把图可达误当作合法通行。
- 四条 `secondary_link` 单向桥候选的（路线到入口 / 出口回路线）最少节点边数分别为：26765842 **2/20**、696726366 **29/2**、698115427 **3/29**、698115429 **19/3**。说明这四条道路在当前 OSM 标签约束下存在有向路网路径，但绕行不对称，不能直接把桥接到游戏赛道；尚未核查转弯限制、车道接续、机动车通行权限和现场桥梁结构。
- 输出增加两个 directed hop 字段和方法免责声明；新增合成 `oneway=yes/-1`、roundabout、非机动车路段和缺失来源 way 测试。候选仍为 13 条、两组机动车审阅位置；没有修改游戏模型、物理碰撞或线上站点。
- Python 48/48、Node 四套通过，原始 XML 重建 GeoJSON 与入库数据 `cmp` 一致。Chrome 148 SwiftShader 首次以默认超时运行在第 16 个（404 回退）场景等待超时；使用 `--timeout 60 --physical-laps 1` 重新完整执行后 **18/18** 通过，含 10,495 帧物理全圈、9 次路肩修正。初次超时原因未确认，不能声称浏览器测试零波动。真实 GPU、人工驾驶、现场核验与旧 HexGL 许可冲突仍未解决。


## 2026-11-01：M3 机动车桥梁通行标签与转弯限制审阅（不改变赛道）

- 基线为 b3b7e35，工作树干净；按本轮实际 Git 状态与同源 OSM XML 继续开发。
- osm_bridge_inventory.py 新增机动车通行标签的保守优先级审阅：motorcar > motor_vehicle > vehicle > access。对 private/no/permit 等限制、destination/customers 等有限通行及未知取值，从离线有向路网 BFS 排除；更具体的机动车标签可覆盖一般 access。没有显式限制的道路仍仅标为 untagged，不代表合法通车。非机动车 highway 标记 not_motor_road。
- 新增 type=restriction 关系审阅：统计原始 OSM XML 的限制关系，按桥梁 way 成员或 via 节点记录附近关系 ID。未实现转向限制约束的 BFS，条件限制与 via way 也仍待进一步核查；没有相邻限制关系不代表实际通行合法。
- 同源快照的 1035 条 MOTOR_ROADS way 中，933 条无机动车通行标签、53 条明确限制、34 条仅有限通行、15 条显式允许；路网 BFS 排除 87 条限制/有限通行 way（本快照没有未知值）。现有快照有 13 个 restriction relations，四条机动车桥候选未直接命中桥 way/via 节点；四条均无明确机动车 access 标签，之前的最短节点边数 2/20、29/2、3/29、19/3 不变。这是候选审阅，不是实体桥梁或实际驾驶权证明。
- 只更新离线桥梁 GeoJSON、Python 测试和文档，不修改 Three.js r50dev、M2 14m 游戏路宽、碰撞、车辆物理、路网或渲染。下一步应实现考虑转弯限制的状态图与现场桥梁核验；真实 GPU/手动驾驶和 HexGL 许可问题仍待解决。


### 2026-11-01 本轮验证记录

- Python 单测 50/50；Node 四套回归通过；同源桥梁 GeoJSON 两次生成 SHA-256 均为 5f22da4fd5a316e646320967bfd4d41d67ded619dd772076becc2f9df9e75bf0。
- Chrome 148 headless SwiftShader 首次使用每场景 60 秒上限：前 16 场通过，第 17 场损坏模型回退等待超时（根因未定位）。以 90 秒上限完整重跑 18/18 通过，实际整轮耗时 37.51 秒。不能把首次超时称为已修复，也不能把软件渲染当作真实 GPU 测试。
- 游戏运行时与原有驾驶物理未修改，未部署无关线上站点，未推送 GitHub。后续应为浏览器偶发加载超时增加可诊断的资源/步骤日志，并继续真实 GPU 与人工驾驶验收。

## 2026-11-01：M3 桥梁有向路网加入 via-node 转弯限制

- 本轮先核对干净 Git 状态、HEAD 4286fb0 和 WORK_CONTINUITY / ROADMAP / M2-BLOCKOUT / ENGINE，未使用旧快照。
- `osm_bridge_inventory.py` 将有向 BFS 从单节点状态升级为（节点、进入道路 way）状态；逆向搜索记录离开道路 way。支持 OSM 无条件、单 via-node 的 `no_*` 与 `only_*` 转弯限制，避免从错误的 incoming way 误禁转向；不把沿同一 way 继续行驶当作转弯。
- 同源 OSM 快照共有 13 个 restriction 关系：7 个无条件 via-node 规则纳入搜索；4 个条件限制和 2 个 via-way 规则未执行，已将未处理关系 ID 明确写入 GeoJSON。其他未识别/机动车豁免规则也会列为未处理，不能据此证明合法驾驶。
- 四条机动车桥候选的最短（路线→桥入口 / 桥出口→路线）仍为 2/20、29/2、3/29、19/3 节点边数；不代表实地桥梁、交通许可或游戏内可行驶连接。起点/终点是 OSM 赛车路线 way 的任意节点，未约束起止方向和车道连接。
- 新增正反向 BFS、`no_*` / `only_*` 和未支持关系回归；Python 52/52、Node 四套、Chrome 148 SwiftShader 18/18 通过（1 圈物理驾驶 10,495 帧/9 次路肩修正）。软件渲染非真实 GPU。
- 仅修改离线审计工具、测试、桥梁候选 GeoJSON 与文档；未修改赛车物理、渲染、线上 gta.jizhang.org，也未推送 GitHub。下一步核验条件限制、via-way 规则、真实桥梁与手动驾驶/真实 GPU。


## 2026-11-01：M3 单段 via-way 转弯限制执行

- 本轮从干净工作树与 HEAD `068bdad` 开始，先核对 git status/log 和 WORK_CONTINUITY、ROADMAP、M2-BLOCKOUT、ENGINE。没有使用提示中旧 `ffd16d1` 覆盖新提交。
- 修复桥梁有向路网 BFS 只执行 via-node 限制的遗漏：新增 `via_way_turn_rules`，对**单条 via-way、from/via/to 各一条 way、唯一且不同的进入/离开共享节点**执行无条件 `no_*` / `only_*` 转弯限制；多段 via-way、拓扑歧义、条件限制或机动车豁免仍不自动执行，并明确列入未处理 ID。
- BFS 在进入 via way 时激活关系，跨其内部多段保留状态，在指定出口节点判定禁止或强制转向；逆向搜索采用对称的进入/离开关系，避免单节点 BFS 误认为所有进出道路相同。新增禁止/强制、反向、替代入口、拓扑歧义及条件限制测试。
- 同一 OSM 快照 13 条限制关系现有 **9 条已执行**（7 via-node + 2 via-way）、**4 条条件限制仍未执行**。四条机动车桥候选的路线→桥入口/桥出口→路线最少图边数仍为 2/20、29/2、3/29、19/3；这不代表桥梁已经可合法通车，起终点方向、时间条件、车道/转弯细节及现场仍待核验。
- 验证：Python **53/53**，Node 四套，Chrome 148 SwiftShader **18/18**（单人完整物理一圈 10,495 帧、9 次路肩修正），桥梁 GeoJSON 重复生成 `cmp` 一致，`git diff --check` 通过。没有修改游戏运行时或无关线上 `/www/wwwroot/gta.jizhang.org`，没有推送 GitHub。
- 下一步：优先补条件转弯限制的时间窗审计（不要在未指定时间时假装合法）；核验桥梁跨水位置/车道接续、真实 GPU 和人工驾驶；处理原 HexGL 非商业许可冲突。


## 2026-11-01 M3 条件转弯限制的指定时刻审计

- 从实际干净 HEAD `4bf31fe` 及四份工程文档继续；`tools/osm_bridge_inventory.py` 新增可选 `--audit-time HH:MM`，仅在明确给出**清迈当地时间**时解析纯每日时段（含逗号分隔、跨午夜），采用起点包含/终点不包含。工作日、节假日、例外车辆、复合条件或无效语法不做猜测，继续列为未处理。
- 默认**不提供时间**时仍保守保留 4 条条件限制未处理，不伪称全天可通行；给定 08:00 时同源 OSM 快照 13/13 条转弯限制纳入搜索（原 9 + 条件 4）；12:00 时 9 条生效、4 条被明确判定为时段外。审计样本在 `docs/M3-TIME-TURN-AUDIT-2026-11-01.json`，保留 ODbL 来源与 SHA。
- 四条机动车桥候选的最短节点边数在 08:00 与 12:00 都是 2/20、29/2、3/29、19/3；这只是**从任意路线节点开始/结束**的有向图统计，未考虑实际比赛行车方向、路口车道接续、实时交通规则或桥梁现场情况。
- 新增纯时段解析、早/午/晚边界、跨午夜、无效语法和有向搜索测试；只影响离线候选审计，**不修改游戏 Three.js r50dev、赛车物理或碰撞**。仍待真实 GPU、人工完整驾驶、桥梁现场核验及 HexGL CC BY-NC 许可冲突处理。

## 2026-11-01：M3 条件单行道方向审计修复

- 从实际干净 HEAD `ae36d7d`、四份文档与 2026-10-31 同源 OSM XML 继续，未回退旧快照。发现原有机动车有向图忽略 `oneway:conditional`，将其按全天双向道路纳入 BFS，可能虚增桥梁候选可达性。
- 该快照实际有 **3 条** `residential` 道路含 `oneway:conditional=yes @ (06:00-09:00,15:00-18:00)`：OSM way IDs 19977738、695727399、695727400。无指定时刻时保守排除这些路段；指定 `--audit-time HH:MM` 后解析简单每日时段，08:00 按单向、12:00 按基本标签双向。无法解析的时间/方向标签不再静默当作双向；补齐 motorway / circular 的隐式单向默认。
- 新增条件单行道、跨午夜、未支持语法、未知方向、显式覆盖的合成回归；Python 56/56、Node 四套、Chrome 148 SwiftShader 18/18 场景通过。桥梁清单 13 条、四条机动车候选的有向边数 2/20、29/2、3/29、19/3 在默认/08:00/12:00 三种审计下均未变化。
- 更新 `source-bridges-osm.geojson` 的方向审计方法及未判定 way ID，更新 `docs/M3-TIME-TURN-AUDIT-2026-11-01.json`；不改 Three.js、物理、碰撞或线上网站。真实 GPU、手动驾驶、现场桥梁/交通核验、HexGL CC BY-NC 许可仍待处理。

## 2026-11-01：M3 via-way only_* 逆向搜索纠错

- 本轮先核对实际干净工作树、HEAD ef41923、git log 及 WORK_CONTINUITY / ROADMAP / M2-BLOCKOUT / ENGINE，保留全部本地提交。
- 复现并修复离线桥梁有向路网的逆向 via-way only_* 转弯限制误用：原实现把 from → via → only to 简单反转成 to → via → only from，既可能错误排除从其他合法入口接入 to 的道路，也可能漏禁 from → via → 非允许出口 的路径。新实现只在逆向路径的出口道路不是允许的 to 时，在经过 via-way 返回指定 from 时阻止该路径；no_* 规则保持原行为。
- 新增合成路网回归：合法 from/其他入口 → via → 指定 to 可达，非法 from → via → 非指定 to 不可达但其他入口仍可达；若赛车路线直接在 via-way 出口节点终止、没有后续 to way，也不得错误触发 only_*。修复范围仅限离线审计工具与测试，不更改 Three.js r50dev、M2 路宽/碰撞、车辆物理或线上网站。
- 当前 OSM 快照的两条 via-way 限制均为 no_*（关系 10134018、10134075），所以此修复主要防止未来数据或其他路网出现假阳性/假阴性；不能据此声称两组桥梁已实地核验、可合法通车或已建模。真实 GPU、人工驾驶、现场道路和 HexGL CC BY-NC 许可风险仍待处理。

### 2026-11-01 浏览器加载超时诊断增强

本轮首次 Chrome 148 SwiftShader 完整冒烟前 17 个场景通过，最后的 45° 合成赛道加载在 90 秒等待上限内没有进入 step-4；该超时未证明是游戏逻辑错误，原因尚未确定。tests/browser_smoke.py 的 boot() 现会在等待超时时收集 readyState、step-4 显示状态、当前赛道、资源条数、页面 URL 与最近的浏览器 SEVERE 日志，避免仅得到空白 Selenium TimeoutException。仍须继续排查偶发资源/渲染压力，不能将增补诊断称为已修复超时。

### 2026-11-01：浏览器冒烟隔离与最终验证

- 首次完整 Chrome 148 SwiftShader 测试在第 18 个 45° 合成路线加载时超时；第二次在第 14 个极高画质加载时超时。第二次诊断显示页面 readyState=complete、step-4=none、resourceCount=41、没有 SEVERE 浏览器日志；这仍不能证明超时根因。
- 为减少连续 WebGL 物理测试对后续质量/回退测试的资源干扰，tests/browser_smoke.py 在双人物理全圈之后和合成旋转路线之前重新启动独立 Chrome 进程，同时保留等待超时诊断。修改后完整 18 场景连续执行两轮均通过（分别 47.34s、44.21s）；**属于测试进程隔离缓解措施，不能声称已找到或修复游戏生产环境的加载超时根因**。
- 最终 Python 57/57，Node 四套回归通过，默认桥梁 GeoJSON 与原始 OSM 同源快照重算字节一致；08:00/12:00 桥梁候选图边数不变。单人 OSM 物理圈仍 10,495 帧/9 次路肩修正；Chrome 使用 SwiftShader，未测真实 GPU 或人工完整驾驶。

## 2026-11-01：M3 via-node only_* 同一道路直行绕过修复

- 本轮从实际干净 HEAD `847e4d3` 开始，先核对 `git status/log` 与 WORK_CONTINUITY、ROADMAP、M2-BLOCKOUT、ENGINE，保留此前所有本地提交；只修改隔离工作树。
- 复现真实离线路网审计缺陷：当 OSM `from` 道路未在 via-node 拆分时，旧 `allowed()` 把 `incoming_way == outgoing_way` 一律视为合法，导致 `only_right_turn` 等强制转弯限制可被“沿同一 way 直行”绕过；逆向路网搜索也会误判可达。合成路网在修复前错误地把 `straight`、`p` 标为可达。
- 修复为：**同一道路继续行驶仍须满足 `only_*` 的目标 way**；`no_*` 对其他目标道路的禁止不误伤正常直行。仍不声称支持 `no_u_turn` 的同一道路 U 型折返（需前一节点状态）；不推断未知转弯限制或实际交通许可。
- 新增 Python 正向/逆向、仅允许指定转向、普通 `no_*` 直行不误禁、同 way 目标允许等回归。默认同源 OSM 桥梁 GeoJSON 重算与入库文件字节一致；四条机动车桥候选统计不变，仍非现场验证的汽车桥。
- 本轮验证：Python **58/58**，Node 四套回归，Chrome 148 headless SwiftShader **18/18**，单人物理全圈 10,495 帧、9 次路肩修正；`git diff --check` 通过。Chrome 是软件渲染，不能代表真实 GPU 或人工驾驶。
- 本轮不修改 Three.js r50dev、赛车物理、道路碰撞或 `/www/wwwroot/gta.jizhang.org`；真实 GPU、人工驾驶、现场桥口及 HexGL CC BY-NC 许可风险仍待解决。

## 2026-11-01：M3 同一 OSM way 的 no_u_turn 约束

- 从实际干净 HEAD `54b3bcb` 和四份工程文档继续，不使用旧 `ffd16d1` 覆盖新工作。此前 `turn_restriction_rules()` 明确不支持 from/to 同一 way 的 `no_u_turn`，且 BFS 只记录节点与 way，无法判断是否在 via 节点原路掉头。
- 增加上一节点作为正反向路网搜索状态：当同一 way 的 `no_u_turn` 命中 via-node，且下一节点等于上一节点时禁止折返；正常沿 way 直行及其他合法转向不受影响。`only_*` 的原有同 way 直行约束继续生效。
- 新增合成路网回归：必须通过死胡同 U 型掉头才能绕过另一个 `only_right_turn` 的路径，在添加 `no_u_turn` 后正反向均不可达；正常直行仍可达。原始 OSM 快照已有 `no_u_turn` 关系 `10042479`，但 from/to 是**不同** way，故本次补齐的是未来/其他数据的同 way 边界。
- 本轮 Python **59/59**、Node 四套回归脚本、Chrome 148 SwiftShader **18/18**（单人完整物理圈 10,495 帧、9 次路肩修正）通过；默认及 08:00/12:00 桥梁候选边数未变。生成器重新输出仍为 13 条桥梁候选，模型与游戏物理未改；真实 GPU、人工驾驶、桥梁现场核验及原 HexGL CC BY-NC 许可冲突仍待处理。
- 仅在隔离工作目录修改离线审计工具、回归测试、审计元数据和工程文档；严禁触碰 `/www/wwwroot/gta.jizhang.org`。GitHub 推送仍未获证实可用。

## 2026-11-01：M3 via-node 转弯关系共享节点校验

- 从干净 HEAD `827f84d` 及 git status/log、WORK_CONTINUITY / ROADMAP / M2-BLOCKOUT / ENGINE 开始，不回退任何本地提交。发现并复现离线路网真实假阴性：OSM `only_*` 关系即使 `to` way 根本不含 via-node，原搜索仍在 `from` way 的 via-node 禁止合法直行（合成路网：原本 2 hops，错误变成不可达）。
- `turn_restriction_rules(..., ways=...)` 在应用 via-node 关系前核对 via 节点同时属于 from/to OSM way；拓扑不成立时列为 unhandled，而不是执行虚假转向限制。实际路网正向/逆向搜索及 GeoJSON 审计统计均传入同一 OSM way 集合；旧无 ways 调用保持向后兼容。增加正向、逆向虚假关系和合法共享节点的回归。
- 2026-10-31 原始 OSM 快照的 11 条 via-node 关系均共享真实节点；默认桥梁 GeoJSON 重生成与入库文件字节一致，08:00 为 13 条生效/0 未处理，12:00 为 9 条生效/0 未处理，四条机动车候选最短路网边数不变。
- Python 60/60、Node 四套、Chrome 148 SwiftShader 18/18（物理一圈 10,495 帧、9 次路肩修正）通过；无实体 GPU、人工驾驶、现场桥口核验。只改离线审计工具/测试/文档，不改 r50 游戏物理、M2 道路或 `/www/wwwroot/gta.jizhang.org`；HexGL CC BY-NC 风险仍未解决。

## 2026-11-01：M3 可视化急弯预警牌（原创游戏资产）

- 本轮从干净 HEAD `d1ac42d`、git status/log 和四份必读文档继续；未修改原始 OSM 路线、物理碰撞、Three.js r50dev 或线上 gta.jizhang.org。
- 针对真实 OSM 路线的两组相邻急弯（点 400/401：55.39°/33.97°，565/566：38.13°/38.30°），新增离线 `sharp_turn_candidates`，按路径累计弧长合并 45m 内重复警告，选择每组最急点。
- `sharp_turn_warning_meshes` 在每组急弯前约 30m、距道路中心线 10.4m 处绘制原创琥珀色低模预警牌与深色右转箭头；两组牌分别合并为两个 r50 静态 mesh，不增加运行时逐帧逻辑或碰撞体。这是游戏导航提示，**不是 OSM 实测泰国道路标牌或交通规则**。
- OSM 默认路面模型由 68 meshes / 16,684 tris / 13 materials 变为 70 meshes / 16,738 tris / 15 materials（+2 meshes、+54 tris）。示意路线无急弯牌，旧 Cityscape 不变。
- Python 新增几何、急弯聚类与车道外定位测试；调整旧模型材料/三角形数的预期，防止将合理的视觉新增误判为回归。真实 GPU、人工驾驶、桥梁现场核验和原 HexGL CC BY-NC 许可冲突仍未解决。
- 本轮验证：Python **61/61**；Node **4 套**；Chrome 148 headless SwiftShader **18/18**（新增实际 r50 游戏场景包含预警牌的断言）；默认 road/route/route-data 三份文件在临时目录重生成后逐字节一致；`git diff --check` 通过。单人物理完整一圈仍 10,495 帧、9 次路肩修正，**视觉提示不等于已改善驾驶物理**。

## 2026-11-01：M3 急弯预警牌水体穿插修复

- 从实际干净 HEAD `26bf8a7`、`git status/log` 和四份必读文档开始；不使用旧 `ffd16d1` 覆盖本地新提交。
- 复现真实场景问题：OSM 急弯预警牌原先固定放在转弯侧 10.4m；第 572 路线点附近的第二组牌柱位于同源 OSM 护城河水面多边形 **内部约 0.99m**，尽管它不在赛道碰撞走廊内。
- `polygon_clearance` 计算多边形内外与边界的有符号距离，离线建模时对水体和 815 栋已导入建筑逐一检查；保留优选转弯侧，若净距不足 1.6m 则尝试另一侧；两侧均不安全则跳过该牌，不生成空的 r50 mesh。1.6m 是 2.6m 牌宽半径 1.3m 加 0.3m 游戏安全边距，**不是实测道路设施规范**。
- 当前默认 OSM 赛道两组牌仍保留；第二组移至道路另一侧，距 OSM 水面边界约 **19.81m**、最近已建模建筑边界约 **8.00m**，路中心线最近约 **10.40m**。第一组牌保留原位，水面边界约 1.99m。箭头仍按弯道转向，不因牌位换侧而翻转。
- 两组牌仍为 2 meshes / 54 tris；整场景 70 meshes / 16,738 tris。道路中心线、14m 碰撞走廊、物理、检查点、Three.js r50dev、真实 OSM 源文件和线上 gta.jizhang.org 均未修改。新增真实 OSM 水体/建筑净距、路面净距、两侧被阻挡跳过与主模型传参回归。
- 本轮仍未完成真实 GPU、人工驾驶完整圈、实地桥梁/路牌核验及原 HexGL CC BY-NC 许可处理；不能把 OSM 几何净距称为实际现场无障碍或可见性证明。
- 验证：Python **63/63**、Node **4 套**、Chrome 148 SwiftShader **18/18**；自动物理全圈 10,495 帧、9 次路肩修正（与此前相同）；`road.json`、`route.json`、`route-data.js` 从当前源文件在临时目录重生成后 `cmp` 全部一致，`git diff --check` 通过。Chrome 软件渲染不代表真实 GPU 验收。

## 2026-11-01：M3 急弯提示提前量校准（本轮）

- 本轮先核对 `git status/log` 与 WORK_CONTINUITY、ROADMAP、M2-BLOCKOUT、ENGINE，实际干净基线 `ced4d78`（领先远端 65 提交），没有使用旧提示 `ffd16d1` 回退工作树。
- 发现可量化的玩法提示不足：原预警牌距急弯仅约 38–40m，若以清迈休闲最高速度 0.62m/物理帧、60fps 估算，只有约 1 秒反应窗口。将离线警告前置距离参数 `SHARP_TURN_WARNING_LEAD_M` 设为 80m；按 10m 路线点取整后两组实际提前量为 **89.96m / 88.48m**，对应理论约 **2.42s / 2.38s**。这只是路线距离/速度换算，不代表已验证实际玩家视距或反应。
- 使用相同 OSM 水体/815 栋建筑避让逻辑重新计算：第一组牌到水体/最近建筑轮廓约 **1.80m / 42.06m**，第二组约 **20.29m / 19.65m**；两组仍保留且不侵入 14m 道路碰撞走廊。新增提前量与不规则采样取整回归，并同步更新两侧障碍阻断测试。
- 重生成 `road.json`；场景仍为 **70 meshes / 16,738 tris**，没有增加 draw call、碰撞体或浏览器运行时计算。Python **64/64**、Node 四套回归、Chrome 148 SwiftShader **18/18** 通过；测试专用物理驾驶仍为 **10,495 帧、9 次路肩修正**。未改赛车物理、道路中心线、Three.js r50dev 或线上 `/www/wwwroot/gta.jizhang.org`。
- 真实 GPU/人工驾驶与视距、实际道路和桥梁现场核验、原 HexGL CC BY-NC 许可冲突仍未解决；后续优先测玩家可见性、驾驶手感并继续原创场景。

## 2026-11-01：M3 急弯警示牌视线遮挡回归

- 本轮先核对干净的 `git status/log`、HEAD `9f16e91` 及 WORK_CONTINUITY、ROADMAP、M2-BLOCKOUT、ENGINE；本地领先远端 67 提交，未使用旧 `ffd16d1` 覆盖新工作。
- 原来的警示牌生成器只检测牌柱与建筑/水体的净距，**无法发现建筑虽然不碰到牌柱、却挡住玩家从道路上游看到牌面**的情况。新增离线 `warning_approach_sightlines`：从上游约 30m 和 50m 路线点向牌面检查已建模建筑的 2D 足迹遮挡；先尝试首选侧，再尝试另一侧，均遮挡则不生成。高度低于 2.75m 的足迹不算遮挡。新增合成遮挡测试，确认“牌柱净距合格但视线被挡”时确实换侧。
- 当前两组 OSM 警示牌原位置没有触发视线遮挡；重生成的 road.json、route.json、route-data.js 与入库文件逐字节相同，仍是 70 meshes / 16,738 tris。新增 Chrome 148 + SwiftShader 的 r50 前向道路摄像机投影检查（两块牌、30/50/70m 上游共 6 个视点）；**这不等于真实玩家追尾摄像机、GPU 或人工驾驶的可见性验收**。
- 验证：Python **65/65**，Node **4 套**，Chrome 148 SwiftShader **19/19**（新增加 1 个前向视锥场景），默认 3 份生成资产逐字节一致；物理全圈仍为 **10,495 帧 / 9 次路肩修正**。
- 仍需真实 GPU、人工驾驶全圈、路肩修正改善、桥梁实地/地图核验及原 HexGL CC BY-NC 许可问题；只修改隔离工作树，未修改线上 `/www/wwwroot/gta.jizhang.org`。

## 2026-11-01：M3 路肩恢复错误吸附修复

- 本轮从干净 HEAD `256aa5e` 开始，核对 `git status/log` 与 WORK_CONTINUITY、ROADMAP、M2-BLOCKOUT、ENGINE，保留既有 69 个未推送提交；仅修改 SentinelX 隔离工作树。
- 复现 `MoatCollision.projectInside` 的真实空间索引边界缺陷：即使查询格子存在路段，它也不保证该路段是**远离赛道的车辆**的全局最近道路。合成闭环矩形上查询 `(75,100)`，原算法错把车辆从靠近右侧道路的位置吸附到左侧 `x=16.2`，而真正最近的右侧道路应恢复到 `x=103.8`。原 `distanceSquared` 同样返回错误的 `4225` 而非 `1225`。
- 修复为先走原 80m 空间格索引；仅当最近候选超过建索引时的 `halfWidth+12m` padding，或当前格没有候选时，回退全路线扫描。正常路内查询仍走快速索引，不在每帧无条件扫描 650 段。`distanceSquared` 与 `projectInside` 同步修复。
- 新增 Node 合成回归验证两项距离、右侧恢复坐标与普通近路查询；保持真实道路/物理速度/旧版 r50 不变。此修复针对极端越界或传送后的恢复，不代表普通自动驾驶 9 次路肩修正已经减少。
- 仍未完成真实 GPU、人工完整驾驶、桥梁现场核验及原 HexGL CC BY-NC 许可处理；未触碰 `/www/wwwroot/gta.jizhang.org`。
- 验证：Python **65/65**、Node 四套、Chrome 148 SwiftShader **19/19**（完整单人物理一圈 10,495 帧、9 次路肩修正）；默认三份 OSM 生成资产在临时目录重算 `cmp` 一致；`git diff --check` 通过。此轮不宣称已测试真实 GPU 或手动驾驶。

## 2026-11-01：M3 物理路肩诊断与损坏路线安全回退

- 本轮先检查 `git status/log` 和四份工程文档；从干净 HEAD `b3f6493` 继续，保留此前 70 个本地未推送提交。
- Chrome 148 SwiftShader 的原有一圈测试加入**实际撞路肩帧/路线点**诊断：基线 10,495 帧 / 9 次修正，分布为 index 77（1 次）、399–400（3 次）、564–566（5 次）。这表明主要修正集中在两组急弯，尚不能证明真实玩家操作或 GPU 表现；没有擅自修改物理手感或美化碰撞次数。
- 发现并修复损坏路线数据的启动缺陷：`MoatCollision` 原本对 `road_width_m=NaN` 视所有位置为可行驶区域，对负路宽平方后仍当有效；缺少/非法路线又可能让 `ChiangMaiMoat` 未注册，`?track=moat` 无法正常启动。现在初始化时验证路宽、有限坐标、有效路段及 spawn/检查点；异常时注册 Cityscape 回退，避免错误路网进入物理系统。
- 新增 Node 回归覆盖 NaN/负数/零/缺省路宽、非法点/零长度路径及缺少/损坏路线时的回退；浏览器加入 HTTP 200 但路线宽度为 null 的回退场景。默认 OSM 资源及 Three.js r50dev 未修改。
- 验证：Python 65/65、Node 四套、Chrome 148 SwiftShader **20/20**（新增坏路线 200-OK 回退）、三份默认 OSM 资产重新生成字节一致、`git diff --check` 通过。第一次浏览器诊断运行在原有第 6 场景出现加载超时；提高单场景超时到 60s 后的两次完整浏览器测试分别 19/19 和 20/20 通过，不能宣称偶发加载问题根治。
- 仍待：真实 GPU、人工完整驾驶、弯道修正次数降低、桥梁现场核验、原 HexGL CC BY-NC 许可风险。只操作隔离开发目录，不触碰线上 gta.jizhang.org。

## 2026-11-01：M3 起跑点与检查点几何校验

- 本轮先核对干净 `git status/log`、实际 HEAD `3876b9b` 与 WORK_CONTINUITY / ROADMAP / M2-BLOCKOUT / ENGINE；未采用旧提示中的 `ffd16d1` 覆盖工作树。
- 新发现路线容错缺口：即使 `route-data.js` 的 spawn/checkpoints 都是有限数字，坐标也可能远离真实道路；旧初始化仍会成功，玩家可能在赛道外起跑或遇到无法完成的检查点。全零或未归一化 spawn 四元数也会被接受。
- `ChiangMaiMoat` 现使用已构造的 `MoatCollision.distanceSquared` 校验起跑点和四个检查点位于道路中心线 `halfWidth-0.5m` 范围内，校验四元数平方模长与 1 的差不超过 0.01；不合格时走既有 Cityscape 回退。仅在初始化执行，不增加逐帧 CPU/GPU 工作，不改物理、道路中心线、r50dev 或线上站点。
- `tests/moat-regressions.js` 新增偏离道路的 spawn/checkpoint、零四元数和非单位四元数回退断言；`tests/browser_smoke.py` 增加 200-OK 但检查点偏离道路的真实浏览器回退场景。修复前新增 Node 测试已实际失败，修复后 Node 测试通过。
- 未完成：真实 GPU、人工完整驾驶、急弯 9 次路肩修正的物理改善、桥梁现场核验与原 HexGL CC BY-NC 许可处理；不能把本轮初始化防护误称为驾驶手感优化。
- 最终验证：Python **65/65**、Node **4 套**、Chrome 148 headless SwiftShader **21/21**（含新 off-road checkpoint HTTP 200 回退）；单人物理全圈仍 **10,495 帧/9 次路肩修正**，`git diff --check` 通过。

## 2026-11-01：M3 路网空间索引预分配防护

- 本轮从干净的实际 HEAD `bd2436d` 开始，先核对 Git 状态、日志及 WORK_CONTINUITY / ROADMAP / M2-BLOCKOUT / ENGINE。只在 SentinelX 持久隔离工作树开发，禁止覆盖线上 gta.jizhang.org。
- 发现并复现另一种损坏 OSM 赛道资源造成的启动卡死：即使路宽、路线坐标都是有限数字，某一段跨度达到 1e9m 时，`MoatCollision` 旧版空间索引会尝试填充数千万个 80m 网格，导致 Node 测试 40 秒超时被终止，浏览器可能在 Cityscape 回退前卡死。
- 修复为**先预检全部网格跨度再创建任何 bucket**：最多 10000 个点、单段最多 4096 个索引格、全部段最多 100000 次格插入；拒绝溢出的线段长度。若生成资源包含 `length_m`，额外检查完整闭环几何长度与声明值偏差不超过 max(1m, 2%)，阻止一处坐标损坏产生跨城虚假道路。
- 这些限制仅约束加载损坏的可选赛道数据；正常 650 点 OSM 赛道实测只有 130 个索引 bucket、1610 次格插入。既有正常道路、驾驶物理、Three.js r50dev、碰撞、场景模型和 CC0/ODbL 来源均不修改。
- Node 新增超宽道路、超长段、超多采样点、篡改长度/采样坐标回归；Chrome 新增 HTTP 200 但超长有限线段应回退 Cityscape 的启动测试。继续优先推进 399–401 / 564–566 急弯制动与驾驶手感，真实 GPU/人工驾驶/桥梁现场/HexGL CC BY-NC 风险未解决。
- 本轮实际测试结果：Python **65/65**、Node **4 套**、Chrome 148 SwiftShader **22/22**（新增超长有限路线 HTTP 200 回退）；正常单人物理全圈 **10495 帧 / 9 次路肩修正**、1750 条回放采样，双人物理竞速和旋转合成路线均通过。该防护不修改驾驶手感，真实 GPU/人工驾驶仍未验收。


## 2026-11-01：M3 近路碰撞查询的隐性全表扫描修复

- 本轮从干净 HEAD `be5eab7`、git status/log 及 WORK_CONTINUITY、ROADMAP、M2-BLOCKOUT、ENGINE 核对开始，保留已有 75 个本地未推送提交。
- 发现 `MoatCollision.distanceSquared` 和 `projectInside` 判断 `this.searchPaddingSquared`，但构造器从未赋值。`best <= undefined` 永远为 false，导致**即使车辆正在道路中央**，每次碰撞查询仍遍历全部 650 个 OSM 路段。Node Proxy 回归修复前实测一次近路查询读取路线点 1326 次并失败。
- 修复为构造空间索引时设置 `searchPaddingSquared=(halfWidth+12)^2`，使索引 padding 内的查询直接返回，超出范围仍全路段扫描以保证极端越界时最近路段正确。新增正常路内查询的读次数上限和远离道路回退回归。未修改路线、碰撞边界、车辆转向或 r50dev。
- Node VM 同机非浏览器微基准：25000 次道路采样点距离查询，模拟旧版缺失阈值耗时 24992.5ms，修复后 600.0ms（约 41.7 倍）；该数字**不是 GPU FPS 或游戏整体提速**。Python 65/65，Node 四套回归通过；Chrome 148 SwiftShader **22/22** 场景通过，完整单人物理圈仍为 10495 帧、9 次路肩修正（本次未修改驾驶手感）。
- 仍需：自动驾驶每圈 9 次路肩修正、真实 GPU/人工驾驶、现场桥梁核验、HexGL CC BY-NC 许可冲突；只改隔离开发目录，不触碰 `/www/wwwroot/gta.jizhang.org`。


## 2026-11-01：M3 旧版静态模型跨 Mesh 面数预算防护

- 本轮从实际干净 HEAD `4495012` 开始，先核对 git status/log 与 WORK_CONTINUITY、ROADMAP、M2-BLOCKOUT、ENGINE；仅操作 `/var/lib/sentinelx/chiang-mai-racer-dev`，不碰线上 `/www/wwwroot/gta.jizhang.org`。
- 发现 `StaticModelLoader.validate()` 只有每个 mesh 的 1,200,000 个索引上限和整模型 500,000 顶点上限，**缺少整个模型的索引总量上限**。攻击性或损坏的静态 JSON 可用许多仅有 3 个顶点但重复数十万次三角面的 mesh 绕过已有预算，令 r50 `THREE.Face3` 构建占用过量内存、长时间阻塞加载。
- 在构建任何 `THREE.Geometry` 之前，累计检查所有 mesh 的 `indices.length`，总计超过 **2,000,000** 时拒绝并通过已有加载错误处理走 Cityscape/车辆回退；不更改合法模型数据或渲染器。Node 新增两块各 1,050,000 索引、仅 6 个顶点的跨 mesh 回归，确保拒绝此类输入。
- 使用同一合成输入分别执行 `git show HEAD:bkcore/threejs/StaticModelLoader.js` 的旧版和当前补丁版（以首个 `Face3` 调用作为安全中断）：旧版确实进入 `Face3` 构建，新版在建模前报 `model face index limit exceeded`；HTTP 200 回归也确认仅调用一次 `onError`。当前实际模型预算：OSM `road.json` **50,214** 索引、Grab3D 赛车 **58,320**、Kenney 赛车 **6,204**，均远低于新上限。该防护属于异常资产的内存预算，不代表正常游戏 FPS 提升，也没有解决自动驾驶 9 次路肩修正。
- 验证：Python **65/65**、Node **4 套**（含 200-OK 超预算模型 `onError` 单次回调）、Chrome 148 SwiftShader **22/22**；单人完整物理圈 **10,495 帧/9 次路肩修正**，双人物理竞速通过；默认 OSM 三份生成资产在临时目录重算与仓库版本逐字节一致。首次浏览器长测在后段 off-road checkpoint 回退场景遇无严重 JS 日志的加载超时；在后段异常路线测试前隔离新 Chrome 会话后，第二次 22/22 通过。此调整降低资源积累影响，但偶发加载超时根因尚未完全确定。
- 未完成：真实 GPU、人工驾驶全圈、399–401 / 564–566 急弯手感、桥梁现场核验与原 HexGL CC BY-NC 许可冲突。下一轮优先继续可重复驾驶/制动对照，避免把加载器修复误称为驾驶改善。


## 2026-11-01：M3 跨越路肩的长帧穿透修复

- 从干净的实际 HEAD `bff1af0` 开始，核对 `git status/log` 与 WORK_CONTINUITY、ROADMAP、M2-BLOCKOUT、ENGINE，未使用旧 `ffd16d1` 覆盖已有 77 个本地提交。仅修改 SentinelX 隔离开发目录。
- 发现 `ShipControls.collisionCheck()` 只检查**帧结束**位置是否在 14m OSM 道路走廊内。若长帧/异常位移从古城外圈一侧道路跨越不可驾驶的古城内部，恰好落在另一侧合法道路上，旧代码会直接接受这次穿透；终点在另一侧路肩时也可能错误吸附到远端道路。
- 新增 `MoatCollision.projectMovement(start,end,margin)`：正常短帧只做原有终点查询；位移超过道路半宽时沿位移按不超过半径一半的间隔离散检测，第一次越界即退回上一个合法采样位置，应用现有减速/氮气取消/伤害冷却；大于 256 采样步的异常位移保守停在原路位置，避免不受限循环；若起点已不在路内，继续使用既有终点恢复。仅清迈 `MoatCollision` 使用此逻辑，Cityscape 不变。
- 新增 Node 合成闭环回归：两端都在路上却穿越内部、终点已在内部、沿道路长帧、正常短帧、极长位移的有界回退；新增 Chrome r50 WebGL 实际 `ShipControls.collisionCheck()` 的跨城道路到道路位移回归。**这是极端长帧/异常位移防穿透，不是自动驾驶 AI 或普通急弯 9 次路肩修正的优化。**
- 仍待真实 GPU、人工完整驾驶、桥梁现场核验及 HexGL 原 CC BY-NC 许可冲突；没有触碰线上 `/www/wwwroot/gta.jizhang.org`。
- 验证：Python **65/65**、Node **4 套**、Chrome 148 headless SwiftShader **23/23**（新增跨城穿透真实 r50 碰撞场景）；自动物理完整一圈 **10,495 帧/9 次路肩修正**，双人物理竞速、氮气及回放均通过；默认 OSM 三份资源从当前生成器在临时目录重算后逐字节一致，`git diff --check` 通过。真实 GPU 和人工驾驶仍未完成。

## 2026-11-01：M3 重赛物理状态残留修复

- 本轮先核对干净的 `git status/log`（起始 HEAD `64ec3d7`，领先 origin/main 79 提交）及 WORK_CONTINUITY / ROADMAP / M2-BLOCKOUT / ENGINE；仅在持久隔离目录修改。
- 发现 `ShipControls.reset()` 虽然重置速度和氮气，却**没有清除上局平滑转向角 `angular`、撞击排斥力 `repulsionForce`、碰撞方向标记、上一帧速度及场景倾斜状态**。重赛第一帧可能继承旧局撞击推力或偏航，影响单人/双人公平性。Node 回归先用 `angular=0.25` 复现失败（实际值未归零），再修复。
- 重置时清除平滑角速度、排斥力/强度、碰撞标记、上一帧速度、坡度倾斜及目标、恢复 shieldDelay，并同步上次碰撞位置到新出生点。兼容 Cityscape 旧旋转四元数缺省 w=1，不改物理转向/制动系数或 Three.js r50dev。
- `tests/regressions.js` 增加污染状态后重赛清零断言；`tests/browser_smoke.py` 增加真实 r50 车辆重赛后第一帧不得无输入移动/转向的 WebGL 场景。Python **65/65**、Node **4 套**已通过；Chrome 148 headless SwiftShader **24/24** WebGL 场景通过（新增真实重赛无输入位移/转向回归），单人物理全圈仍 **10495 帧/9 次路肩修正**、双人竞速与氮气均通过。
- 尝试一次性执行 7 组测试专用驾驶跟随器 A/B 参数，但单次 Selenium 脚本超过 HTTP 120s 读取超时，**没有可用的 A/B 结果**，不能据此改变游戏手感。下一轮拆分为短批次并逐组保存结果，继续定位 index 399–400 / 564–566 的 8 次路肩修正。
- 仍未完成真实 GPU、人工完整驾驶、桥梁现场核验及原 HexGL CC BY-NC 许可冲突；不触碰线上 gta.jizhang.org，不声称已推送 GitHub。

## 2026-11-02：M3 急弯 A/B 短批次诊断（测试工具）

- 从干净的 HEAD `fcb71fd` 开始，先核对 `git status/log` 与 WORK_CONTINUITY、ROADMAP、M2-BLOCKOUT、ENGINE；仅在 SentinelX 隔离工作目录操作。
- 上轮 Selenium 单次 7 组全圈参数对照超时，本轮改为 `tests/corner_ab.py` 独立浏览器短批次：分别在真实 OSM index 392→408、558→578 进行测试专用路线跟随器的 3 种参数 A/B，逐组调用真实 r50 `ShipControls.update(1)`；每次重置同一位置、朝向、速度和碰撞状态，并额外重复基线确认结果可复现。
- 急弯一（392→408）基线 300 帧/3 次路肩修正；提前制动 314 帧/4 次；缩短前视目标距离（3→2 个路径点）268 帧/**0 次**。急弯二（558→578）基线 382 帧/4 次；提前制动 396 帧/5 次；缩短前视目标 332 帧/**0 次**。6 次试验均完成，两个基线复跑的进度、帧数、碰撞点完全一致。
- `tests/browser_smoke.py` 增加 `--follower-lookahead {2,3}` 参数，以便用**完整物理单圈**复核短批次结论；默认值仍为 3，保留既有回归基线。
- 已实际运行 `python3 tests/browser_smoke.py --follower-lookahead 2 --physical-laps 1`：**24/24** Chrome 148 SwiftShader WebGL 场景通过，测试专用跟随器完成整圈 **10,399 帧 / 0 次路肩修正 / 1,734 条回放采样**；四组检查点、结算和双人场景仍通过。同轮重新运行默认 3 点基线确认 **10,495 帧 / 9 次路肩修正 / 1,750 条回放采样**，24/24 WebGL 场景通过。第一次默认参数浏览器长测在双人加载时偶发启动超时（step4 未显示、无严重 JS 日志），改为 60s 等待重试后全部通过；加载超时根因仍待排查。
- **重要限制**：这里优化的是测试专用路线跟随控制器，不是游戏生产车辆的自动转向/玩家手感；不能将减少的测试碰撞直接宣称为正式玩家体验改进。未修改物理、地图或生产代码。下一步应结合真实玩家视角/输入验证较短预瞄与驾驶辅助的可行性，不得把测试 AI 当作生产功能。
- 真实 GPU、人工完整驾驶、桥梁现场核验及原 HexGL CC BY-NC 许可冲突仍待解决；未推送 GitHub，严禁修改 `/www/wwwroot/gta.jizhang.org`。

## 2026-11-02：M3 成绩记录菜单与实际赛道名同步

- 本轮先核对 `git status/log` 与 WORK_CONTINUITY、ROADMAP、M2-BLOCKOUT、ENGINE，实际基线为 `e502ab8`、工作区干净、领先远端 81 个提交。未使用旧提示 `ffd16d1` 回滚。
- 发现 `launch.js` 主菜单读取历史最佳的 localStorage key 仍硬编码 `Chiang Mai Moat (blockout)`，但 `HexGL.displayScore()` 保存使用 `this.track.name`，当前 OSM 赛道名为 `Chiang Mai Moat (OSM prototype)`。因此清迈赛道正常完赛成绩虽然写入，回到主菜单仍显示“暂无记录”。
- `updateBest()` 改为从已注册的实际赛道对象读取 `name`，与游戏结算页一致；当 `route-data.js` 异常导致 `ChiangMaiMoat` 别名回退 Cityscape 时，主菜单也使用 Cityscape 的真实名称。仅改菜单读键，不迁移/清除旧数据、不修改计时、物理、OSM 路线或 WebGL。
- Node 回归先证实旧代码读取错误 key 并失败，修复后覆盖 OSM 已保存成绩可见、Cityscape 回退、URL 参数。Chrome headless 增加从真实 `track.name` 预存成绩、刷新页面验证菜单读取的浏览器场景。
- 实际回归：Python **65/65**、Node **4 套**、Chrome 148 headless SwiftShader **25/25**（新增真实 OSM 历史成绩菜单），测试专用 2 点预瞄完整单圈 **10,399 帧/0 次路肩修正/1,734 回放采样**；双人、Cityscape、异常路线回退均通过。`git diff --check` 通过。
- 仍待：真实 GPU、玩家手动完整驾驶、真实道路/桥梁现场核验及原 HexGL CC BY-NC 许可冲突。下轮继续尝试玩家可读的急弯导航，不把测试 AI 直接移入生产。严禁修改线上 `/www/wwwroot/gta.jizhang.org`。


## 2026-11-02：M3 可关闭的急弯 HUD 提示落地与验收

- 本轮先检查实际 `git status/log` 与 WORK_CONTINUITY、ROADMAP、M2-BLOCKOUT、ENGINE。基线为 `fa223d7`，领先 origin/main 82 提交，工作区已有上一轮**尚未提交**的 CornerGuide/菜单/WebGL 测试改动；未覆盖或丢弃这些在途修改。
- 完成 `bkcore/hexgl/CornerGuide.js`：基于已验证 OSM 中心线预计算转角，合并 45m 内连续急弯（当前两组，约 index 400/566），在弯前 150m 显示左/右方向与距离；按每位玩家独立位置每 6 帧更新 DOM，不写入转向、制动、碰撞或氮气状态。兼容原 Three.js r50dev。
- 新增主菜单“弯道提示：开/关”，可用 `?cornerGuide=0` 禁用；仅当当前赛道实际为有效 `moatMode` 时显示该选项，默认 Cityscape 与损坏 OSM 资源回退不显示。HUD 关闭/回放模式不创建提示。暂停、重赛、单人结算、双人结算清除残留警告。
- 审核转向坐标系：游戏局部 +Z 前进，+Y 朝上，正 yaw 对应左转；在 (x,z) 平面，叉积负值为左转、正值为右转。保留正确映射并添加合成左右转/跨圈回归，避免将屏幕 XY 的直觉套到旧引擎上。
- Node `tests/corner-guide.js` 覆盖真实两组弯道、双人独立、倒计时不提示、重赛清理、左右转方向、跨圈；`tests/launch-options.js` 覆盖菜单开关、Cityscape 与损坏 OSM 回退隐藏。浏览器新增真实 r50 提示显示/重置与单人完赛隐藏断言。
- 最终验证：Python **65/65**，Node **5 套**（regressions、moat-regressions、racedata-regressions、launch-options、corner-guide），Chrome 148 headless SwiftShader **26/26** WebGL 场景通过；测试专用 2 点预瞄全圈 **10,399 帧/0 次路肩修正/1,734 回放采样**，双人、Cityscape 和损坏路线回退仍通过；`git diff --check` 通过。以上不是人工驾驶或真实 GPU 验收。
- 未触碰 `/www/wwwroot/gta.jizhang.org`，未部署线上。原 HexGL CC BY-NC 许可冲突、桥梁/道路现场复核、真实 GPU/手动驾驶和偶发加载超时根因仍待处理。下一轮继续玩家可读性/人工驾驶、性能和许可审计，不把测试跟随器当作生产 AI。


## 2026-11-02：M3 弯道提示近距离并行道路误定位修复

- 本轮先核对实际 `git status/log` 与 WORK_CONTINUITY、ROADMAP、M2-BLOCKOUT、ENGINE；从干净的 `f4ab30c`（领先远端 84 个本地提交）继续，保留既有工作树，不触碰线上 `/www/wwwroot/gta.jizhang.org`。
- 发现 `CornerGuide.nearestIndex` 只在前次 12 点窗口的最近点距离超过 **30m** 时才全局重定位，且仍允许 30m 外的离路车辆显示提示。构造相距 12m、采样间距 10m 的两条并行道路，先定位第 10 点再跳至对侧第 31 点，旧版错误保持第 10 点；在离路 18m 的真实 OSM 弯道旁旧版仍会显示转弯警告。已先用 Node 回归复现前一缺陷。
- 将本地搜索容差与 14m 游戏道路宽度及 10m 重采样约束匹配：路半宽 + 4m（当前 **11m**），超过后全局重新定位，仍超出则隐藏提示；保留每 6 帧更新和独立双人缓存，不改赛车物理、OSM 数据或旧版 Three.js r50dev。
- 新增 Node 并行道路重定位、离路隐藏、路缘/采样间隙合法点回归；浏览器现有 M3 导航场景增加实际 OSM index 390 法线外移 18m 的离路隐藏断言。Python 65/65、Node 五套通过；Chrome 148 SwiftShader 原有 **26/26** 场景在新增离路断言前后均通过（最终复测包含真实 OSM index 390 法线外移 18m 隐藏提示），测试专用两点预瞄完整单圈 **10,399 帧/0 次路肩修正/1,734 回放采样**。
- 单样本 Chrome SwiftShader 加载剖析：OSM 3441ms/68 资源/6.5MiB 传输/47.1MiB JS 堆；Cityscape 3599ms/80 资源/7.1MiB/75.5MiB。这是无 GPU、每赛道仅 1 样本，不是稳定加载时间或 60fps 验收。
- 仍需：真实 GPU、人工完整驾驶、桥梁现场核验、偶发加载超时原因及原 HexGL CC BY-NC 许可冲突。不可将测试专用跟随器零碰撞误认为玩家实际驾驶体验。


## 2026-11-02：M3 弯道导航紧邻道路误定位与缓存修复

- 先核对实际 `git status/log` 和 WORK_CONTINUITY、ROADMAP、M2-BLOCKOUT、ENGINE；起始 HEAD `739da9b`，干净工作区、领先远端 85 提交。未使用旧 `ffd16d1` 回滚。
- 新发现：上一轮 11m 的重定位容差虽然修复了相距 12m 的并行道路，但**相距 8m 的道路**仍可能错误保留上一条道路：局部 12 点窗口距离旧道路 8m，低于 11m 阈值，因而没有发现当前坐标与另一道路中心线完全重合。先新增 Node 回归，修复前实测期望索引 31、实际错误索引 10。
- `CornerGuide.nearestIndex` 改为在每 6 帧的 HUD 更新中遍历全部 OSM 中心线采样点，选取严格最近点；以之前的索引作为等距时的稳定选择，避免路口等距提示闪烁。仍在超过道路半宽 + 4m 时隐藏离路提示；不改变物理、碰撞、氮气、OSM 资产或 r50dev。当前 OSM 路线仅 650 点，Node 单进程 10,000 次定位微基准约 51.7ms（不是浏览器 FPS）。
- Node 新增 8m 并行道路重新定位及等距稳定断言；Python **65/65**、Node **5 套**通过；Chrome 148 SwiftShader **26/26** WebGL 场景通过（测试专用 2 点预瞄完整单圈 **10,399 帧/0 次路肩修正/1,734 回放采样**）。浏览器原有 M3 导航测试通过，但**本轮 8m 合成并行道路的新断言仅在 Node 中执行**，不能误称浏览器已覆盖该特定场景。
- 尚需真实 GPU、玩家人工完整驾驶、现场道路/桥梁核验、偶发加载超时根因和 HexGL 原 CC BY-NC 许可冲突。修改只在 SentinelX 隔离目录，未触碰 `/www/wwwroot/gta.jizhang.org`，未推送 GitHub。


## 2026-11-02：M3 弯道导航连续路段定位修复（当前轮）

- 开始先核对实际干净工作树与 git log（起始 HEAD fdbf31d、领先远端 86 提交），并读取 WORK_CONTINUITY、ROADMAP、M2-BLOCKOUT、ENGINE；未使用旧 ffd16d1 覆盖现有代码。
- 发现前两轮的“最近采样点”导航仍有几何误判：当车辆在道路 A 两个约 10m 采样点之间，而相邻道路 B 恰好有更近的采样点时，HUD 可能提示 B 的弯道。合成相邻道路坐标 (5,0) 在 A 的线段上，但旧实现实际定位到 B 的索引 5；修复后正确返回 A 的索引 0。
- CornerGuide.locate() 改为求到连续道路线段的正交投影而非仅比较采样端点；记录段内比例，用于精确计算剩余弯道距离，减少每 10m 跳变。相邻道路等距时优先保留上一合法线段；离路超过原半路宽+4m 容差仍隐藏。旧 nearestIndex() 作为兼容包装保留。
- 直接全线段投影会造成不必要 CPU 开销（Node 同机 10000 次约 5.3s）；已加入 80m 空间格，预计算每段长度/边界并将格索引预分配限制为单段 4096 格、总 100000 次插入。最终 Node 10000 次路段定位约 134ms（单点微基准，非 FPS），索引 113 个格、650 条 OSM 线段。完整索引覆盖由 250 个确定性真实 OSM 附近坐标与全段暴力投影的差分测试验证。
- Node 新增临近道路“点近但线段远”、长线段中点合法定位、连续弯距精度及 250 组索引/暴力法差分回归；不改玩家转向、制动、碰撞、Nitro、道路数据、Three.js r50dev 或 CC0/ODbL 资产。
- Python 65/65、Node 五套通过；Chrome 148 headless SwiftShader 最终 26/26 场景通过，测试专用 2 点预瞄完整物理圈 10399 帧/0 次路肩修正/1734 回放采样，双人物理与 Cityscape 回退通过。浏览器回归验证现有 OSM HUD，但新合成并行道路及 250 组差分仅在 Node 执行。真实 GPU/人工完整驾驶/现场桥梁与道路/HexGL CC BY-NC 许可问题仍未完成；未修改 /www/wwwroot/gta.jizhang.org，未推送远端。


## 2026-11-02：M3 逆向行驶弯道提示修正

- 本轮首先核对实际 `git status/log` 与 WORK_CONTINUITY、ROADMAP、M2-BLOCKOUT、ENGINE；起始 HEAD `5b1a01a`，工作树干净，领先远端 88 个本地提交。未使用旧 `ffd16d1` 回滚。
- 发现 CornerGuide 的弯道箭头始终按 OSM 单向中心线的正向解释；赛车掉头、逆向行驶时仍显示同一个“急弯向左/右”，会误导玩家。新增合成路线 Node 回归先复现：在 +X 路段车辆 yaw -90° 逆向时旧 HUD 仍为 block。
- 增加只读 `dummy.quaternion` 的朝向判断：使用旧版 r50 的本地 +Z 前向向量与当前最近路线段切线点积；当夹角大于 120°（点积 < -0.5）时隐藏提示，朝向恢复时再次显示。没有修改物理、碰撞、转向、道路数据或测试专用 AI 跟随器；缺失/非法四元数保留原兼容行为。
- Node 新增正向→逆向→正向的可重复断言；Chrome WebGL 现有 OSM 导航场景增加真实 OSM 路段正反朝向/恢复断言。Python 65/65、Node 五套回归通过；Chrome 148 SwiftShader **26/26** WebGL 场景通过，包含真实 OSM 路段正向显示、逆向隐藏、恢复显示的新增断言；测试专用 2 点预瞄完整单圈 **10,399 帧/0 次路肩修正/1,734 回放采样**，双人竞速和 Cityscape 回退均通过。此测试不是人工驾驶或真实 GPU 验收。
- 仍待真实 GPU、人工完整驾驶、桥梁现场核验、偶发浏览器启动超时和原 HexGL CC BY-NC 许可冲突；仅操作 SentinelX 隔离工作目录，不触碰线上 `/www/wwwroot/gta.jizhang.org`，未推送远端。


## 2026-11-02：M3 窄路肩间隙短帧穿透修复

- 本轮首先核对实际 `git status/log` 与 WORK_CONTINUITY、ROADMAP、M2-BLOCKOUT、ENGINE；起始 HEAD `7b6d903`、工作区干净、领先远端 89 提交，未使用旧 `ffd16d1` 覆盖。
- 发现 `MoatCollision.projectMovement()` 在移动距离 <= 7m（半路宽）时直接检查终点，允许赛车单帧从一条 14m 道路带跨越 4m 非道路空隙到另一条道路带，两端均合法却没有碰撞。先在 `tests/moat-regressions.js` 构造相距 18m 的两条平行道路、起点 z=6/终点 z=12，测试在修复前失败。
- 将扫掠路径采样间距改为最多约 1m，<=1m 正常物理移动仍走快速终点检查；保留 256 步上限及异常长帧的保守恢复。短跨越现在在 z=7 的原道路边缘停止，不再跳到对面。此为离散采样，**不能证明亚米级间隙绝不穿透**；更高精度连续碰撞仍可后续评估。
- Python 65/65、Node 五套回归、`node --check` 与 `git diff --check` 已通过。Chrome 148 SwiftShader **26/26** WebGL 场景通过，测试专用 2 点预瞄整圈 **10,399 帧 / 0 次路肩修正 / 1,734 回放采样**；真实 GPU 与人工完整驾驶仍未验收。无物理参数、OSM 资产、Three.js 版本改动；未触碰 `/www/wwwroot/gta.jizhang.org`。


## 2026-11-02：M3 亚米级道路间隙穿透修复（本轮）

- 本轮先核对实际 `git status/log` 和 WORK_CONTINUITY、ROADMAP、M2-BLOCKOUT、ENGINE；起始 HEAD `5fdd3c2`，工作区干净，本地领先 origin/main 91 提交。未用旧 `ffd16d1` 覆盖新代码。
- 发现上轮 1m 固定采样仍允许 **0.6m 物理移动跨越 0.4m 非道路间隙**：两端均在相距 14.4m、宽 14m 的并行道路上，旧版 `projectMovement` 在长度 <=1m 时只检查终点。新增 Node 回归，先确认旧实现失败。
- 将 MoatCollision 扫掠改为基于距离函数 1-Lipschitz 性质的自适应区间验证：若两端距道路分别 d0/d1、移动段长 L，利用 `(d0+d1+L)/2` 上界证明整段在道路内；不能证明则二分检查。普通车道中心帧保留快速路径；限制最多 256 次中点检测、深度 20，病态移动保守阻断。为避免紧贴路缘的误撞保留 2cm 判定容差，<=1m 的普通越界终点仍走既有回投（避免卡死在急弯），**因此并非数学上完全精确的连续碰撞**。
- 首次实现后浏览器急弯跟随器在 index 399 卡住（430 帧、287 次修正），已据此修复普通短帧越界恢复与边界数值容差，最终急弯恢复为 301 帧/3 次路肩修正；这次失败没有被计作通过。
- Node 新增 0.4m 间隙/合法贴边行驶回归；Chrome r50 真实 ShipControls.collisionCheck 增加合成 0.4m 间隙场景。最终 Python **65/65**、Node **5 套**、Chrome 148 SwiftShader **27/27** WebGL 场景通过；测试专用两点预瞄物理完整单圈 **10,399 帧/0 次路肩修正/1,734 回放采样**，双人和 Cityscape 回退仍通过。Node 单次 10k 中心线短移动微基准约 161ms（不是 FPS）。
- 尚未完成真实 GPU/人工驾驶、桥梁道路现场核验、浏览器偶发加载超时和 HexGL 原 CC BY-NC 许可审计。没有修改赛车手感参数、OSM 资产或 Three.js 版本；未推送 GitHub，未触碰 `/www/wwwroot/gta.jizhang.org`。

## 2026-11-02：M3 极窄路线的路肩恢复边界修复

- 开始核对 `git status/log` 和 WORK_CONTINUITY、ROADMAP、M2-BLOCKOUT、ENGINE；实际基线 `7457fa1`，工作区干净、领先远端 93 个提交，未按旧 `ffd16d1` 回滚。
- 发现 `MoatCollision.projectInside` 的恢复偏移下限硬编码为 **0.5m**：当有效但异常窄的 `road_width_m=0.6m` 路线被导入，车辆从路外恢复到距离中心线 0.5m 的位置，仍超出 0.3m 半路宽，导致每帧持续判定路外。先添加 Node 失败回归，确认旧实现未能将车放回可驾驶区域。
- 修复为恢复偏移 `max(0, halfWidth - max(0, margin))`，始终不超过半路宽；正常 14m 道路、0.8m 安全内缩的结果仍为 6.2m，未改变游戏物理参数、路线或 Three.js。新增窄路恢复可驾驶性与正常路宽行为断言。
- Python **65/65**、Node **五套**回归、Chrome 148 SwiftShader **27/27** WebGL 场景通过；测试专用两点预瞄整圈 10,399 帧/0 次路肩修正/1,734 条回放采样。Chrome 现有场景覆盖正常 14m 道路，新 0.6m 边界断言只在 Node 执行。真实 GPU、人工完整驾驶和许可证冲突仍未解决。此修复仅针对异常窄路数据的边界健壮性，**不是实际清迈路宽的现场确认**。


## 2026-11-02：M3 亚米级道路间隙的路肩回投防跨越

- 本轮先核对 `git status/log` 与 WORK_CONTINUITY、ROADMAP、M2-BLOCKOUT、ENGINE，起始 HEAD `46b2675`，工作树干净、领先远端 94 个提交；仅在 SentinelX 隔离工作目录继续。
- 复现新的可验证 Bug：两条 14m 宽道路中心线相距 14.4m，赛车从 z=6.9 单帧移至 z=7.3（0.4m），终点位于两条道路的 0.4m 非道路间隙。旧版 `projectMovement` 因 `end.corrected && length<=1` 直接接受 `projectInside`，将车从左侧道路投影到另一侧 z=8.2，跨越不可驾驶间隙。新增 Node 失败回归记录原行为。
- 修复：短帧路肩恢复前，沿起点到恢复点运行现有有界连续扫掠认证；合法的同侧路肩回投保持不变，跨越另一条道路则保留安全位置。内部 `checkingRecovery` 防止递归回投循环；不修改 OSM、玩家物理参数、Three.js r50dev 或 Cityscape。
- Node 新增非法跨路肩回投及正常同侧回投断言；Chrome 浏览器现有 0.4m 间隙真实 `ShipControls.collisionCheck()` 场景增加终点位于间隙时的回投断言。
- 实测：Python **65/65**、Node **5 套**、Chrome 148 SwiftShader **27/27** WebGL 场景通过（新增真实 `ShipControls.collisionCheck()` 间隙内终点回投断言）；测试专用 2 点预瞄整圈 **10,399 帧 / 0 次路肩修正 / 1,734 回放采样**。首次新增 Node 测试在旧实现上失败，修复后通过。
- Node 单进程 10,000 次调用微基准：中心行驶 87.4ms、同侧路肩 138.2ms、跨间隙路肩 269.8ms；仅为一次 CPU 微基准，非浏览器 FPS。服务器只有虚拟 VGA `1234:1111`，`/dev/dri` 无 render 节点，无法在本机完成真实 GPU 验收。
- 真实 GPU、人工完整驾驶、现场道路/桥梁及 HexGL CC BY-NC 许可仍未完成。严禁修改 `/www/wwwroot/gta.jizhang.org`，本地提交不等于远端推送。

## 2026-11-02：M3 斜向道路浮点采样精度修复

- 先核对 git status/log 和 WORK_CONTINUITY、ROADMAP、M2-BLOCKOUT、ENGINE；起始 HEAD `84fe20d`、领先 origin/main 95 提交，发现四个文件已有未提交的连续坐标修复与回归测试，保留现有工作树并完成验证，没有回滚旧快照。
- 确认 OSM `MoatCollision` 使用连续米坐标；旧 `Gameplay.checkPoint()` 与 `ShipControls.boosterCheck()` 沿用 Cityscape 位图的 `Math.round`，斜向道路边缘可能把仍在 14m 路廊内的车采样到路外，漏掉检查点或氮气加速带。仅对旧位图保持整数取样，OSM 分析器传入原始浮点米坐标。
- 新增 Node 合成 45° 道路边缘断言，验证合法位置 (50.2,59.6) 被取整为路外 (50,60)，同时覆盖真实 Gameplay.checkPoint 与 ShipControls.boosterCheck；Chrome r50 实例验证相同场景。Python 65/65、Node 五套、Chrome 148 SwiftShader 28/28 WebGL 场景通过，`git diff --check` 和相关 JS 语法检查通过。
- 浏览器测试专用物理跟随器本次整圈 10495 帧/9 次路肩修正；另一次同期测试曾得到 10399 帧/0 次修正，提示跟随器时序或加载环境仍有波动，不得当作真实玩家零碰撞验收。服务器无真实 GPU；人工驾驶、现场桥梁/道路核验及原 HexGL CC BY-NC 许可冲突仍待解决。未修改线上 `/www/wwwroot/gta.jizhang.org`，未推送 GitHub。

## 2026-11-02：M3 检查点跨帧漏判与物理圈复测

- 本轮先核对 `git status/log` 与 WORK_CONTINUITY、ROADMAP、M2-BLOCKOUT、ENGINE；起始 HEAD `2dccfbd`，工作区干净、领先 origin/main 96 提交，未回滚旧快照。
- 复现可验证的 **OSM 检查点跨帧漏判**：12m 半径检查点在 `(50,0)`，赛车从 `(35,0)` 移至 `(65,0)`，两端均合法且均不在检查点圆内；旧 `Gameplay.checkPoint()` 仅取终点像素，返回 -1。新增 Node 失败回归后修复。
- `Gameplay` 对 OSM 记录上次检查点采样位置（比赛重新开始时重置），仅在终点未命中时检查运动线段与**下一个**检查点的圆盘交集；利用现有 `MoatCollision.projectMovement` 验证整条直线运动留在道路内，拒绝穿越旧城内侧的作弊捷径。Cityscape 原位图逻辑保持不变。测试覆盖合法跨帧命中、同位置重复检查不重复触发、非法穿城捷径拒绝、重新开始时采样原点清理。
- 基线浏览器回归连续两次均为 28/28、完整单圈 **10495 帧/9 次路肩修正**，相同冲击点；此前 10399 帧/0 次来自不同轮次，不能仅据此断言随机性。另完成原版代码 3 圈物理回归 **31474 帧/26 次路肩修正**、28/28。修复后 Python **65/65**、Node 五套、Chrome 148 SwiftShader **29/29**；单圈 **10495 帧/9 次路肩修正**、1750 回放采样。
- 风险：跨帧补判采用两次游戏逻辑采样之间的**直线段**，急弯处实际轨迹弯曲时可能保守拒绝；大跨度/非法道路穿越也会被现有碰撞预算拒绝。真实 GPU、人工驾驶、现场道路/桥梁核验、HexGL CC BY-NC 许可冲突未解决。未推送 GitHub，未触碰 `/www/wwwroot/gta.jizhang.org`。

## 2026-11-02：M3 检查点终点落点绕过道路扫掠修复

- 开始先核对实际 HEAD `046a550`、`git status` 干净、四份权威工程文档，未使用旧 `ffd16d1` 覆盖任何文件。
- 先新增失败 Node 回归：合法左侧路点 `(0,50)` 直接跳到顶部检查点 `(50,0)`，跨越矩形赛道内部不可驾驶区域。旧 `Gameplay.checkPoint()` 因终点位于检查点圆内立即返回 1，绕过上一轮对“跨帧圆盘补判”增加的道路扫掠验证。
- 修复仅针对 OSM 连续坐标：当**下一个**检查点直接命中但前后采样距离超过 24m（两倍 12m 检查点半径），先检查上次位置仍合法，并用 `projectMovement(...,checkingRecovery=true)` 验证直线轨迹。合法道路长步进仍可计点；原 Cityscape 位图和普通短帧不变。
- 浏览器原有“模拟整圈”与“双人独立状态”用直接注入坐标，现明确同步注入邻近检查点采样，仅测试状态机；真正的物理整圈测试仍由 `ShipControls.update(1)` 路线跟随器执行，不会在生产代码绕过新校验。
- 此规则主要防止异常大步进/传送错误获得检查点；24m 以下仍依赖物理碰撞系统，直线扫掠在复杂弯道可能保守拒绝。真实 GPU、人工驾驶、现场道路核验与 HexGL CC BY-NC 许可问题仍未解决。
- 本轮最终复核：Python **65/65**，Node **5 套**，Chrome 148 SwiftShader **29/29**（分别以 1 圈和 3 圈模式各执行一次）。测试专用物理路线跟随器：1 圈 **10495 帧/9 次路肩修正/1750 条回放采样**；3 圈 **31474 帧/26 次路肩修正/5246 条回放采样**。最初浏览器回归失败是原测试直接瞬移到检查点，与新增异常跨路保护冲突；调整模拟状态机测试的上一采样位置后通过，生产物理圈不注入位置。首次修改测试脚本时误用 Python `#` 注释写入 JS 片段导致语法异常，已改为 `//` 并完整复测。以上失败均未计为通过。当前服务器无真实 GPU，未推送远端，未触碰无关线上站点。

## 2026-11-02：M3 检查点短距离跨路与连续采样可信性修复

- 本轮开始先核对 `git status/log` 和 WORK_CONTINUITY、ROADMAP、M2-BLOCKOUT、ENGINE；实际起始 HEAD `eaed77d`，工作树干净、领先 `origin/main` 101 个本地提交，未使用旧 `ffd16d1` 回滚。
- 先新增 Node 失败回归：两条 14m 宽平行道路相距 20m（中间 6m 非道路），赛车从 `(0,6.9)` 跳到 `(0,13.1)`，移动仅 6.2m 且落在下一个检查点 12m 圆内。原先 >24m 才验证直接命中，错误计点（实测预期 -1、实际 1）。去除 24m 豁免后发现第二个真实漏洞：第一次非法命中虽被拒绝，`_lastCheckpointSample` 已提前更新到跳跃终点，第二次静止调用又能获得检查点（Node 修复前失败）。
- `Gameplay.checkPoint()` 现在在 OSM 模式对**每次游戏逻辑采样**使用现有有界 `projectMovement(..., checkingRecovery=true)` 检查连续道路路径；非法移动不更新最后可信采样，因此中间先非法跨路、再进入检查点也不能绕过验证。直接命中与跨帧圆盘补判共用一次认证，避免重复扫掠；Cityscape 仍使用原位图逻辑。合法短帧、长帧直线道路与原检查点顺序保持不变。
- Node 新增短距离跨路、非法终点停留重试、无检查点中间跨路与同侧合法命中回归，旧实现分别先复现失败。Chrome 148 SwiftShader 浏览器场景在真实 r50 `Gameplay.checkPoint()` 合成道路中覆盖短距离跨路、重复拒绝、合法同侧命中；完整 1 圈测试专用物理跟随器 **10495 帧/9 次路肩修正/1750 回放采样**，3 圈 **31474 帧/26 次路肩修正/5246 回放采样**。Python **65/65**、Node 五套、Chrome **29/29**（分别以 1/3 圈各运行一次）通过。
- 限制：每次 OSM 逻辑采样增加有界道路扫掠，尚无真实 GPU/人工完整驾驶验收；极端长帧在急弯处的直线段可能保守拒绝，非法大幅瞬移后可能需要比赛重启才能重新建立可信采样。真实道路/桥梁现场核验和原 HexGL CC BY-NC 许可冲突仍待解决。没有推送 GitHub，未触碰 `/www/wwwroot/gta.jizhang.org`。

## 2026-11-02：M3 回放倒退定位修复（本轮）

- 本轮先核对 `git status/log` 和 WORK_CONTINUITY、ROADMAP、M2-BLOCKOUT、ENGINE，实际起始 HEAD `57bf66b`、工作区干净、本地领先远端 103 个提交；未依据旧 `ffd16d1` 覆盖新代码。
- 复现 `RaceData.applyInterpolated()` 回放时间倒退时的真实边界 Bug：先播放到 300ms 末帧，再请求 150ms，旧实现仍将赛车固定在末帧位置 30（正确应为 15），因为 `seek` 只能向前递增。新增 Node 回归先失败（30 !== 15），修复后通过。
- 回放游标现在会在时间倒退时回退至对应采样区间，保持正常正向播放与旧版 Three.js r50dev 的插值逻辑不变；没有新增可视化拖动 UI，也没有修改赛车物理、OSM 赛道、氮气或碰撞。
- `tests/browser_smoke.py` 在真实 r50 WebGL 回放场景增加「末帧→中间→首帧」逆向时间请求，验证实际赛车坐标和游标，不只依赖 Node 模拟。Python **65/65**、Node **5 套**、Chrome 148 SwiftShader **29/29** 场景通过；测试专用跟随器物理单圈 **10495 帧/9 次路肩修正/1750 条回放采样**，双人物理竞速及 Cityscape 回退仍通过。
- 仍需真实 GPU、人工完整驾驶、道路/桥梁现场核验、加载超时根因及原 HexGL CC BY-NC 许可问题。仅操作 SentinelX 持久隔离目录，未推送 GitHub，未触碰 `/www/wwwroot/gta.jizhang.org`。

## 2026-11-02：M3 回放四元数健壮性与急弯 A/B 验证

- 开始先核对 `git status/log` 与 WORK_CONTINUITY、ROADMAP、M2-BLOCKOUT、ENGINE；起始 HEAD `a2b3d9b`，工作树干净、领先 origin/main 105 个本地提交，未使用旧快照。
- 复现本地回放数据验证缺陷：`RaceData.import()` 接受零长度或长度为 2 的四元数（数值均有限），后续 r50 `Quaternion.slerpSelf` 假定单位四元数，可能产生无效旋转。先增加 Node 失败回归（Missing expected exception），随后拒绝平方长度偏离 1 超过 0.02 的回放帧，并在插值前归一化轻微舍入误差；非法导入不替换已有有效数据。浏览器实际 r50 回放验证了损坏帧拒绝与微小误差归一化。
- 独立测试专用驾驶 A/B：路线 index 392–408 的 3 点预瞄 3 次路肩修正、2 点预瞄 0 次；index 558–578 分别 4 次与 0 次。提前刹车参数在这两处没有改善。新增测试断言保护两处 2 点预瞄零碰撞；这**只证明测试控制器轨迹可改善**，没有修改正式玩家物理/自动驾驶。
- Chrome 148 SwiftShader `--follower-lookahead 2` 完整一圈 10,399 帧、0 次路肩修正、1,734 回放采样；29/29 WebGL 场景通过。先前一次浏览器启动在双人场景超时，失败未计入通过，隔离重跑后全套成功。Python 65/65、Node 五套回归通过。与默认 3 点预瞄 10,495 帧/9 次修正的旧基线是不同**测试驾驶策略**，不能宣称正式驾驶体验改善。
- 未改 OSM 资产、赛车物理、Three.js 版本或 `/www/wwwroot/gta.jizhang.org`；无真实 GPU，人工驾驶、现场道路/桥梁核验与 HexGL CC BY-NC 许可问题仍待解决。仅本地 Git 提交，未推送 GitHub。

## 2026-11-02：M3 回放导入数据别名隔离

- 开始核对 `git status/log` 和 WORK_CONTINUITY、ROADMAP、M2-BLOCKOUT、ENGINE，实际基线 `29f4cb5`、工作树干净、领先远端 108 个本地提交；未使用旧 `ffd16d1` 回滚。
- 新增先失败的 Node 回归：`RaceData.import()` 校验过的调用方数组仍被 `this.data=imp` 直接引用；导入后将首帧位置 10 改成 999，回放就错误地使用 999（旧版实际报错 `999 !== 10`）。调用方还能事后改成零四元数或追加帧，绕过导入校验。
- 修复为在验证每一帧后保存独立 `slice` 快照，成功校验后原子替换回放数据；非法导入仍保留之前有效回放。浏览器真实 r50 场景增加导入后篡改源数组、检查位置与旋转不受影响。
- 本轮已通过 Python 65/65、Node 五套、JS/Python 语法及 `git diff --check`。Chrome 148 SwiftShader 首轮通过前 28 个场景（含新增真实 r50 回放别名测试），但最后的旋转合成赛道加载在默认 35 秒超时，不能记作 29/29；已使用 60 秒超时重试全套，最终 **29/29 场景通过**，其中真实 r50 回放输入别名断言通过。测试专用 2 点预瞄完整单圈 **10,399 帧 / 0 次路肩修正 / 1,734 回放采样**；双人竞速与旋转赛道回归通过。首次超时不计入成功结果，重试通过不能证明加载超时根因已消失。修复不涉及赛车物理、OSM、Three.js 版本或无关线上站点。真实 GPU/人工驾驶/现场道路与原 HexGL CC BY-NC 许可风险仍未解决。

## 2026-11-02：M3 回放重复时间戳与大跨度跳转修复

- 开始先核对实际 `git status/log` 与 WORK_CONTINUITY、ROADMAP、M2-BLOCKOUT、ENGINE：起始 HEAD `5854d78`、工作区干净、领先 origin/main 110 提交。只修改持久隔离目录。
- 先新增失败 Node 回归：相同时间戳的两帧（100ms，位置 10/20）在正向播放和从末帧回退后产生不同结果（10 与 20）；另一个 65,536 帧测试中，跨 60,000 帧跳转访问数组超过 100 次，暴露旧 `while` 逐帧线性扫描的 UI 卡顿风险。
- `RaceData.applyInterpolated` 现对普通区间保留 O(1) 快速路径；跨区间跳转改用上界二分查找 O(log N)，重复时间戳统一取该时刻最后一帧，精确到最后时间戳即可定位末帧；非法 NaN/Infinity 时间直接拒绝而不传给 r50 旋转插值。导入校验、物理、OSM、Three.js r50dev 均未改变。
- Node 新增方向无关的重复时间戳、65,536 帧正反跳转数组读取上限与 NaN 时间保护断言；Chrome r50 浏览器回放新增重复时间戳正反定位断言。Python **65/65**、Node **5 套**、语法与 diff 检查、Chrome 148 SwiftShader **29/29** 均通过；测试专用 2 点预瞄物理整圈 **10,399 帧 / 0 次路肩修正 / 1,734 条回放采样**，双人物理竞速和 Cityscape 回退均通过。此次浏览器完整测试一次成功（112.88 秒），但不代表历史偶发加载超时已经根治。
- 真实 GPU、人工完整驾驶、道路/桥梁现场核验及 HexGL CC BY-NC 许可风险仍未解决。无远端推送、无生产站点改动。

## 2026-11-02：M3 完赛回放持久化（本轮）

- 开始先核对 `git status/log` 和 WORK_CONTINUITY、ROADMAP、M2-BLOCKOUT、ENGINE；起始 HEAD `463e2eb`、工作区干净、领先 `origin/main` 112 提交，未覆盖旧快照或无关线上目录。
- 发现真实功能缺口：`Gameplay.start()` 的 replay 模式读取 `race-<track>-replay`，但全仓库没有任何写入该键的代码，因此正常单人完赛无法生成下次可播放的记录。先新增 Node 失败回归（`recording.save is not a function`），随后实现 `RaceData.save(storage)`，在 `HexGL.displayScore()` 的单人 FINISH 路径调用。
- 保存前复用 `RaceData.import` 的完整帧数、时间、有限数值和单位四元数校验，成功才一次写入 localStorage；赛车损毁、双人赛、回放模式、异常录制或存储空间不足不覆盖此前有效回放，存储异常不阻塞成绩页。
- Node 回归验证保存键与回放读取键一致、保存后能插值播放、非法录制不覆盖有效存档、replay 模式不写入、QuotaExceededError 不导致异常；Chrome 物理完整圈回归新增完赛后实际 localStorage 帧数断言。 Python **65/65**、Node **5 套**及 JS/Python 语法检查均通过；Chrome 148 SwiftShader 首轮 **29/29** 通过，测试专用两点预瞄物理单圈 **10,399 帧 / 0 次路肩修正 / 1,734 回放采样**。
- 第二次以更新后的浏览器测试脚本完整复跑 **29/29** 通过：回放测试改为从刚刚实际写入的 localStorage JSON 读取，再用真实 r50 赛车对象执行插值/回退；证明保存与读取形成闭环。首次和第二次均为 10,399 帧、0 次测试跟随器路肩修正、1,734 回放采样。
- 仍无玩家可见的回放入口/拖动 UI；该改动只补齐已有底层 replay 读取机制的持久化环节，不能宣称回放产品 UI 完成。真实 GPU、人工驾驶、现场 OSM 核验及原 HexGL CC BY-NC 许可冲突仍未解决。

## 2026-11-02：M3 玩家可见的完赛回放与时间轴

- 开始先核对 `git status/log` 与 WORK_CONTINUITY、ROADMAP、M2-BLOCKOUT、ENGINE；实际起始 HEAD `2dda2b7`、工作树干净、领先 origin/main 114 提交，没有使用旧快照或触碰线上 gta.jizhang.org。
- 上一轮虽保存单人完赛轨迹，但成绩页没有任何观看入口。现在有效单人完赛存档才显示「观看回放」；在同一 WebGL 场景中读取、验证本地回放，提供暂停/播放、可拖动时间轴、进度时钟、返回成绩页。拖动时间轴自动暂停；播至末尾自动暂停，再点播放从头开始。按 Esc 返回、空格暂停/播放。回放时隐藏会遮挡进度条的氮气面板，退出后恢复。
- 回放只驱动经过 `RaceData.import` 校验的 r50 赛车姿态；在场景渲染循环跳过 `ShipControls.update`，不再额外推进物理、氮气或碰撞。非法存档拒绝进入回放，单人损毁和双人比赛不显示按钮。关闭回放不覆盖成绩或回放数据，重新比赛仍调用原重置流程。
- 浏览器新增一个真实按钮事件、滑动输入、逆向 seek、非法存档、关闭与末尾重新播放的 WebGL 场景；第一次完整 Chrome 148 SwiftShader 测试 **30/30** 通过。最终修改后需以实际重跑结果为准；Python 65 项、Node 5 套及 JS/Python 语法回归已通过。
- 这是赛后本地回放 UI，尚未实现主菜单跨会话回放库/导出，也不是人工驾驶或真实 GPU 验收。原 HexGL CC BY-NC 与仓库 MIT 许可冲突、OSM 现场核验、偶发 Chrome 加载超时仍未解决。修正了游戏制作名单中把原项目简单标为 MIT 的误导性文字，明确部分源码带 CC BY-NC 声明且授权待核实。

## 2026-11-02：M3 跨页面历史回放入口（主菜单）

- 本轮从实际干净 HEAD `5af7282`（领先 origin/main 116 提交）起步，先核对 Git 状态和 WORK_CONTINUITY、ROADMAP、M2-BLOCKOUT、ENGINE，未采用旧快照覆盖工作树。
- 之前只有**本次单人完赛成绩页**可进入回放；刷新页面后虽然 localStorage 保留最近一次有效轨迹，主菜单却没有入口。新增「观看上次比赛回放」，按当前真实赛道名称读取保存键；无记录、无效 JSON、损坏帧、单帧或非正时长录制，以及双人模式均隐藏按钮。菜单设置变化时重新计算；缓存相同原始存档的验证结果，避免频繁重复解析大回放。
- 从主菜单直接加载对应 r50dev 场景、进入纯轨迹回放，保留暂停/拖动/时间显示；不启动玩家驾驶物理和计圈更新。回放底部退出按钮在菜单入口模式显示「返回主菜单」并刷新释放 WebGL 资源；赛后入口仍返回成绩页。读取与显示均使用 `RaceData.import()` 验证，不改变存档格式、物理、OSM、Three.js 版本或许可。
- 回归：Node `tests/launch-options.js` 覆盖有效/无效存档、双人隐藏、Cityscape fallback 隔离、菜单直达；Chrome `tests/browser_smoke.py` 增加跨页面读取、实际 WebGL 冻结物理、拖动和返回菜单及损坏存档保护场景。实测 Python **65/65**、Node **5 套**、Chrome 148 SwiftShader **31/31** WebGL 场景通过（本轮新增主菜单历史回放跨页场景）；测试专用两点预瞄整圈 **10,399 物理帧 / 0 次路肩修正 / 1,734 回放采样**。浏览器全套耗时 145.24 秒，本轮一次通过。
- 仍需真实 GPU、人工驾驶、现场道路/桥梁核验，HexGL 部分 CC BY-NC 声明与 MIT 文件冲突尚未解决。仅本地提交；不触碰 `/www/wwwroot/gta.jizhang.org`。

## 2026-11-02：M3 部分录制覆盖有效回放的修复

- 开始核对 `git status/log` 与 WORK_CONTINUITY、ROADMAP、M2-BLOCKOUT、ENGINE；实际起始 HEAD `66bdb0f`、工作区干净、领先 origin/main 118 个提交，未采用旧快照。
- 新增 Node 失败回归确认 `RaceData.save()` 原先仅使用 `import()` 的帧结构验证，单帧、同时间戳零时长或负起始时间的录制仍可写入 `race-<track>-replay`，覆盖之前正常的比赛回放；但菜单和播放器均拒绝这些录制，导致用户失去上次可观看录像。
- 现在保存前额外要求至少两帧、首帧时间非负、末帧时间严格大于首帧；不改变 `RaceData.import()` 对单帧/重复时间戳的安全插值兼容性。三类异常均拒绝写入并保留旧存档，正常录制不变。Node 五套、Python 65 项及 JS 语法/`git diff --check` 已通过。
- 代码提交 `f2d96e1`。本轮不改赛车物理、OSM 路线、Three.js r50dev 或无关线上 `/www/wwwroot/gta.jizhang.org`；真实 GPU、人工完整驾驶、现场 OSM 核验和原 HexGL CC BY-NC 许可冲突仍未解决。

- 浏览器实测补充：Chrome 148 SwiftShader 首次在后段损坏 route-data.js 回退场景加载超时（前 27 项成功，非 31/31）；90 秒等待重试完整 **31/31 通过**，测试专用 2 点预瞄物理整圈 **10,399 帧 / 0 次路肩修正 / 1,734 条回放采样**。尝试在路由元数据回退前增加全新 Chrome 进程隔离，另一轮却在最后旋转赛道场景超时，故撤销该未证实有效的测试调整。超时页面 readyState=complete、WebGL 场景未就绪、无严重浏览器日志；根因未定，不能声称修复。
- 修正回归测试自身覆盖：配额异常测试改用可观看的双帧录制，并断言确实调用了 `storage.setItem`，避免新保存门槛导致测试虚假通过。最终 Node 五套与 Python 65/65 通过。

## 2026-11-03：M3 可选音频加载失败不再卡住比赛

- 本轮先核对 git status/log 和 WORK_CONTINUITY、ROADMAP、M2-BLOCKOUT、ENGINE；起始 HEAD `27f4641`，工作区干净，领先 origin/main 121 提交；没有使用旧 `ffd16d1` 覆盖新改动。
- 复现真实缺陷：旧 `bkcore/Audio.js` 在 HTTP 404 时仍尝试解码，解码失败只输出错误而不调用完成回调；网络失败或无响应也没有可靠结束路径，`Loader.progress.loaded` 不能达到 total，游戏可能永远停在加载页。新增 `tests/audio-regressions.js`，旧实现先失败，修复后通过。
- 可选音频现在对 404、网络失败、解码失败、请求/解码超时（15 秒看门狗）及 HTMLAudioElement error/abort 均只完成一次回调；故障音效标记为静音，`play/stop/volume` 安全跳过，赛车仍可进入。保留 file:// XHR status=0 且有有效响应的兼容路径。
- 另复现 `Loader.loadSound` 丢弃清单的 `usePanner` 标志（Node 旧值 undefined），已补传给 `Audio.addSound`，使用原有 WebAudio panner。
- `tests/browser_smoke.py` 增加在内存中对 `audio/bg.ogg` 故意返回 404 的真实 WebGL 场景，验证赛道加载、资源计数完成、比赛重开；超时诊断增加 pending 资源、加载进度、失败音效列表。
- 首轮 Chrome 148 SwiftShader **32/32** 通过，测试专用两点预瞄完整一圈 **10,399 帧 / 0 次路肩修正 / 1,734 回放采样**；Python 65 项、Node 六套回归通过。历史偶发 WebGL 超时尚不能证明全部由音频造成，仍需捕获真实超时的 pending 资源。
- 未修改 OSM 资产、赛车物理、Three.js r50dev；真实 GPU、人工完整驾驶、道路/桥梁现场核验及 HexGL CC BY-NC 许可冲突仍未解决。未推送 GitHub，未触碰 `/www/wwwroot/gta.jizhang.org`。

## 2026-11-03：M3 可选贴图/HUD 图片失败时的加载降级

- 本轮首先核对 `git status/log` 与 WORK_CONTINUITY、ROADMAP、M2-BLOCKOUT、ENGINE；实际起始 HEAD `0f44a01`，工作树干净，领先 origin/main 123 提交；未依据过期的 `ffd16d1` 覆盖当前代码。
- `bkcore/threejs/Loader.js` 旧逻辑：`THREE.ImageUtils.loadTexture` 错误回调只报告错误，不推进 `progress.loaded`；HUD `Image` 完全没有 `onerror`。任一必经的图片 HTTP 404 都可能使加载界面永久等待。新增 `tests/loader-failures.js` 先复现失败（HUD onerror 缺失），再修复。
- 可选贴图失败时生成 2×2 白色 Canvas，设置 r50 `Texture.image/needsUpdate`；HUD 图片失败时用 192×25 透明 Canvas 保持原 1920:250 比例，以满足 HUD `drawImage`/尺寸访问。错误仍报告，视觉会降级但不阻止进入比赛。`Loader.updateState` 增加完成状态幂等保护，重复图片事件不重复计数或触发 `onLoad`。
- Node 七套回归（新增 loader-failures）、Python 65/65、语法与 `git diff --check` 通过。Chrome 148 SwiftShader 新增故意让 `textures/hud/hex.jpg` 与 `textures/hud/hud-bg.png` 返回 HTTP 404 的场景，检查 WebGL 启动、资源计数、Canvas 降级与重新比赛。
- Chrome 148 SwiftShader 首次完整运行旧 32 项均通过，但新增视觉 404 场景把预期的 `console.error("Error loading ...")` 误判为意外严重错误，故该次全套不能记作通过。修正测试过滤仅忽略本场景预期的两个 404/错误日志后，重新执行完整 **33/33 WebGL 场景通过**（144.73 秒）；包括实际 r50 WebGL 重启和 HUD Canvas 降级。
- 尚未覆盖天空盒立方贴图/几何/分析图的所有弱网错误与无响应超时；Chrome 历史偶发加载超时不能宣称根治。真实 GPU、人工驾驶、OSM 现场核验和 HexGL CC BY-NC 授权冲突仍未解决。仅本地隔离目录修改，不部署 `/www/wwwroot/gta.jizhang.org`。

## 2026-11-03：M3 天空盒单面加载失败保护

- 本轮开始核对 Git status/log 与 WORK_CONTINUITY、ROADMAP、M2-BLOCKOUT、ENGINE；基线 `33af6ae`、工作区干净、本地领先远端 125 提交。没有采用提示中的旧 ffd16d1。
- 确认 r50dev 的 `THREE.ImageUtils.loadTextureCube` 只有六张图全部 onload 才回调，**没有 onerror**；缺失任一天空盒图片会让 `Loader.progress.loaded` 无法达到 total。新增 `tests/cubemap-regressions.js` 先在旧实现上复现失败（onerror 不存在）。
- `bkcore/threejs/Loader.loadTextureCube` 改为构建同款 r50 `THREE.Texture` + `CubeRefractionMapping`，逐面绑定成功/失败事件，15 秒超时、一次性完成。任意面失败时将六面**统一**替换为 2×2 白色 Canvas，防止不同面尺寸导致 WebGL cubemap 不完整；成功时保留原六张天空图。晚到事件不能重复计数。
- Node 新增失败、成功、迟到回调和超时回归；Python 65 项与全部 Node JS 回归通过。Chrome 新增单面 HTTP 404 的完整 WebGL 场景，实际 Chrome 148 SwiftShader 完整 **34/34** 通过（约 139 秒）；测试专用两点预瞄物理整圈 **10,399 帧、0 次路肩修正、1,734 条回放采样**，不代表人工驾驶。不改变 OSM 地图、驾驶物理或 Three.js 库文件。
- 仍未覆盖旧几何/分析图的所有失败路径；真实 GPU、人工驾驶、道路/桥梁现场复核与原 HexGL CC BY-NC 许可冲突仍待解决。未触碰线上 `/www/wwwroot/gta.jizhang.org`。


## 2026-11-03：M3 旧 r50 JSON 几何加载失败保护

- 开始时核对了 `git status/log` 与 WORK_CONTINUITY、ROADMAP、M2-BLOCKOUT、ENGINE，实际基线 `b7bb7ef`，工作树干净，领先远端 127 个提交；未回退至过时的 ffd16d1。
- 确认 `THREE.JSONLoader.load/loadAjaxJSON` 在 HTTP 404、空响应、异常 JSON 或网络无响应时不会调用成功回调，`Loader.progress` 永久缺项。新增 `tests/geometry-failures.js` 在旧实现上先复现 `onreadystatechange` 缺失，再修复。
- `bkcore.threejs.Loader.loadGeometry` 现在自行管理 XHR，成功时仍调用原 r50 `JSONLoader.createModel`，失败时提供可被 `createMesh/computeTangents` 使用的空 `THREE.Geometry`；15 秒看门狗、错误回调、迟到事件一次性完成。缺失模型仍不可见，**不能把核心赛道几何缺失视为可玩场景**。
- Node 新增 404、解析/转换错误、超时、迟到回调及正常模型回归；Python 65/65、既有 Node 回归通过。Chrome 148 SwiftShader 新增故意 404 `geometries/booster/booster.js` 的真实场景，验证 M2 游戏加载、空几何、重新比赛；完整 **35/35** WebGL 场景通过（约 76 秒），单人测试专用两点预瞄整圈仍为 10,399 帧、0 次路肩修正。
- 仅本地提交 `4a82b99`（文档另交），不推送、不部署、不触碰 `/www/wwwroot/gta.jizhang.org`。下一步检查 `bkcore.ImageData` 的碰撞/高度分析图错误和无响应路径：该资源属于核心物理依赖，不应像可选几何一样静默降级。真实 GPU、人工驾驶、OSM 现场核验、HexGL CC BY-NC 授权风险仍在。


## 2026-11-03：M3 Cityscape 核心分析图故障安全停止

- 开始核对 git status/log 与 WORK_CONTINUITY、ROADMAP、M2-BLOCKOUT、ENGINE；实际起始 HEAD `72a8e30`，工作树干净，本地领先 origin/main 129 提交。未使用旧 ffd16d1 覆盖当前树，未触碰线上 gta.jizhang.org。
- 发现 `bkcore.coffee/ImageData.js` 仅监听 onload，Cityscape 碰撞/高度 PNG 发生 HTTP 404、网络无响应或 Canvas `getImageData` 异常时，不会结束分析图加载。此前加载页可能无限等待；更危险的是不能简单填全零图片，否则会禁用真实碰撞/高度判定。
- 为 ImageData 添加 onerror、15 秒看门狗、空图/Canvas 异常保护、成功/失败一次性回调及 `failed` 标记；同步维护 CoffeeScript 源码。Loader 为 analyser 故障记录 `progress.failed/failures`，仍结算进度以供诊断，但**绝不执行 onLoad/init**；新增 `onFatal` 回调。加载页面显示中文故障信息及重试按钮，避免玩家误以为安全可开车。M2 OSM 赛道不加载 Cityscape 分析图，仍采用独立米坐标碰撞和高度分析器。
- 新增 `tests/analyser-failures.js`：先复现旧实现缺少失败标志/错误回调，再验证正常双图、404、超时、迟到事件、污染 Canvas、短像素缓冲及禁止不安全启动。Node **10 套**、Python **65/65**、JS/Python 语法和 diff 检查通过。
- Chrome 148 SwiftShader 完整回归**未全部通过**：第一轮在第 3 个场景超时，第二轮完成前 27 个场景后在损坏路由回退场景超时，第三轮完成前 **33 个场景**后在天空盒 404 场景超时。共同诊断为页面 readyState=complete、`window.hexGL` 未创建、`progress=null`、无严重浏览器日志；不能把这三轮记作 37/37，也不能断言与本次分析图修复有关。已对测试用 Chrome 加强不同阶段的进程隔离，仍有偶发问题，根因待查。
- 新增独立 `tests/browser_analyser_failures.py`，真实 Chrome 148 SwiftShader **2/2 通过**：分别让 Cityscape 碰撞图/高度图 HTTP 404，确认出现可见致命错误、物理比赛没有启动、资源计数完成，点击重试恢复正常两张分析图并成功进入比赛。这个专项验证不等于完整 37 场景回归。
- 真实 GPU、人工完整驾驶、OSM 现场道路/桥梁复核及原 HexGL CC BY-NC 授权冲突仍未解决。

## 2026-11-03：M3 可选贴图与 HUD 图片无响应看门狗

- 本轮开始核对 git status/log 及 WORK_CONTINUITY、ROADMAP、M2-BLOCKOUT、ENGINE；起始 HEAD `03688bf`、工作区干净、领先 origin/main 131 提交，未使用过期 ffd16d1 覆盖现有成果。
- 发现上一轮 `Loader.loadTexture` 和 `Loader.loadImage` 虽已处理 HTTP 404，但在图片请求永久挂起、既不触发 onload 也不触发 onerror 时仍无法推进 `progress.loaded`。新增 Node 失败回归先复现：两个挂起图片的 watchdog 数量为 0，而预期为 2。
- 现在为普通纹理和 HUD 图片各加 15 秒看门狗、单次完成门闩及迟到事件保护；超时分别使用 2×2 白色 Canvas 材质与 192×25 透明 HUD Canvas，保留原错误回调及正常图片路径。`loadImage` 在设置 src 前注册资源状态，避免同步异常时丢失 fallback。
- Node 八套脚本与 Python 65/65、JS 语法和 git diff --check 通过。新增 `tests/browser_visual_timeouts.py`，在 localhost 故意让材质和 HUD 图片 45 秒无响应，Chrome 148 SwiftShader 约 19 秒内完成 15 秒降级、WebGL 启动及重开，专项 **1/1 通过**。完整浏览器回归结果见本节后续验证记录。未修改道路、物理、Three.js r50dev、无关线上 gta.jizhang.org；真实 GPU、人工驾驶、OSM 现场复核、原 HexGL CC BY-NC 许可仍未解决。

- 完整 Chrome 148 SwiftShader WebGL 首轮在第 28 个场景（越界检查点路由回退）启动超时：页面 `readyState=complete`、`window.hexGL` 未创建、`progress=null`、无严重日志；该轮不能记为通过。给 `tests/browser_smoke.py` 增加点击阶段 `error/unhandledrejection` 捕获、WebGL 可用性与菜单事件处理器诊断。第二轮重新执行完整测试 **37/37 通过**（87.53 秒），包含新增前的全部故障回退、单人完整物理圈与双人测试；并不证明偶发 Chrome 初始化问题已经根治。

## 2026-11-03：M3 Cityscape 核心道路几何故障安全停止

- 本轮先核对实际 `git status/log` 与 WORK_CONTINUITY、ROADMAP、M2-BLOCKOUT、ENGINE；起始 HEAD `ecec0d8`，工作树干净、领先 origin/main 133 提交。未使用旧 `ffd16d1` 覆盖现有改动。
- 复现真实缺陷：原 `Loader.loadGeometry` 对所有失败的 r50 JSON 几何都返回空 `THREE.Geometry` 并继续游戏；如果 Cityscape 的 `track.cityscape` 核心道路 404、解析失败、超时或返回零三角形模型，游戏会在道路消失的状态下启动。先新增 `tests/required-geometry.js` 失败断言，确认旧实现未触发 `onFatal`。
- `Cityscape.js` 的低/高画质清单均显式声明 `requiredGeometries: {'track.cityscape': true}`；`Loader` 对此核心道路的缺失、空面/空顶点、超时调用现有 fatal UI，记录失败并继续结算加载进度供诊断，**不执行 onLoad/init**。普通 booster 等可选几何仍可降级为空模型。更新启动错误文案涵盖赛道模型和物理分析图。
- Node 新增 404、HTTP 200 空几何、请求挂起、迟到事件、可选几何正常降级、两种画质资源清单回归；Python **65/65**、Node **11 套**、JS/Python 语法和 `git diff --check` 通过。Chrome 148 SwiftShader 完整 **38/38** 场景通过（103.94 秒），新增真实 Cityscape 道路 404 安全停止、点击重试恢复并正常启动的场景。自动物理一圈为 **10,495 帧 / 9 次路肩修正 / 1,750 条回放采样**（当前默认测试跟随器；不代表人工驾驶）。
- 未修改 OSM 道路、赛车物理、Three.js r50dev、线上 `/www/wwwroot/gta.jizhang.org`；仅本地 Git 提交。浏览器历史偶发 `window.hexGL` 未创建的加载超时仍未定位，**单次 38/38 不证明根治**。真实 GPU/人工驾驶、道路与桥梁现场核验及原 HexGL CC BY-NC 授权冲突仍未解决。
- 主机本轮观察到磁盘约 **93%**、Swap **5.0/5.0GiB**；未擅自清理其他项目文件或调整服务。下一轮继续调查浏览器启动偶发失败与资源压力，并推进驾驶体验/地标精度。运行时 `launch.js` 已长期偏离旧 `launch.coffee`，不要直接重新编译旧 CoffeeScript 覆盖运行时代码。

## 2026-11-03：M3 OSM 静态道路无事件请求的双重超时保护

- 本轮开始核对 git status/log 与 WORK_CONTINUITY、ROADMAP、M2-BLOCKOUT、ENGINE；基线 `63b031c`、工作区干净、本地领先 origin/main 135 提交。实际运行代码优先，不使用用户提示中的旧 ffd16d1 覆盖新工作。
- 发现 `THREE.StaticModelLoader.load` 虽设置 `xhr.timeout=30000`，但没有独立 JS 看门狗；某些浏览器/协议若既不触发 readyState，也不触发 ontimeout/onerror/onabort，`road.json` 会无限等待，无法进入既有 Cityscape 回退。新增 `tests/static-loader-watchdog.js`，在旧实现上先复现 `timers.size===0` 的失败。
- 现在使用 30 秒 `setTimeout` 独立看门狗，与 XHR 原生超时并行；所有成功/失败路径通过单次 `finish()` 清除定时器，晚到 XHR 事件不能重复回退。Node 新专项测试覆盖完全无事件、迟到事件、坏 JSON 和网络故障；原 `tests/regressions.js` VM 同步测试注入假时钟，避免无意义 30 秒等待。
- Chrome 148 SwiftShader 本地 HTTP 故意让 M2 `road.json` 挂起 45 秒，`tests/browser_road_timeout.py` 验证约 **32.8 秒**内自动切换可玩 Cityscape、完整资源计数并成功重开。此专项不等于真实 GPU/手动驾驶验收。
- 未修改 OSM 路线、道路几何、碰撞、氮气、Three.js r50dev、无关线上 `/www/wwwroot/gta.jizhang.org`；未推送远端。偶发 Chrome 初始化超时、真实 GPU/手动驾驶、OSM 现场复核和 HexGL CC BY-NC 许可冲突仍未解决。

- 本轮最终验证：Python **65/65**、Node **12 套**、JS/Python 语法及 diff 检查通过；Chrome 148 SwiftShader 完整 **38/38** 场景一次通过（约 106 秒），包含单人 10,495 帧物理全圈、9 次路肩修正和双人物理竞速。独立道路静默挂起 Chrome 专项 **1/1** 通过。单次完整通过不代表此前偶发 `window.hexGL` 未创建问题已根治。


## 2026-11-03：M3 OSM 路面与物理中心线不匹配时回退

- 本轮开始先核对实际 Git status/log 及 WORK_CONTINUITY、ROADMAP、M2-BLOCKOUT、ENGINE；起始 HEAD 为 `05c80ea`，工作区干净，本地领先远端 137 提交。以当前工作树为准，不使用过期的 `ffd16d1`。
- 发现有效的 HTTP 200 `cmr-static-v1` JSON 不代表是当前赛道的路面：旧 `ChiangMaiMoat.load` 对任意成功构造的静态模型都视为可玩道路。若模型是错误文件或与 `route-data.js` 不匹配，程序化碰撞/检查点仍运行，但可见路面可能缺失或偏移。
- 在进入 M2 资源加载前检查必需的 `race-asphalt` 网格、顶点/三角面数量、中心线坐标和宽度是否与当前路线一致；不符时复用原有完整 Cityscape 回退，而非在不可见道路上启动比赛。该检查遵循当前 `tools/build_moat_blockout.py` 的双顶点道路带生成契约，不修改 OSM 原始数据、碰撞宽度或 Three.js r50dev。
- Node `tests/moat-regressions.js` 新增缺失路面、偏移路面、残缺索引的回退验证，修复前确实失败；Chrome `tests/browser_smoke.py` 新增真实 HTTP 200 错位路面场景。测试结果以本节后续实际验证记录为准。
- 仍需真实 GPU、人工驾驶、OSM 道路与桥梁现场核验；原 HexGL 部分 CC BY-NC 与 MIT/CC0 商用目标的冲突未解决。未触碰线上 `/www/wwwroot/gta.jizhang.org`，本地提交优先，GitHub 推送需实际认证。

- 最终验证：进一步将中心线匹配从稀疏抽样加强为**全部 650 个路线点**，新增第 111 点单点偏移回归。Python 单元测试 **65/65**、Node **12 套**、JS/Python 语法与 diff 检查通过；Chrome 148 + SwiftShader 在修改前后各完成 **39/39** 场景，新增 HTTP 200 错位路面真实回退场景通过。测试专用全圈物理仍为 **10,495 帧 / 9 次路肩修正 / 1,750 回放采样**，不代表人工驾驶或真实 GPU。

## 2026-11-03 · M3 OSM 路面三角拓扑完整性（当前轮）

- 开始时已核对 git status/log 与四份文档；起点 c417d5e，工作区干净、领先远端 139 提交。
- 发现前一轮可见路面校验仅核对 `race-asphalt` 的顶点中点/宽度和三角面总数，未验证索引连接关系；HTTP 200 且所有索引合法的错接三角形仍可跨古城绘制，而实际碰撞保持 OSM 道路。
- `ChiangMaiMoat.validRoadModel` 现逐段验证离线生成器 `strip_mesh` 的两三角索引及最后一段闭环；不符时完整回退 Cityscape。新增 Node 错接/退化面红灯复现和 Chrome HTTP 200 错接道路回归。
- 仅修改道路资产语义校验和测试；没有修改 OSM 6,492.2m 中心线、14m 路宽、碰撞、氮气、Three.js r50dev 或线上 gta.jizhang.org。实机 GPU/人工驾驶/真实路宽/上游许可仍待验收。
- **本轮最终验证**：Node 12 套全部通过、Python 65/65、Chrome 148 SwiftShader **40/40** 完整场景通过（约 116 秒；新增 HTTP 200 错接路面回退）；测试专用 2 点预瞄跟随器单圈 10,399 物理帧/0 次路肩修正/1,734 回放采样。未进行真实 GPU 或人工完整驾驶。

## 2026-11-03 · M3 OSM 路面局部坐标、海拔与截面朝向校验

- 先核对 `git status/log` 和 WORK_CONTINUITY、ROADMAP、M2-BLOCKOUT、ENGINE；实际起点 `0247e00`、工作树干净、领先 origin/main 141 提交。没有使用过时的 `ffd16d1` 或覆盖当前代码。
- 复现新缺陷：`validRoadModel` 虽校验 650 个中心点/宽度和全部三角索引，却未检查 `StaticModelLoader` 后续应用的 `mesh.offset`、路面 Y 高度和道路截面左右顶点的朝向。HTTP 200 的模型可带 `[100,0,0]` 偏移或将单个截面两侧顶点交换，旧校验仍会启动与碰撞路线不一致的比赛。新增 Node 失败回归在修复前确认回退次数为 0。
- 现在路面不接受非零 mesh.offset，按 `build_moat_blockout.py::normal/strip_mesh` 的前后切线计算左右边缘并逐点比较（0.35m 容差），要求路面 Y 接近当前示意模型的 +0.08m（0.25m 容差）。异常时仍通过完整 Cityscape 回退，不启动错位/悬空/反向三角带。此为**当前示意路面生成契约**，后续真实地形起伏须同步升级校验与测试，不能把固定 Y 误当真实海拔。
- Node 12 套、Python 65/65、JS/Python 语法与 diff 检查通过；Chrome 148 SwiftShader 新增 HTTP 200 非零 mesh.offset 回退场景，完整 **41/41** WebGL 场景一次通过（119.64 秒）；测试专用物理单圈 **10,495 帧、9 次路肩修正、1,750 条回放采样**。单次通过不证明偶发初始化超时已根治。未更改 6,492.2m OSM 中心线、14m 游戏路宽、物理、Three.js r50dev 或线上 `/www/wwwroot/gta.jizhang.org`。真实 GPU、人工驾驶、OSM 现场复核、原 HexGL CC BY-NC 与商用/CC0 目标冲突仍待解决。

## 2026-11-03 · M3 重复路面与不可见材质防护

- 本轮先核对实际 Git status/log 及 WORK_CONTINUITY、ROADMAP、M2-BLOCKOUT、ENGINE；起始 HEAD `afd9fce`，工作区干净，领先 origin/main 143 提交；未使用旧 `ffd16d1` 回滚。
- 复现可验证缺陷：原 `validRoadModel` 找到第一份合法 `race-asphalt` 即停止搜索。若 HTTP 200 模型额外包含第二份同名但错位的道路网格，原检查仍放行；若道路材质 `opacity=0`，模型顶点和索引仍合法，实际却可能没有可见的可驾驶路面。新增 Node 失败断言在修复前复现回退次数为 0。
- 现在要求模型数据和 r50 构建的 children 都恰好有一份 `race-asphalt`；道路材质须是生成器 `road` 材质且不透明（禁止 `transparent=true` 或 opacity<0.95）。坏数据统一使用完整 Cityscape 回退，不加载 M2 精简清单。Node 回归覆盖重复网格、透明/错误材质和原有拓扑/偏移保护。
- 仅改加载前道路语义校验与测试，未改 OSM 中心线、14m 游戏路宽、物理/氮气、Three.js r50dev 或线上 `/www/wwwroot/gta.jizhang.org`。后续更换道路材质规范时须同步校验器及测试；实机 GPU、人工驾驶、路桥现场复核、HexGL CC BY-NC 授权风险仍在。
- 最终验证：Python **65/65**、Node **12 套**、JS/Python 语法及 `git diff --check` 通过；Chrome 148 SwiftShader 完整 **43/43** 场景一次通过（134.53 秒），新增重复路面和不透明材质错误两种 HTTP 200 回退。测试专用自动物理单圈 **10,495 帧、9 次路肩修正、1,750 条回放采样**；仍不是人工驾驶或真实 GPU。浏览器历史偶发初始化超时仍未证实根治。

## 2026-11-03 · M3 倒计时氮气输入边沿修复

- 本轮先核对 Git status/log 与 WORK_CONTINUITY、ROADMAP、M2-BLOCKOUT、ENGINE；实际起点 `27f776a`，工作区干净，领先 origin/main 145 提交。未从旧 `ffd16d1` 恢复工作树。
- 可验证缺陷：M2 车辆在倒计时/结算阶段冻结 `ShipControls.update` 时直接 return，绕过 `nitroCheck` 的按键边沿消费。玩家在倒计时长按氮气键或触发一次触摸氮气请求，第一帧比赛可能自动放出氮气。新增 Node 回归在旧实现下先复现 `nitroActive≈1.783s`（预期 0）。
- 冻结分支现在同步 `nitroKeyPrev` 并清空 `nitroRequest`，不改变冻结速度、剩余氮气、原 Cityscape 路径或 Three.js r50dev。松开后比赛期间重新按下仍可正常触发。新增 Node 及真实浏览器场景断言。
- Node 12 套、Python 65/65、JS/Python 语法与 diff 检查已通过。完整 Chrome WebGL 验证见后续记录。真实 GPU、人工完整驾驶、OSM 现场路桥核验、HexGL CC BY-NC 授权冲突仍未解决。未触碰线上 `/www/wwwroot/gta.jizhang.org`。

## 2026-11-03 · M3 OSM 赛道实机渲染过曝修复（当前轮）

- 本轮从最新快照提交 `c173f47` 继续，处理 `?track=moat` 实机全屏发白；未改 OSM 6,492.2m 中心线、14m 路宽、碰撞/氮气、Three.js r50dev 或线上 `/www/wwwroot/gta.jizhang.org`。
- 根因有两处：`StaticModelLoader` 把 `THREE.Color` 实例作为 `MeshPhongMaterial` 构造参数，r50 `setValues()` 再经 `Color.set(Color)` 解析成黑色，导致所有导入路面/立面变黑，只剩默认白色 `ambient` 与强光；同时 CC0 车接入后原 Feisar 助推器 sprite 仍显示，形成巨大白色星芒和蓝色点光污染。
- 现在 `StaticModelLoader` 的 `legacyHex` 直接向材质传数字 `0xRRGGBB`，导入材质默认 `ambient` 降为 `0x222222`；CC0 车加载成功后隐藏 `booster`、`boosterSprite`、`boosterLight`。仅 moat 使用 Bloom `0.35`（Cityscape 保持 `0.8`）和太阳强度 `1.1`（Cityscape 保持 `1.5`），原 Cityscape 画面不变。
- 使用本地无缓存服务器 `:8082` 与内置 Chrome 实测：高画质 `?track=moat&quality=3` 读取到 road `#4a4843`、ambient `#222222`、bloom `0.35`、sun `1.1`，助推器视觉已隐藏；低画质 `?quality=0` 无 Bloom，材质颜色正常。起点和短暂前进截图不再全屏发白或出现白色星芒，控制台无 error。
- 回归：Node **12/12 套**、Python **65/65**、相关 JS `node --check`、`git diff --check` 均通过。内置浏览器验证覆盖起点与短程驾驶，不等同于完整圈速或真实 GPU 验收；真实 GPU、人工完整驾驶、OSM 现场路桥核验、HexGL CC BY-NC 授权冲突仍未解决。

## 2026-11-04 · M3 OSM 地面、树木与 Lanna 路灯（当前轮）

- 本轮从 `6825bcf` 继续，先核对 Git 状态和 WORK_CONTINUITY、ROADMAP、M2-BLOCKOUT、ENGINE；没有回退旧快照，未触碰线上 `/www/wwwroot/gta.jizhang.org`。
- 修复 OSM 场景悬空与空旷问题：新增 `TERRAIN_Y = -0.25` 和 16 km 单面朝上的 `illustrative-ground`。地面只在同时提供 OSM 水体与建筑时生成，`--schematic` 与仅水体模式的原有网格/材质输出保持不变。
- 把临街建筑、四座城门、Wat Chedi Luang 塔基/墙体、急弯警告牌、树干与灯座统一落到 `TERRAIN_Y`；警告牌箭头也随基座下移。地面和道具是游戏示意，不是现场地形、真实树木位置或历史灯具复原。
- 新增原创低模街景：每约 80 m 交替放置一棵树和一盏 Lanna 风格路灯，最终各 **81** 个。道具位于道路外侧约 **10.2 m**，最近净距实测为建筑 **3.60 m**、水体 **16.80 m**、城门 **40.82 m**、警告牌 **10.11 m**；树木缩放 **0.85–1.17**，最大树冠半径约 **2.57 m**。所有位置由离线生成器计算，不声称对应 OSM 树木或市政设施。
- 新材质为地面 `#73775a`、树干 `#6a4b34`、树冠 `#4f7a3e`、灯杆 `#3f332c`、灯罩 `#f0c36b`（`emissive:"#5f3f10"`）。`StaticModelLoader` 现在把材质 `emissive` 转成数字 hex，避免 r50 将 `#RRGGBB` 解析成黑色。
- 重新生成 `assets/tracks/chiangmai-moat/road.json`：**20 materials / 75 meshes / 24,030 triangles**；`route.json` 与 `route-data.js` 内容未变。重复运行生成器后三个文件 SHA256 完全一致，确认结果可复现。
- 测试：完整 Python **68/68**、`node tests/regressions.js` **4 组**、`node --check`、`python -m py_compile`、`git diff --check` 均通过。新增测试覆盖地面朝向/尺寸、OSM 场景门槛、道具数量/材质/网格三角形数、与道路/建筑/水体/城门/警告牌的净距，以及所有基座落地。
- 内置浏览器实机验证：高画质 `?track=moat&quality=3` 与低画质 `?quality=0` 均加载 75 个道路子网格，地面 `#73775a`、Y `-0.25`，灯罩 `#f0c36b` / emissive `#5f3f10`；低画质确认无 Bloom，两个页面 console 无 error。用 canvas `toDataURL` 下载起点、东侧和西侧街景截图，确认地面、树木、路灯和落地建筑可见。浏览器截图 API 因窗口不可见失败，不能等同于完整 Selenium 冒烟、真实 GPU 或人工整圈验收。
- 仍需真实 GPU、人工完整驾驶、OSM 现场道路/桥梁核验，以及完整 `tests/browser_smoke.py` 回归；本机缺少 Selenium，未在本轮运行该套件。原 HexGL CC BY-NC 与 MIT 目标的授权冲突仍未解决。

## 2026-11-04 · M3 暖色清迈古城视觉返工（当前轮）

- 本轮从 `ba2ed7e` 继续，先定位“M3 变丑”的来源：`bkcore/threejs/Shaders.js` 的蓝色六边形 `hexvignette` 在 moat 高/中画质全屏叠加，加上偏冷的环境光/太阳、平面地面、规则锥形树和平屋顶建筑，造成屏幕纹理感与空旷感。未回退上一轮地面/树木/路灯提交，直接在其上返工。
- 暗角：`HexGL.js` 在 moat 且 `quality>0` 时改用 `THREE.ShaderExtras.vignette`（`offset=0.9`、`darkness=0.22`）；Cityscape 保留原 `hexvignette`，低画质保留 screen pass。moat Bloom 维持 `0.35`。
- 光照：`Cityscape.js` moat 分支改为 ambient `0xd2c2ad`、太阳 `0xfff0dc` 强度 `0.95`、暖色补光 `0xffcfa6` 强度 `0.55`、雾 `0xd9b88d` 700–12000m；Cityscape 分支保持原 ambient/太阳/雾。
- 建筑：`build_moat_blockout.py` 为 815 栋建筑加入暖白/赭黄/柚木等顶点色立面、深色勒脚、木檐、窗框与深色窗洞；屋顶改为红瓦攒尖/四坡/截顶四坡低模，超过 14m 的建筑保留平屋顶。38 个建筑网格合计 **100,826 tris**（85,648 立面 + 15,178 屋顶），未增加材质槽。
- 地面与远景：16km 地面改为 64×64 变形网格，中心密、边缘疏，带暖土/草色顶点色；新增两圈共 128 段、512 tris 的低模远山环 `illustrative-horizon-ridges`，与地面共用 `illustrative-ground` 材质。
- 街景：树木改为每约 100m 成组布置，共 **231 棵**；树冠由 3 个低模阔叶球团组成（每棵 72 tris），带三种绿色/暖色顶点色。路灯增至 **109 盏**，保持约 60m 节奏。起点闸门立柱收窄为 `0.9×6×0.9`、横梁 `18.4×0.85×0.75`，颜色改为 `#a87f4a`。
- 材质：road `#504a42`、curb `#b99b79`、water `#3f7b70`、checkpoint `#a87f4a`、ground `#8c845f`、facade `#d8c6a4`、roof `#a3543d`；地面、远山、树冠、立面、屋顶和窗户均通过顶点色乘基色。`StaticModelLoader` 继续把 `colors` 写入 r50 `Face3.vertexColors`。
- 资产：重新生成 `assets/tracks/chiangmai-moat/road.json` 为 **20 materials / 76 meshes / 141,434 triangles**；SHA256 `5dd61db28766fb0d8a7e8e4141971a843c0fe03017ec40f68e44bd0a441e242b`。连续运行生成器两次 SHA256 一致，`route.json` / `route-data.js` 未变。
- 测试：完整 Python **69/69**、`node tests/regressions.js` **4 组**（新增顶点色加载断言）、相关 JS `node --check`、`python -m py_compile`、`git diff --check` 均通过。同步更新建筑三角数/屋顶绕序/顶点色、地标总数/远山，以及地面网格/树木/路灯断言。
- 内置浏览器：高画质 `?track=moat&quality=3` 与低画质 `?quality=0` 均启动到 `step-4`，console 无 error；高画质确认无六边形暗角，窗框/红瓦、成组树木、远山和雾可见；默认 Cityscape 也加载正常并保留原六边形暗角。截图 API 在窗口不可见时失败，改用第二个 canvas `toDataURL` 下载图片验证，不等同于完整 Selenium/真实 GPU/人工整圈验收。
- 仍需真实 GPU、人工完整驾驶、OSM 现场道路/桥梁核验和完整 `tests/browser_smoke.py`；本机缺 Selenium。原 HexGL CC BY-NC 与 MIT 目标的授权冲突仍未解决。
