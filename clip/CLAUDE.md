# clip — CLI 教學影片產生器（lesson 驅動、tool-agnostic）

一個產生 1920×1080 CLI 教學影片的小框架：左側 VHS 終端逐情境跑命令，右側
explainshell 風格側欄（編號 + 命令逐 token 拆解，隨打字浮現），一條連續繁中旁白，
場景間 1s 定格 + crossfade，開場 dissolve、結尾淡出，字幕外掛。

**內容與引擎分離**：每支影片只是一個 **lesson**（`lessons/<name>/`），裡面放旁白、
命令、面板註解、環境 setup；`src/` 的引擎完全不認得 rsync 或任何特定工具。要教別的
CLI 工具就寫一支新 lesson，引擎不用動。內建兩支：`rsync` 與 `find`。

## 結構

```
clip/
  config.toml          # 旋鈕：[lesson].active 選 lesson；語音/尺寸/時間/配色
  CLAUDE.md            # 本檔
  src/                 # tool-agnostic 引擎
    lesson.py          # lesson 契約：S()/R()/CLR() 三個 builder + load() 載入器
    build.py           # active lesson 的 SCRIPT → 旁白合成 + demo.tape + timeline.json
    overlay.py         # 合成側欄、場景轉場（含轉場 J-cut）、開場/結尾淡出；依 slug 命名
    verify_sync.py     # 畫音同步的可測訊號：結構同步/旁白沒切/時長/J-cut，可自癒 desync
    bundle.py          # 把一次 render 的 provenance 凍進 <slug>/provenance/（intermediate 會被覆蓋）
    envcheck.py        # 確定性環境探測：工具在不在、是 GNU 還是 BSD/variant、有沒有 g* 替代
    setup_dirs.sh      # dispatcher：讀 config 的 active，跑該 lesson 的 setup.sh
    compose.py         # legacy：只在 clear 偵測失敗的 fallback 用到
  lessons/             # 內容（要改的都在這）
    rsync/
      lesson.py        # SLUG/TITLE + SCRIPT（旁白＋命令＋面板）
      setup.sh         # 建/重置這支 lesson 的環境（來源 A、目標 B、暫存 C）
    find/
      lesson.py        # 第二支範例：用述詞在 proj/ 樹裡定位檔案
      setup.sh         # 建/重置 proj/ 範例樹（含 -size/-mtime 的刻意佈置）
  intermediate/<slug>/ # 每個 lesson 各自的工作區（並行安全）：terminal.mp4 / demo.tape /
                       #   timeline.json / audio/ / demo env(A,B,C,proj…) / _*（皆可再生）
  dist/                # 成品：<slug>.mp4 (+ <slug>.srt 外掛字幕 / <slug>.html)，逐 lesson 累積
  context/             # 設計與踩坑筆記（sync-model / panel-design / lessons-learned）
```

## 需求
`vhs`、`ttyd`、`ffmpeg`(含 libx264)、要教的 CLI 工具本身（rsync 需 GNU `rsync`，非系統
openrsync）、`edge-tts`、`tree`，Python 3.11+（內建 `tomllib`），側欄繪圖用
`Pillow`+`numpy`。

## 選 lesson

`config.toml` 的 `[lesson] active = "rsync"`（或 `"find"`，或你新增的）。也可以用環境
變數 `LESSON=<slug>` 臨時覆寫（優先於 config，不必改檔）——`build.py` 與
`setup_dirs.sh` 都認得，root 的 `/clip` workflow 就靠它鎖定單一 slug。輸出檔名依
lesson 的 `SLUG`：`dist/rsync.mp4`、`dist/find.mp4`…，所以 `dist/` 會逐支累積成品。
每支 lesson 的暫存放在**自己的** `intermediate/<slug>/`（terminal.mp4 / demo.tape /
timeline.json / audio / demo env 全在裡面），所以多支可以**同時並行渲染**互不干擾，
也不會像舊版共用 `intermediate/` 那樣被下一支覆蓋。

> 這個 `clip/` 是**共用 render 引擎**。專案根目錄的 `/clip` 動態 workflow
> （`.claude/workflows/clip.js`）會讀 `material/` 或 `/clip <指示>`，在此新增一支
> lesson、用本 pipeline 渲染，再把成品複製到根目錄的 `./<slug>/`。引擎不會因為某支
> clip 完成而消失。

## 重新產生（從 clip/ 執行）

