# OSM 清迈古城外圈道路数据：来源、提取与限制

采集日期：2026-10-31（UTC）  
当前状态：**真实 OSM 道路中心线已导入 M2 原型；道路宽度与检查点门框仍为游戏示意；护城河水面已采用 OSM 水体多边形；未经现场及实体 GPU 验收。**

## 数据来源与许可

- 数据提供方：© OpenStreetMap contributors。
- 许可：Open Database License (ODbL) 1.0；数据衍生物须按 ODbL 的条件使用和分享。
- 官方 API： https://www.openstreetmap.org/api/0.6/map?bbox=98.977,18.780,98.994,18.797
- 许可和署名： https://www.openstreetmap.org/copyright
- 请求时间：2026-10-31 UTC；边界经纬度：west 98.977、south 18.780、east 98.994、north 18.797。
- 原始 XML 大小：10,955,870 字节；SHA-256：63cda4fd16cdc4c20421f68de0055538b2fd104d4c9d3a0a8f5239324b4b8934。
- 原始 XML 暂存服务器 /tmp/chiang-mai-racer-osm-20261031.xml，未提交 Git；上游数据会更新，日后重新下载得到的 SHA 可能不同。

## 提取方式

使用 tools/osm_outer_ring.py 离线读取 OSM API XML。脚本只接受 highway=secondary、带明确 oneway 标签、且属于外环的道路；按 OSM 节点 ID 真实连通，**不跨断点补直线**。路线依次经过：

1. Kotchasarn Road（东侧，南行）。
2. Chang Lo Road（南侧，西行）。
3. Bun Rueang Rit Road（西侧，北行）。
4. Mani Noppharat Road（北侧，东行）。
5. Chayiaphoom Road（东北转角，衔接东侧）。

算法按四个已命名道路的中段节点作为锚点，在有向路网内求最短连接，并以离护城河矩形边界的距离作为路径惩罚。结果经过无自交、单闭环、顺时针、路程长度和几何有效性检查。

本次提取使用 236 个 OSM 路径节点、90 个 OSM way IDs，**原始路线约 6,497.5 m**；约 10 m 间距重采样后为 **6,492.2 m**，650 个点；结合 19 块 OSM 护城河水体多边形后为 4,274 个三角面、5 个合并网格。来源 way ID、道路名称、输入 XML 哈希、提取日期及许可写在 assets/tracks/chiangmai-moat/source-osm.geojson 和 route.json 中。

## 可复现命令

在项目根目录：

    python3 tools/osm_outer_ring.py --osm-xml /tmp/chiang-mai-racer-osm-20261031.xml --out assets/tracks/chiangmai-moat/source-osm.geojson --snapshot-date 2026-10-31
    python3 tools/osm_moat_water.py --osm-xml /tmp/chiang-mai-racer-osm-20261031.xml --out assets/tracks/chiangmai-moat/source-water-osm.geojson --snapshot-date 2026-10-31
    python3 tools/build_moat_blockout.py
    python3 -m unittest discover -s tests -p 'test_*.py' -v
    node tests/moat-regressions.js
    python3 tests/browser_smoke.py

如果没有上述原始 XML，先从官方 API 获取同范围的最新快照，记录新的日期和 SHA；更新后重新运行验证并人工复核道路。不能假设最新快照与本次快照完全相同。

如果要恢复原来的纯尺寸示意版本，请生成到**独立输出目录**，避免覆盖 OSM 默认运行时资产：

    python3 tools/osm_moat_water.py --osm-xml /tmp/chiang-mai-racer-osm-20261031.xml --out assets/tracks/chiangmai-moat/source-water-osm.geojson --snapshot-date 2026-10-31
    python3 tools/build_moat_blockout.py --schematic --out /tmp/chiangmai-schematic-preview

## 仍未解决

