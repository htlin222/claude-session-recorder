# clips — rsync 教學影片（自包含）

一支 1920×1080 教學影片：左側 VHS 終端跑 rsync 7 個情境，右側 explainshell 風格
側欄（編號 + 命令逐 token 拆解，隨打字浮現），一條連續繁中旁白，場景間 1s 定格 +
crossfade，開場 dissolve、結尾淡出，字幕外掛。一切都在這個資料夾裡。

## 結構

```
clips/
  config.toml        # 旋鈕：語音、尺寸、時間、配色（build.py / overlay.py 會讀）
  CLAUDE.md          # 本檔
  src/               # pipeline
    build.py         # 唯一內容來源：SCRIPT(旁白+命令+面板) → 旁白合成 + demo.tape + timeline.json
    overlay.py       # 合成側欄、場景轉場、開場/結尾淡出、輸出 dist/
    compose.py       # legacy：只在 clear 偵測失敗的 fallback 用到（正常流程不需要）
    setup_dirs.sh    # 建/重置來源 A 與目標 B（每次渲染前跑）
  intermediate/      # 產生物：demo.tape / timeline.json / audio/voice.* / rsync-demo.mp4 / A,B,C / _* (皆可再生)
  dist/              # 成品：rsync-demo-final.mp4 (+ .srt 外掛字幕) / rsync-demo.html
  context/           # 設計與踩坑筆記
    sync-model.md      旁白↔畫面同步模型演化
    panel-design.md    側欄設計取捨
    lessons-learned.md 環境/VHS/ffmpeg/時間軸踩坑（含 TS 校準、清屏偵測等關鍵）
```

## 需求
`vhs`、`ttyd`、`ffmpeg`(含 libx264)、GNU `rsync`(非系統 openrsync)、`edge-tts`、`tree`，
Python 3.11+（內建 `tomllib`），側欄繪圖用 `Pillow`+`numpy`。

## 重新產生（從 clips/ 執行）

```bash
# 0) 一次性：建 venv（側欄繪圖）
uv venv .venv && uv pip install --python .venv/bin/python pillow numpy

# 1) 旁白 + tape + 時間軸（旁白以 edge-tts 合成並快取於 intermediate/audio）
python3 src/build.py

# 2) 重置 A/B，渲染終端（從 intermediate 跑，tape 用相對路徑）
bash src/setup_dirs.sh
( cd intermediate && vhs demo.tape )          # -> intermediate/rsync-demo.mp4

# 3) 合成側欄 + 轉場 + 淡入淡出，輸出成品
.venv/bin/python src/overlay.py               # -> dist/rsync-demo-final.mp4 + .srt

# 4)（選用）離線 HTML 播放器
python3 ~/.claude/skills/agent-demo-recorder/scripts/gen_html.py \
    dist/rsync-demo-final.mp4 -o dist/rsync-demo.html
```

字體/尺寸/語音/時間若沒改，可跳過 1–2、只跑 3 重出片（約 40s，不必重渲染 VHS）。

## 要改什麼，改哪裡

- **旁白措辭 / 情境 / 命令 / 面板註解** → `src/build.py` 的 `SCRIPT`（`S()` 旁白、
  `R()` 命令、`CLR()` 場景＋一句話重點＋token 註解）。改完刪 `intermediate/audio/voice.*`
  重跑 build → setup → vhs → overlay。
- **節奏 / 尺寸 / 語音 / 配色** → `config.toml`。只動 config 多半只需重跑 overlay
  （除非改了 render 尺寸或 voice，那要重跑 build + vhs）。
- **面板版面細節**（字號、行高、padding、CMD_Y…）→ `src/overlay.py` 頂部常數。

## 同步是怎麼鎖住的（重點，細節見 context/）

- VHS `Set TypingSpeed 45ms` 實際打字 ~24ms/char → `config.timing.ts=0.024` 校準，
  預測時鐘逐點貼合實際。
- 從 `intermediate/rsync-demo.mp4` **偵測每次清屏的真實幀**（`overlay.detect_clears`），
  把面板場景釘在那一幀 → 左右同幀切換。
- 視訊在清屏前 `safety` 收（定格停在最後輸出、非空白）；音訊按**句界**切，每段旁白
  重錨到場景起點，所以不會切在句中。
- 結尾留靜音尾再淡出，旁白不會被切。
