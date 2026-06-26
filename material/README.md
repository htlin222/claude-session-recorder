# material/ — 餵給 `/clip` 的題材

把你想做成教學影片的素材丟進這個資料夾，然後執行 `/clip`。內容格式不拘，負責設計
lesson 的 agent 會自己消化：

- 一份 man page、`--help` 輸出、官方文件節錄
- 你的筆記、想強調的重點、踩過的坑
- 想教的命令清單、希望出現的情境順序
- 純粹一個工具名稱（例如 `jq`、`git rebase`、`tar`），讓 agent 自己決定情境

也可以**不放檔案**，直接用指示驅動：

```
/clip 教 git 的 rebase 與 cherry-pick，給中階使用者，繁中旁白
```

`/clip <指示>` 的指示會當主題；若同時有 material/ 檔案，指示優先、檔案當補充。

## 產出

`/clip` 跑完後，成品在專案根目錄的 `./<slug>/`（slug 由主題決定，例如 `git-rebase/`）：

```
<slug>/
  <slug>.mp4 / .srt / .html    # 影片 + 外掛字幕 + 離線播放器
  manifest.md                  # 標題/受眾/情境清單/時長/A-V 同步結論
  provenance/                       # 這次 render 的「凍結存證」（provenance）
    timeline.json sync_report.json jcut_report.json   # 同步來源 + 報告
    verify.json                # 五道 gate 的 PASS/FAIL 判決
    config.toml                # 當時用的旋鈕快照
    terminal.mp4 narration.mp3 # 重合成用（不必重跑 vhs）
    demo.tape  lesson/         # tape + lesson 原始碼副本
    build.log  PROVENANCE.md   # 建置紀錄 + 如何從 bundle 重出片
```

目標長度 **5 ± 1 分鐘**，workflow 自動調整情境數直到落在此區間。

### 為什麼有 `provenance/`（工廠 vs 成品）
`clip/` 是**共用工廠**：引擎 + 所有 lesson 原始碼 + **共用且會被覆蓋的** `intermediate/`
暫存 + 預設 `config.toml`。下一支 clip 一 render，`intermediate/` 就被洗掉——所以
`provenance/` 把「這支怎麼做出來的」小而有用的部分凍在成品旁邊，讓每個 `./<slug>/` **自包含、
可重現、可稽核**。重大的可再生暫存（分段、面板 PNG、demo 環境）不複製，靠 `setup.sh`
＋ pipeline 重生。要再生 bundle 由 `clip/src/bundle.py` 負責（Deliver 階段自動跑）。

> 同步沒過也照樣出片，但 `manifest.md` 與 `provenance/verify.json` 會**明確標記**
> `SYNC NOT VERIFIED` 與原因（例如稀疏輸出讓清屏偵測抓錯場景數），讓你發片前先檢查。

## 它怎麼運作（簡述）

`/clip` 是 `.claude/workflows/clip.js` 動態 workflow：它在 `clip/`（render 引擎）底下
新增一支 lesson（`clip/lessons/<slug>/`），用引擎的 pipeline 渲染，再把成品複製到
`./<slug>/`。引擎本身（`clip/`）是共用的，不會因為某支 clip 完成而消失——它是所有 clip
的產線與 lesson 的家。