- 这是 **OSM 绘制的道路中心线**，不是现场测绘、实拍或真实交通管理核验；单行方向、道路封闭、地理准确度都可能变化。
- 算法自动挑选的路段虽然通过拓扑与单行方向校验，但仍需要人工对照地图逐段核实，尤其东北转角 Chayiaphoom Road。
- 道路被游戏统一扩展到 14 m（不代表真实宽度）；护城河水面来自 19 块 OSM water=moat 多边形，保留原始轮廓，但仍缺现场验证、桥梁/水位/岸墙等细节。
- 四个检查点投影到四座城门附近的路线点，但城门坐标是 OSM 节点近似值，不等于建筑中心或完整古迹范围；城门/城墙是程序化示意，临街建筑和 Wat Chedi Luang 已有 OSM 轮廓驱动的低模 blockout，仍需逐栋和现场核验。
- 已有 Chrome 148 SwiftShader 的无 GPU WebGL 冒烟测试；尚未完成实体 GPU 上的真实手动绕圈、碰撞与帧率验收。
- 原始 HexGL 及其它资产许可应独立核查；不能将 ODbL 道路数据误标为 CC0 或 MIT。

## 发布要求

游戏界面与制作名单必须保留 “Map data © OpenStreetMap contributors (ODbL)” 和官方版权页入口。提供道路数据衍生数据库时遵守 ODbL 的共享、署名和数据库权利条款。地图源数据许可与游戏代码、模型许可是不同的。

## 同一 OSM 快照中的护城河水体（2026-10-31）

- 提取 natural=water + water=moat 且明确闭合的 19 个 OSM way 多边形，按真实 OSM 节点坐标构造水面，不再使用统一 20m 宽度的模拟条带。
- 输入：assets/tracks/chiangmai-moat/source-water-osm.geojson（ODbL，包含 19 个 way IDs、原始 XML SHA、采集日期）；提取器：tools/osm_moat_water.py。
- 离线几何：耳切法将各多边形三角化并合并为单个 water mesh；19 块水体共 230 个三角面，原型总面数从 5,344 降至 4,274。
- 生成器校验道路与水体来自同一 OSM XML SHA；水面三角形法线、面积、凹多边形和错误闭合都有回归测试。没有采用额外的第三方水面资产。
- OSM 水体边界仍不代表实测岸墙/水位；现场核实、桥梁、真实城门和建筑依然待做。


## OSM 四座历史城门坐标（2026-10-31）

同一 XML 快照含 4 个带 historic=city_gate 标签的节点，提取为 assets/tracks/chiangmai-moat/source-gates-osm.geojson（ODbL）：

- Tha Phae Gate：node 1017379824，经纬度 98.9932697, 18.7877625。
- Chiang Mai Gate：node 6107975995，经纬度 98.9889812, 18.7813553。
- Suan Dok Gate：node 6717438786，经纬度 98.9781922, 18.7888357。
- Chang Phueak Gate：node 11229077788，经纬度 98.9865942, 18.7954331。

复现：python3 tools/osm_city_gates.py --osm-xml /tmp/chiang-mai-racer-osm-20261031.xml --out assets/tracks/chiangmai-moat/source-gates-osm.geojson --snapshot-date 2026-10-31

路线检查点现在投影到离每座城门最近的外圈路面中心线点，四座建筑在 OSM 城门坐标处绘制。**程序化低模城门/城墙仅为原创示意几何**；历史建筑外观和精确方位仍待现场/照片复核，不能把坐标精确性误当成建筑三维精度。数据按 ODbL 署名。


## OSM 临街建筑轮廓（2026-10-31）

从同一 SHA-256 已登记的 OSM API XML 中筛选 6,290 条带 building 标签的闭合 way。仅保留距外环道路中心线不超过 80m 的建筑候选，排除靠道路中心线小于 12m 的建筑顶点、距离四座历史城门小于 27m 的建筑顶点，并限制每约 50m 路段最多 10 栋、总量 900 栋。最终 815 栋，来源 way ID 和平面轮廓写入 source-buildings-osm.geojson，保持 ODbL 1.0 署名。原始 OSM 快照没有提供这些建筑的完整三维信息。

