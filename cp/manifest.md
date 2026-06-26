# cp 教學 · 在命令列複製檔案與目錄（macOS BSD cp）

**Audience**: macOS 命令列初學者 — 想學會用 `cp` 複製檔案與目錄、看懂常用旗標（`-r`/`-p`/`-n`/`-v`/`-a`），並理解 BSD `cp` 與 GNU 版本差異的人。範例以 `gcp`（GNU coreutils）示範，於介紹中點出 BSD/GNU 分歧。

## Summary

一支 1920×1080、約五分鐘的教學影片：左半邊是 VHS 終端機逐字輸入並執行 `cp` 相關指令，右半邊是 explainshell 式的面板，逐 token 拆解每一條指令；搭配一條連續的 zh-TW 旁白、J-cut 場景轉場與外掛 `.srt` 字幕。內容從「進入範例資料夾、看清楚有哪些檔案」開始，循序帶過 `cp` 最基本的「來源→目的」用法、複製進目錄、一次複製多個檔案，再逐一示範 `-r` 遞迴、`-p` 保留中介資料、`-n` 不覆蓋、`-v` 詳細輸出、合併短旗標 `-rv`、`-a` 封存模式，最後用 `tree` 檢視複製成果。

## Scenes

| # | key | hero command |
|---|-----|--------------|
| 1 | cp · 在命令列複製檔案與目錄（intro 標題） | — |
| 2 | 先進到範例資料夾，看看裡面有哪些檔案 | `gls -l` |
| 3 | 最基本的用法：cp 來源 目的 | `gcp a.txt copy.txt` |
| 4 | 目的地是目錄：結尾加斜線複製進去 | `gcp report.txt backup/` |
| 5 | 一次把多個檔案複製進同一個目錄 | `gcp a.txt b.txt backup/` |
| 6 | -r：遞迴複製整個目錄 | `gcp -r docs docs-backup` |
| 7 | -p：保留權限、擁有者與時間戳 | `gcp -p stamped.txt kept.txt` |
| 8 | -n：不覆蓋已經存在的檔案 | `gcp -n a.txt copy.txt` |
| 9 | -v：印出每一步複製動作 | `gcp -v notes.txt copied.txt` |
| 10 | 短旗標可以合併：-rv | `gcp -rv docs docs-v` |
| 11 | -a：封存模式，完整保留一切 | `gcp -a docs archive` |
| 12 | 用 tree 檢視最後的複製成果 | `tree -L 1` |

## Duration

Final: **292.68s** (terminal 265.52s · narration 277.80s ≤ final · target 300s ±60s, on-target).

## A/V sync

sync verified (PASS) — J-cut on 11/11 transitions, mean 0.35s; min gap 0.993s; 0 voice overruns.

## Provenance

`cp/provenance/` holds the frozen record of this render — `verify.json` (the 5 gates: structural sync, narration-not-cut, duration, J-cut clips, voice overruns), the `timeline.json` / `sync_report.json` / `jcut_report.json` reports, a `config.toml` snapshot, the `terminal.mp4` + `narration.mp3` source artifacts, a copy of `lesson/` (`lesson.py` + `setup.sh`), `build.log`, and `PROVENANCE.md` (human index + how to re-composite without re-running vhs). This folder is **self-contained & portable** — move it anywhere and it still builds; its own `CLAUDE.md` documents how to rebuild:

```bash
cd cp && python3 src/build.py && bash setup.sh && ( cd intermediate && vhs demo.tape ) && .venv/bin/python src/overlay.py
```