```bash
# 0) 一次性：建 venv（側欄繪圖）
uv venv .venv && uv pip install --python .venv/bin/python pillow numpy

# 1) 旁白 + tape + 時間軸（寫到 intermediate/<active>/，旁白快取 audio/）
python3 src/build.py

# 2) 重置環境 + 渲染終端（工作區 = intermediate/<active>/，可多 slug 並行）
bash src/setup_dirs.sh                          # → intermediate/<active>/ 的 demo env
( cd intermediate/<active> && vhs demo.tape )   # → intermediate/<active>/terminal.mp4
# （明確指定或並行時，每步前面加 LESSON=<slug>，例如 LESSON=jq python3 src/build.py …）

# 3) 合成側欄 + 轉場 + 淡入淡出，輸出成品（檔名依 slug）
.venv/bin/python src/overlay.py                # → dist/<slug>.mp4 + .srt

# 4)（選用）離線 HTML 播放器
python3 ~/.claude/skills/agent-demo-recorder/scripts/gen_html.py \
    dist/<slug>.mp4 -o dist/<slug>.html
```

字體/尺寸/語音/時間若沒改，可跳過 1–2、只跑 3 重出片（約 40s，不必重渲染 VHS）。

## 要改什麼，改哪裡

- **某支 lesson 的旁白 / 情境 / 命令 / 面板註解** → `lessons/<name>/lesson.py` 的
  `SCRIPT`（`S()` 旁白、`R()` 命令、`CLR()` 場景＋一句話重點＋token 註解）。改完刪
  `intermediate/audio/<slug>.*` 重跑 build → setup → vhs → overlay。
- **某支 lesson 的命令環境**（資料夾/檔案）→ `lessons/<name>/setup.sh`。
- **新增一支 lesson** → 建 `lessons/<新名>/`，寫 `lesson.py`（定義 `SLUG`、`TITLE`、
  `SCRIPT`，並 `from lesson import S, R, CLR`）與 `setup.sh`（建環境到 `intermediate/`），
  再把 `config.toml` 的 `active` 指過去。引擎不用改。
- **節奏 / 尺寸 / 語音 / 配色**（所有 lesson 共用）→ `config.toml`。只動 config 多半
  只需重跑 overlay（除非改了 render 尺寸或 voice，那要重跑 build + vhs）。
- **面板版面細節**（字號、行高、padding、CMD_Y…）→ `src/overlay.py` 頂部常數。

面板 token 的三種 role（顏色，見 `overlay.ROLE`，跨工具通用）：
`ord`＝一般旗標（綠）、`star`＝該情境的關鍵旗標（桃）、`path`＝運算元/路徑/參數（紫）。
旁白的解說句要**逐字帶到** star/ord 的旗標文字，token 才會貼著打字浮現（見下）。

## 同步是怎麼鎖住的（重點，細節見 context/）

- VHS `Set TypingSpeed 45ms` 實際打字 ~24ms/char → `config.timing.ts=0.024` 校準，
  預測時鐘逐點貼合實際。
- 從 `intermediate/terminal.mp4` **偵測每次清屏的真實幀**（`overlay.detect_clears`），
  把面板場景釘在那一幀 → 左右同幀切換。**稀疏輸出**（如 `fzf -f` 只印幾行）會讓畫面
  中途掉到近空、被誤判成多次清屏（fzf 實測偵到 24 次、實際 13 段）。所以盲偵測數量不對
  時，會改用 **guided**：用各場景的預測清屏時刻，挑出最接近的 N 個落點（忽略場景中途的
  假掉落），數量保證正確。仍對不上才 fallback 回無轉場版。
- 視訊在清屏前 `safety` 收（定格停在最後輸出、非空白）；音訊按**句界**切，每段旁白
  重錨到場景起點，所以不會切在句中。
- 結尾留靜音尾再淡出，旁白不會被切。
- **每幕定格自適應**：每一幕的結尾定格撐到「自己的旁白講完 + `hold`」才轉場
  （`end_pad = max(0, delays+A−L) + hold + xfade`），所以一幕的旁白**絕不會溢出**到下一幕。
- **轉場 J-cut**：下一幕引入句提前 ~0.35s 進到那段靜默定格上（只動音軌，畫面仍釘清屏幀）。
  lead 自適應 = `min(jcut_lead, gap−jcut_guard)`；因為 gap 一定 ≥ `hold`，通常給滿 0.35s。

## 畫音同步是可驗的（loop engineering）

`src/verify_sync.py` 把同步變成 PASS/FAIL 訊號（exit code），渲染後跑：
```bash
.venv/bin/python src/verify_sync.py --slug <slug> --target-sec 300 --tol-sec 60
```
它 gate 五件事：結構同步（每幕釘到真實清屏）、旁白沒被切、時長 5±1 分、J-cut 沒蓋過舊旁白
（`jcut_clips`）、舊旁白沒溢出到新畫面（`voice_overruns`，看 `min_gap_sec`）。
desync 時會掃 threshold 還原 count-correct clears 寫 `clears_override.json`，再跑一次
`overlay.py` 就自癒（不必重渲染 vhs）。`/clip` workflow 的 Verify phase 已把這條包成有界迴圈。