39 栋的高度来自 OSM building:levels 标签并按每层约 3.2m 估算（最高截断为 30m）；776 栋没有高度数据，使用可复现的 6.5–10m 游戏示意值。屋顶坡度、红瓦颜色、窗框和立面配色均为原创程序化示意，不可把高度/颜色当作 OSM 实测值或历史街景。生成器按约 350m 路段把立面和屋顶分块合并，共 38 个网格、100,826 个三角面（85,648 立面 + 15,178 屋顶），避免整圈巨型包围盒。加入道路、水体、城门、Wat Chedi Luang、警告牌、变形地面、远山和街景道具后，当前 `road.json` 合计 **20 materials / 76 meshes / 141,434 triangles**；游戏中心虚线位置基于 OSM 衍生的游戏赛道中心线生成，但不代表真实道路标线或官方交通设施。

复现：
    python3 tools/osm_roadside_buildings.py --osm-xml /tmp/chiang-mai-racer-osm-20261031.xml --out assets/tracks/chiangmai-moat/source-buildings-osm.geojson
    python3 tools/build_moat_blockout.py

开发机可复现上述来源，但 XML 不进入仓库；外部贡献者需获取官方 OSM 数据并核对快照 SHA。OSM 建筑轮廓仍需逐栋地图/现场验证，真实 GPU 性能、纹理、遮挡裁剪与历史建筑外观均未验收。


## Wat Chedi Luang 寺院范围与地标 footprint（2026-10-31）

从同一 OSM 官方 API XML 快照提取 4 个闭合 way，生成 assets/tracks/chiangmai-moat/source-wat-chedi-luang-osm.geojson：

- way 243018795：Wat Chedi Luang 寺院范围（amenity=place_of_worship）。
- way 93413945：Wat Chedi Luang Stupa（man_made=stupa、historic=ruins、tourism=attraction）。
- way 93413944：Pra Wihan Luang（building=yes、historic=yes）。
- way 441418807：Ho Inthakhin City Pillar Shrine（amenity=place_of_worship、building=yes）。

源文件的 snapshot_sha256 必须与 route.json 中 osm_snapshot_sha256 完全一致；提取器会拒绝混用快照、缺失 way、关键 OSM tags 变化、开口多边形和落在寺院范围外的子建筑。原始 OSM XML 仍不进入仓库，外部复现者需从官方 API 获取对应范围数据并核对 SHA。

复现：

    python3 tools/osm_wat_chedi_luang.py --osm-xml /path/to/chiang-mai-racer-osm.xml --out assets/tracks/chiangmai-moat/source-wat-chedi-luang-osm.geojson --snapshot-date 2026-10-31
    python3 tools/build_moat_blockout.py

**几何精度限制**：OSM 仅提供寺院范围和建筑平面轮廓，没有可靠三维模型、测绘高度或历史形制数据。生成器原创生成 4 张低模网格（古塔阶梯体、塔基支座、主殿/城柱庙墙体、屋顶），约 230 triangles。古塔视觉高度 38.4m、屋顶、墙体和颜色均为游戏美术参数，不能称为实测高度、扫描模型或历史建筑精确复原。模型不参与车辆碰撞。

数据与衍生几何按 ODbL 1.0 署名 © OpenStreetMap contributors；游戏代码和原创程序化模型的许可应独立理解，不能把 OSM 数据标为 CC0/MIT。

## M3 程序化地面、远山、树木与路灯（非 OSM 实测）

