# tar 打包教學 · 從建立、列出到解開

**Audience:** 想紮實學會 `tar` 的 macOS / Unix 命令列使用者（初中階）——已經會在終端機裡走動，但還沒把打包、壓縮、解開的完整流程練成肌肉記憶的人。

## Summary

一支以 tool-agnostic 引擎渲染的繁體中文 CLI 教學影片，左側是逐情境執行的 VHS 終端、右側是 explainshell 風格的逐 token 側欄、配上一條連續旁白。內容聚焦 macOS 的 `tar`（bsdtar）可攜旗標，照「建立 → 列出 → 解開」的安全順序，從把整個 `project/` 資料夾打包成封存檔開始，依序示範 `-c`、`-f`、`-v`、`-t`、`-r`、`-z`、`-czf`、`-tzf`、`--exclude`，最後用 `-xzf -C` 把壓縮封存檔還原到指定目錄、驗證內容完整。每個解說句都逐字帶到該情境的關鍵旗標文字，面板 token 隨打字浮現，畫面與旁白同幀對齊。

## Scenes (key · hero command)

| # | Key | Hero command |
| - | --- | ------------ |
| 1 | tar · 把資料夾打包、壓縮、再解開（開場 / 環境巡覽） | `tree project` |
| 2 | -c 建立一個封存檔 | `tar -c -f project.tar project` |
| 3 | -f 指定輸出的封存檔名 | `tar -c -f docs.tar project/docs` |
| 4 | -v 顯示打包過程 | `tar -c -v -f project.tar project` |
| 5 | -t 列出封存檔內容（不解開） | `tar -t -f project.tar` |
| 6 | -r 把檔案追加進既有封存檔 | `tar -r -f project.tar notes.txt` |
| 7 | -z 邊打包邊用 gzip 壓縮 | `tar -c -z -f project.tar.gz project` |
| 8 | -czf 把常用旗標併成一串 | `tar -czf project.tgz project` |
| 9 | -tzf 列出壓縮封存檔的內容 | `tar -tzf project.tgz` |
| 10 | --exclude 打包時排除不要的檔 | `tar -czf clean.tgz --exclude='*.log' project` |
| 11 | -xzf -C 解開到指定目錄 | `tar -xzf project.tgz -C restored` |

## Duration

286.32s（約 4 分 46 秒）。

## A/V sync

sync verified (PASS) — J-cut on 10/10 transitions, mean 0.35s; min gap 0.998s; 0 voice overruns.

## Provenance

`tar/build/` holds the frozen record of this exact render: timeline/sync/jcut
reports (`timeline.json`, `sync_report.json`, `jcut_report.json`), the 5-gate
verdict (`verify.json`), a config snapshot (`config.toml`), the raw terminal
render (`terminal.mp4`) plus synthesized narration (`narration.mp3`), the lesson
source (`lesson/lesson.py` + `lesson/setup.sh`), the VHS tape (`demo.tape`) and
the build log (`build.log`). `clip/intermediate/` is SHARED scratch the next
build overwrites, so this snapshot is what keeps the clip reproducible.
`build/PROVENANCE.md` explains how to re-composite the final MP4 from these
artifacts without re-running vhs.

## Canonical source & full rebuild

The canonical source lesson lives in `clip/lessons/tar/`. A full rebuild is:

```bash
( cd clip && LESSON=tar python3 src/build.py && LESSON=tar bash src/setup_dirs.sh ) \
  && ( cd clip/intermediate && vhs demo.tape ) \
  && ( cd clip && .venv/bin/python src/overlay.py )
```
