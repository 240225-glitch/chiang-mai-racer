$ = (_) -> document.getElementById _

init = (controlType, quality, hud, laps, players, difficulty, godmode) ->
  hexGL = new bkcore.hexgl.HexGL(
    document: document
    width: window.innerWidth
    height: window.innerHeight
    container: $ 'main'
    overlay: $ 'overlay'
    gameover: $ 'step-5'
    quality: quality
    difficulty: difficulty
    laps: [1, 3, 5][laps]
    twoPlayer: players is 1
    hud: hud is 1
    controlType: if players is 1 then 0 else controlType
    godmode: godmode
    track: 'Cityscape'
  )
  window.hexGL=hexGL

  progressbar = $ 'progressbar'
  hexGL.load(
    onLoad: ->
      console.log 'LOADED.'
      hexGL.init()
      $('step-3').style.display = 'none'
      $('step-4').style.display = 'block'
      hexGL.start()
    onError: (s) ->
      console.error "Error loading #{ s }."
    onProgress: (p, t, n) ->
      console.log("LOADED "+t+" : "+n+" ( "+p.loaded+" / "+p.total+" ).")
      progressbar.style.width = "#{ p.loaded / p.total * 100 }%"
  )

u = bkcore.Utils.getURLParameter

defaultControls = if bkcore.Utils.isTouchDevice() then 1 else 0

s = [
  ['controlType', ['键盘', '触摸', '体感控制器',
    '手柄'], defaultControls, defaultControls, '操控：']
  ['quality', ['低', '中', '高', '极高'], 3, 3, '画质：']
  ['hud', ['关', '开'], 1, 1, 'HUD：']
  ['laps', ['1 圈', '3 圈', '5 圈'], 1, 1, '圈数：']
  ['players', ['单人', '双人'], 0, 0, '模式：']
  ['difficulty', ['休闲', '竞技'], 0, 0, '难度：']
  ['godmode', ['关', '开'], 0, 0, '上帝模式：']
]

updateBest = ->
  el = $ 'best'
  return if not el?
  d = s[5][3]
  l = [1, 3, 5][s[3][3]]
  if s[4][3] is 1
    el.innerHTML = "最佳成绩：双人模式不记录 <span>· 同屏对战 · #{l} 圈</span>"
    return
  key = "hexgl-best-Cityscape-#{d}-#{l}"
  val = null
  try
    val = Number localStorage.getItem(key)
  catch e
    val = null
  if val > 0
    t = bkcore.Timer.msToTimeString val
    el.innerHTML = "最佳成绩：#{t.m}'#{t.s}''#{t.ms} <span>· #{s[5][1][d]} · #{l} 圈</span>"
  else
    el.innerHTML = "最佳成绩：暂无记录 <span>· #{s[5][1][d]} · #{l} 圈</span>"

for a in s
  do(a)->
    a[3] = u(a[0]) ? a[2]
    e = $ "s-#{a[0]}"
    (f = -> e.innerHTML = a[4]+a[1][a[3]])()
    e.onclick = ->
      f(a[3] = (a[3]+1)%a[1].length)
      updateBest()
updateBest()

$('step-2').onclick = ->
  $('step-2').style.display = 'none'
  $('step-3').style.display = 'block'
  init s[0][3], s[1][3], s[2][3], s[3][3], s[4][3], s[5][3], s[6][3]

$('go-restart').onclick = ->
  if window.hexGL then window.hexGL.restartRace() else window.location.reload()
$('go-menu').onclick = ->
  window.location.reload()
$('pause-resume').onclick = ->
  window.hexGL.resume() if window.hexGL
$('pause-restart').onclick = ->
  window.hexGL.restartRace() if window.hexGL
$('pause-menu').onclick = ->
  window.location.reload()
$('nitro-panel').onclick = ->
  if window.hexGL?.components.shipControls
    window.hexGL.components.shipControls.triggerNitro()
$('nitro-panel-p2').onclick = ->
  if window.hexGL?.components.shipControls2
    window.hexGL.components.shipControls2.triggerNitro()

$('s-credits').onclick = ->
  $('step-1').style.display = 'none'
  $('credits').style.display = 'block'
$('credits').onclick = ->
  $('step-1').style.display = 'block'
  $('credits').style.display = 'none'

hasWebGL = ->
  gl = null
  canvas = document.createElement('canvas');
  try
    gl = canvas.getContext("webgl")
  if not gl?
    try
      gl = canvas.getContext("experimental-webgl")
  return gl?

if not hasWebGL()
  getWebGL = $('start')
  getWebGL.innerHTML = '当前浏览器不支持 WebGL'
  getWebGL.onclick = ->
    window.location.href = 'http://get.webgl.org/'
else
  $('start').onclick = ->
    $('step-1').style.display = 'none'
    $('step-2').style.display = 'block'
    if s[4][3] is 1
      $('step-2').style.backgroundImage = 'none'
      $('step-2').innerHTML = '<div id="help-vs"><div class="help-title">双人同屏对战</div><div class="help-cols"><div class="help-col"><b>玩家 1</b><span>W / S 加速 · 刹车</span><span>A / D 转向</span><span>Q / E 空气刹车</span><span>左 Shift 氮气</span></div><div class="help-col"><b>玩家 2</b><span>↑ / ↓ 加速 · 刹车</span><span>← / → 转向</span><span>空格 氮气</span></div></div><div class="help-note">率先完成选定圈数者获胜</div><div id="ctrl-help">点击继续</div></div>'
    else
      $('step-2').innerHTML = '<div id="ctrl-help">点击继续</div>'
      $('step-2').style.backgroundImage = "url(css/help-#{s[0][3]}.png)"