- 赛道新增一个 16 km × 16 km 的 `illustrative-ground` 变形网格：中心 64×64 格较密，向边缘逐渐变疏，并带暖土/草色顶点色。另有两圈共 128 段的低模远山环 `illustrative-horizon-ridges`，与地面共用材质。它们只是填补天空盒与 OSM 道路/建筑之间视觉空隙的示意地表，没有 DEM、坡度、土地利用、现场地形或真实高程数据。地面只在同时具备 OSM 水体与建筑轮廓时生成，schematic / water-only 路线保持原输出。
- 临街建筑、四座城门、Wat Chedi Luang 塔基/墙体、急弯警告牌、树干和灯座都落到同一 `TERRAIN_Y=-0.25`，避免旧版悬空。该高度是游戏美术参数，不是清迈实测海拔（约 310m）或道路纵断面。
- 新增 **231 棵低模阔叶树**和 **109 盏原创 Lanna 风格路灯**。树木每约 100m 成组布置（每组最多 6 棵、随机选道路一侧），路灯保持约 60m 节奏。放置算法只使用 OSM 路线、水体、建筑和城门作避让约束，并按建筑/水体/城门/警告牌净距筛选；**没有读取任何 OSM 树木、路灯或街道设施位置**，也不代表真实市政设施或历史灯具形制。
- 树木与灯具全部由 `tools/build_moat_blockout.py` 离线生成，使用自有低模几何；树干、树冠、建筑、地面和远山使用顶点色多色调，没有引入外部模型或贴图。灯罩使用 `#f0c36b` 与 emissive `#5f3f10`，属于游戏发光参数，不是实测灯光颜色。
- 当前生成的 `road.json` 为 **20 materials / 76 meshes / 141,434 triangles**；对同一输入重复运行生成器，`road.json`、`route.json`、`route-data.js` 的 SHA256 一致。地面、远山、树木、路灯的可追溯性来自生成器输入快照和回归测试，不代表现场测绘。

## 护城河附近 OSM 桥梁候选清单（2026-10-31）

新增 `tools/osm_bridge_inventory.py`，读取与水体完全相同的官方 OSM XML 快照，只选 `bridge=yes` 且存在 `highway` 的 way，按原始节点坐标和已入库的 19 块护城河水体计算完整道路线段至水多边形边界的最短距离（含穿越/内部线段）。**12m 内仅保留为“候选”**，不等于已证明它跨越护城河。共找到 **13 条候选 way**（含 footway、service、secondary_link），保留 OSM way ID、坐标、道路类型及距水体的距离；另外一些桥梁标签不在此距离内，不能据此推断其不存在。

来源：`assets/tracks/chiangmai-moat/source-bridges-osm.geojson`，许可 ODbL 1.0，`snapshot_sha256` 与道路/水体一致；缺失或混用快照时提取器拒绝处理。复现：

    python3 tools/osm_bridge_inventory.py --osm-xml /tmp/chiang-mai-racer-osm-20261031.xml --water-geojson assets/tracks/chiangmai-moat/source-water-osm.geojson --out assets/tracks/chiangmai-moat/source-bridges-osm.geojson

**尚未生成任何桥梁 3D 模型或碰撞体**；当前 `road.json` 不包含这些桥。需先逐段核实桥梁确实跨水、桥面宽度、行人/车辆通行属性和高程，才可将低模桥梁接入 M3。禁止将 `bridge=yes` 推断为可赛车驶入或历史桥梁准确外观。

### 2026-10-31 桥梁候选几何拓扑复核

在 12m 近水初筛后，将 way 线段按 19 块水体边界交点切分，按区间中点判断水体并集内长度；岸边共线与切点不算穿越。13 条中 7 条两端在水体外、至少两次穿越边界且水体重叠 ≥1m（way IDs：93180450、207166728、238840462、320183152、320364172、331338373、744567075；全部 highway=footway），另外 6 条只具近水证据。GeoJSON 新增 mapped_water_overlap_m、mapped_water_boundary_crossings、topology_status，保留 ODbL 和快照 SHA。

