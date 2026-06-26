# df 教學 · 在命令列查看磁碟空間還剩多少

**Audience**: 中文（zh-TW）終端機使用者 — 初學到中階，想學會在命令列查看磁碟空間，
並理解 `df` 各旗標含義，以及 macOS BSD `df` 與 Linux/GNU `df`（此處用 `gdf`）的差異。

## Summary

一支 1920×1080 的教學影片：左側是 VHS 終端機逐一輸入並執行 `gdf` 指令，右側是
explainshell 風格的解析面板，把每個指令逐 token 拆解；搭配一段連續的 zh-TW 旁白、
J-cut 場景轉場與外掛 `.srt` 字幕。內容從最樸素的一行 `gdf` 開始，一個旗標一個旗標
帶觀眾把磁碟空間看清楚，並貫穿說明 macOS 內建 BSD `df` 與 Linux/GNU `df` 的差異
（影片全程改用 Homebrew coreutils 的 `gdf` 以對齊 Linux 觀眾所見）。

## Scenes (key · hero command)

| # / 11 | Key | Hero command |
| ------ | --- | ------------ |
| 1 | gdf：列出每個檔案系統，預設以 1K 區塊計數 | `gdf` |
| 2 | -h：人類可讀，用 K/M/G 並以 1024 進位 | `gdf -h` |
| 3 | -H：改用 1000 進位的 SI 單位 | `gdf -H` |
| 4 | -m：所有大小固定用 MB 顯示 | `gdf -m` |
| 5 | -i：改看 inode 用量而非容量 | `gdf -i` |
| 6 | -T：在輸出裡多印一欄檔案系統型別 | `gdf -T -h /` |
| 7 | gdf /：只查一個路徑所在的檔案系統 | `gdf /` |
| 8 | gdf .：目前所在的目錄落在哪顆磁碟 | `gdf .` |
| 9 | -h 與路徑組合：好讀地只看一顆磁碟 | `gdf -h /` |
| 10 | -P：POSIX 可攜格式，欄位固定不換行 | `gdf -P /` |
| 11 | -l：只列出本機的檔案系統 | `gdf -l` |

(A title/intro scene precedes scene 1; the 11 command scenes above are the
structurally-synced clears.)

## Duration

**298s** (≈5 min; terminal 267.12s, narration 283.37s — narration fits within final).

## A/V sync

sync verified (PASS) — J-cut on 11/11 transitions, mean 0.35s; min gap 0.993s; 0 voice overruns.

## Provenance

`df/provenance/` holds the frozen record of this render — `verify.json` (the 5
gates), the timeline/sync/jcut reports, a `config.toml` snapshot, the
`terminal.mp4` + `narration.mp3`, a copy of `lesson.py`/`setup.sh`, `build.log`,
and `PROVENANCE.md` (how to re-composite without re-running vhs). This `df/`
folder is **self-contained & portable** — move it anywhere and it still builds;
its own `CLAUDE.md` documents how to rebuild:

```bash
cd df && python3 src/build.py && bash setup.sh && ( cd intermediate && vhs demo.tape ) && .venv/bin/python src/overlay.py
```
