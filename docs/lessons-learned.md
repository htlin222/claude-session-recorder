# 技術踩坑與教訓

這支 demo 從零做到「終端錄影 + explainshell 側欄 + 連續旁白 + 外掛字幕」，
過程踩到不少坑。這份記錄「非顯而易見」的部分，給下次自己／別人省時間。

## 環境 / 工具

### macOS 內建的是 openrsync，不是 GNU rsync
`/usr/bin/rsync` 在新版 macOS 是 **openrsync**（`rsync version 2.6.9 compatible`），
**不支援** `--info=progress2`、itemize 的某些輸出格式等 GNU 專屬選項。
教學影片要用大家熟悉的 GNU 行為 → `brew install rsync`（3.4.4），
並確認 `which -a rsync` 時 `/opt/homebrew/bin/rsync` 排在 `/usr/bin` 前面。

### 這台的 ffmpeg 沒有 libass / freetype / drawtext
`brew` 的 ffmpeg（8.0.1）是精簡 build，**沒有 `subtitles`、`ass`、`drawtext` 濾鏡**。
→ 沒辦法用 `-vf subtitles=...` 燒字幕，也不能用 drawtext 畫字。
解法：**用 Pillow 把文字（字幕／側欄）畫成 PNG，再用 `overlay` 濾鏡合成**。
overlay / libx264 / aac 都有，足夠。（`ffmpeg` 還被 alias 成 `ffmpeg-bar`，
script 裡一律用絕對路徑 `/opt/homebrew/bin/ffmpeg` 避開 alias。）

### zsh 互動模式預設不把 `#` 當註解
tape 裡想打一行 `# 說明` 當畫面提示，結果終端噴 `zsh: command not found: #`。
zsh 互動 shell 預設沒開 `interactive_comments`。
解法：tape 開頭用 VHS `Hide` 偷偷 `setopt interactive_comments`（不入鏡、不佔時間軸）。

## VHS

### Font/Width 不影響時間軸，只影響畫面
改 `Set FontSize` / `Set Width` **不會**改變 tape 的時長（時長只由 `Sleep` ＋
`TypingSpeed` 決定）。所以為了「字大一點 / 改尺寸」重渲染，旁白時間軸完全不用動，
既有的 `_av.mp4`（混音）若尺寸沒變還能續用。

### `Hide` / `Show` 不佔錄製時間
被 `Hide` 包起來的指令照常執行，但不錄進影片，也不佔錄製時間軸。
拿來做「每段開頭清屏」「開 interactive_comments」很乾淨——畫面零閃爍、計時零誤差。

### VHS 只能等畫面上的字串（agent demo 才需要）
這支是純 shell 指令（確定性），用 `Sleep` 控時即可，
不需要 agent-demo-recorder 那套 Stop-hook sentinel。

## 字幕 / 旁白時間

### edge-tts 的 `--write-subtitles` 給「逐句真實時間戳」
edge-tts 會依 word-boundary 把旁白切成**逐句** SRT（在 `。！？` 斷句，逗號不斷）。
這是整個同步的基石：知道每句話結束的真實秒數，就能把「打字 / 執行 / 出結果」
釘在語音的句界上。**前提**：腳本每句結尾要有 `。`，句中別出現 `。`，
否則 edge-tts 切出的 cue 數會跟你的句子數對不上（build.py 有 assert 擋）。

### 預測時間 vs 實際渲染：用 atempo 線性校正
tape 的事件時刻是「預測時鐘」算出來的；VHS 實際渲染因打字／取整有漂移。
解法：`compose.py` 量測實際長度算 `scale`，用 `atempo=1/scale`（聽不出）
把整段語音微調貼合畫面；字幕時間戳也乘同一個 `scale`。三者共用同一時鐘。

### ⚠️ `Set TypingSpeed 45ms` 的實際打字是 ~24ms/char（關鍵！）
最初預測 140.7s、實際只有 135.5s，差 5s。拆開 tape 一算：
**非隱藏 Sleep 總和 129.35s（精確）+ 打字 252 字**。反推實際打字速度
= (135.5 − 129.35) / 252 = **24.4ms/char**，是設定值 45ms 的一半。
VHS 的 `Set TypingSpeed` 不等於每字實際耗時。
- 把模型 `TS` 校準成 **0.024** 後，預測時鐘**逐點**貼合實際（scale 0.96→**1.00**）。
- 這才是「deterministic、follow the tape sec」的本質：Sleep 精確、打字校準，
  整條時間軸就能直接拿來放面板浮現，不用線性 scale 硬拉。
- `Set TypingSpeed` 仍保 45ms（那是「產生 24ms 實際」的已知設定），別從 TS 反推。

### 面板浮現要跟「語音」走，不是跟「固定節拍」走
hero 命令若用固定 `TOKEN_STEP` 打字，token 會擠在解釋句前半段浮現完，
但語音是把 flag 鋪在整句念——後段就「語音還在講、面板早切完」。
解法：在解釋句文字裡找每個 flag 的**字元位置**，映射到 cue 內的時間，
讓打字／面板浮現**鋪滿整句、落在語音念到該 flag 的時刻**。

### 終端（真實）vs 面板（預測）切場景會差一點
終端是 VHS 實錄、面板是預測時鐘合成，scene 切換時終端常**略快**。
給面板一個小的全域提前量（`PANEL_LEAD ≈ 0.15s`）補償即可。

## ffmpeg 合成效能

### 別堆幾十個 overlay 濾鏡
最初把每個面板狀態 / 每句字幕都當一個 `overlay=...:enable='between(t,..)'`，
71 個 overlay 疊在 140s 影片上逐幀合成 → **每道好幾分鐘**。
解法：**先把每一層壓成一條影片**（concat demuxer：一張圖配一段時長），
再單次 overlay。面板壓成 `_panel.mp4`、字幕壓成帶 alpha 的影片，
總共剩 2 個 overlay → **整段合成 ~12 秒**。可快速迭代。

```bash
# concat demuxer：每張圖顯示指定秒數
ffmpeg -f concat -safe 0 -i list.txt -r 25 -c:v libx264 ... panel.mp4
# list.txt:  file 'x.png'\nduration 1.2\n ...  最後一張要再 file 一次（concat 怪癖）
```

### filtergraph 裡 `force_style` 的逗號會被當分隔符
（這次最後沒用到，但記著）`subtitles=...:force_style=A,B,C` 的逗號會被
filtergraph parser 當濾鏡分隔，要 `\,` 轉義。

## 其他

- **路徑相對化**：script 用 `os.path.dirname(os.path.abspath(__file__))` 當專案根，
  搬目錄（如 `/tmp/...` → `~/vhs-demo`）才不會壞。
- **Pillow 連接線在窄欄會交錯**：見 [panel-design.md](panel-design.md)。
- **`rip` 不吃某些批量參數**：清檔時 `rip audio/s[1-7]_*` 這種 glob 可以，
  但 `rip $(ls|grep..)` 噴 usage——展開成太多/含特殊參數。