跨越已绘制 OSM 水体不等于实地核实的桥梁；无重叠也不证明现实中没有桥梁。尚缺高程、桥宽及机动车通行证据，不生成 3D 桥梁或可驾驶区域。

## 2026-10-31：桥梁清单识别水体断口附近的机动车道路（待核验）

- 以实际 HEAD `fff6a9f`、干净工作树和四份工程文档为起点。原有桥梁清单仅把 7 条与水体重叠的 footway 识别为跨水候选，忽略了 OSM 水体多边形可能在桥口断开：`bridge=yes` 机动车道路不一定与水面多边形直接相交。
- `tools/osm_bridge_inventory.py` 复用已测试的保守岸墙端部几何识别，计算 13 条候选道路至水体端部中点的整条线段最短距离；对 16m 内且没有水面重叠的机动车 `bridge=yes` 道路标记 `mapped_water_gap_motor_bridge_candidate`，仅用于**人工核查优先级**，不是已确认汽车桥，也不据此添加 3D 模型或碰撞。
- 同一 OSM 快照中 4 条 `secondary_link` 候选：26765842（9.01m）、696726366（5.35m）、698115427（14.80m）、698115429（11.10m）。原 7 条 footway 几何跨水候选不变，另 2 条仍为仅近水。保留 ODbL、OSM way ID、快照 SHA；新的端部距离和分类已写入 `source-bridges-osm.geojson`。
- 这解决的是**候选筛选盲点**，不是实地验证；端部阈值是保守的游戏数据审阅启发式。下一步核对这四条道路的桥面/方向、连接拓扑及是否跨越实际水面，再考虑原创低模。仍需真实 GPU/人工驾驶/HexGL 许可审查。

## 2026-11-01 候选桥梁与赛车中心线几何审计

桥梁候选清单额外与同一快照 SHA 的 source-osm.geojson 交叉验证；route_centerline_distance_m、route_centerline_intersections、route_nearest_segment_index 和 route_alignment_abs_dot 为平面几何衍生量，不是路口、可通行性或实测桥梁证据。机动车候选 4 条均不与赛道中心线直接相交；继续保留 ODbL 署名和现场核验限制。


## 2026-11-01：M3 机动车桥梁通行标签与转弯限制审阅（不改变赛道）

- 基线为 b3b7e35，工作树干净；按本轮实际 Git 状态与同源 OSM XML 继续开发。
- osm_bridge_inventory.py 新增机动车通行标签的保守优先级审阅：motorcar > motor_vehicle > vehicle > access。对 private/no/permit 等限制、destination/customers 等有限通行及未知取值，从离线有向路网 BFS 排除；更具体的机动车标签可覆盖一般 access。没有显式限制的道路仍仅标为 untagged，不代表合法通车。非机动车 highway 标记 not_motor_road。
- 新增 type=restriction 关系审阅：统计原始 OSM XML 的限制关系，按桥梁 way 成员或 via 节点记录附近关系 ID。未实现转向限制约束的 BFS，条件限制与 via way 也仍待进一步核查；没有相邻限制关系不代表实际通行合法。
- 同源快照的 1035 条 MOTOR_ROADS way 中，933 条无机动车通行标签、53 条明确限制、34 条仅有限通行、15 条显式允许；路网 BFS 排除 87 条限制/有限通行 way（本快照没有未知值）。现有快照有 13 个 restriction relations，四条机动车桥候选未直接命中桥 way/via 节点；四条均无明确机动车 access 标签，之前的最短节点边数 2/20、29/2、3/29、19/3 不变。这是候选审阅，不是实体桥梁或实际驾驶权证明。
- 只更新离线桥梁 GeoJSON、Python 测试和文档，不修改 Three.js r50dev、M2 14m 游戏路宽、碰撞、车辆物理、路网或渲染。下一步应实现考虑转弯限制的状态图与现场桥梁核验；真实 GPU/手动驾驶和 HexGL 许可问题仍待解决。
