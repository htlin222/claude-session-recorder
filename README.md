# rsync 教學 Demo（含 explainshell 側欄）

一支 **1920×1080** 的 rsync 教學影片：左側是會「打字 → 執行 → 出結果」的真實終端，
右側是 [explainshell](https://github.com/idank/explainshell) 風格的命令拆解側欄，
配上一條**從頭到尾連續的繁體中文旁白**，字幕以**外掛 `.srt`**（未燒進畫面）提供。

涵蓋 7 個情境，把來源資料夾 `A` 同步到目標 `B`／`C`：
`tree` 認識資料夾 → `-avn` dry-run 預覽 → `-av` 標準同步 → `--delete` 鏡像 →
`--exclude` 排除 → `-z --info=progress2` 壓縮＋進度 → `-avi` itemize 看懂輸出。

## 成品

| 檔案 | 說明 |
| --- | --- |
| `rsync-demo-final.mp4` | 成品影片（1920×1080，終端＋側欄＋旁白） |
| `rsync-demo-final.srt` | 字幕（外掛，播放器自動載入同名檔；**未燒錄**） |
| `rsync-demo.html` | 自帶播放/暫停控制的離線 HTML 播放器 |
| `rsync-demo.mp4` | VHS 原始終端錄影（1200×1080，未加側欄／旁白） |

## 設計重點

- **一條連續旁白**：整支影片只合成一段 edge-tts 語音；終端的打字、`<CR>`、輸出，
  都釘在這段語音的「句子邊界」上（edge-tts 提供每句的真實時間戳）。
- **Hero 命令逐 token 慢打**：關鍵 rsync 指令一個 flag 一個 flag 地打，
  每個 token 打完的瞬間，右側側欄就浮出對應註解（appear-on-type）。
  解說句也依打字順序逐一念出 flag。
- **側欄 = explainshell 風格**：一句話重點橫幅 ＋ 回顯命令（過長自動**換行不縮字**）
  ＋ 每個 token 的彩色註解（綠＝一般、桃＝該段關鍵 flag、紫＝路徑），
  以「顏色＋順序＋短樁」連結，窄欄也不會連線交錯。
- **時間鎖定**：VHS 實際渲染長度與預測會有微小漂移，`compose.py` 量測後用
  `atempo` 把整段語音微調貼合，語音／字幕／畫面共用同一時鐘。

## 文件 `docs/`

這一路的設計決策與踩坑都整理在 docs：

- [`docs/sync-model.md`](docs/sync-model.md) — 旁白與畫面同步模型的演化（J-cut → 連續旁白）
- [`docs/panel-design.md`](docs/panel-design.md) — explainshell 側欄的設計與取捨
- [`docs/lessons-learned.md`](docs/lessons-learned.md) — 環境／VHS／ffmpeg／時間軸的踩坑教訓

## 重新產生

### 需求
- [`vhs`](https://github.com/charmbracelet/vhs)、`ttyd`、`ffmpeg`（需含 libx264）
- GNU `rsync`（系統內建 openrsync 不支援 `--info=progress2`）
- `edge-tts`（zh-TW 語音）、Python 3 ＋ `Pillow`、`tree`

### 步驟
```bash
# 1. 建立 Python venv（側欄繪圖用 Pillow）
uv venv .venv && uv pip install --python .venv/bin/python pillow

# 2. 產生 tape ＋ 旁白 ＋ 時間軸（旁白會以 edge-tts 合成並快取於 audio/）
python3 build.py

# 3. 重設來源／目標資料夾到初始狀態，然後渲染終端
bash setup_dirs.sh && vhs demo.tape          # -> rsync-demo.mp4 (1200x1080)

# 4. 混入 J-cut 旁白（atempo 對齊）
python3 compose.py                            # -> _av.mp4 + subs.srt

# 5. 合成右側 explainshell 側欄（pad 到 1920，單次 overlay）
.venv/bin/python overlay.py                   # -> rsync-demo-final.mp4 + .srt

# 6.（選用）包成離線 HTML 播放器
python3 ~/.claude/skills/agent-demo-recorder/scripts/gen_html.py \
    rsync-demo-final.mp4 -o rsync-demo.html
```

## 檔案

| 檔案 | 角色 |
| --- | --- |
| `build.py` | 唯一真相來源：旁白腳本 `SCRIPT`、場景／面板資料、產生 `demo.tape` ＋ `timeline.json` |
| `setup_dirs.sh` | 建立／重置來源 `A` 與目標 `B` 的初始內容（每次渲染前跑） |
| `demo.tape` | VHS 腳本（由 `build.py` 產生，勿手改） |
| `timeline.json` | 旁白句時間軸 ＋ 每段面板的 token／浮現時刻 |
| `compose.py` | 量測渲染長度 → atempo 對齊旁白 → 混音成 `_av.mp4`，並寫出 `subs.srt` |
| `overlay.py` | 繪製 explainshell 側欄並合成（含命令換行、token 浮現時序） |
| `audio/voice.*` | 快取的連續旁白（mp3 ＋ 逐句 srt） |

### 想改內容
- **旁白措辭／情境**：改 `build.py` 的 `SCRIPT`（`S(...)` 旁白、`R(...)` 命令、
  `CLR(...)` 場景＋面板），刪掉 `audio/voice.*` 重跑 `build.py` 會重新合成。
- **只改面板文案／配色**：改 `build.py` 的 token 註解或 `overlay.py` 的顏色，
  **不需重渲染 VHS**，跑 `overlay.py` 約 10 秒出片。
- **打字節奏**：`build.py` 的 `TOKEN_STEP`（每個 token 前的停頓）。
