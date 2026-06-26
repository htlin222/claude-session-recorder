# awk 教學 · 用一行指令切欄位、篩選與彙總資料

**Audience:** 想用一行指令處理欄位式 / 表格資料的 macOS / Unix 命令列使用者（初中階）——已經會在終端機裡走動，會用 `cat`、管線，但還沒把 `awk` 的切欄位、篩選、彙總練成肌肉記憶的人。

## Summary

一支以 tool-agnostic 引擎渲染的繁體中文 CLI 教學影片，左側是逐情境執行的 VHS 終端、右側是 explainshell 風格的逐 token 側欄、配上一條連續旁白。內容聚焦 macOS 內建的 one-true-awk（非 GNU gawk），只用可攜寫法、不含雙引號與反斜線。以一份「名字 / 部門 / 薪水」的員工資料為例，照「切欄位 → 篩選 → 彙總」的順序，依序示範 `print $0`、`$1`、`$1, $3`、`-F`、`NR`、`NF`、`/Eng/` 樣式比對、`$3 > 5000` 數值比較、`END`、`sum += $3` 累加器、`BEGIN`、`-v` 外部變數，最後用 `sum / NR` 算出平均薪水作為總結。每個解說句都逐字帶到該情境的關鍵旗標文字，面板 token 隨打字浮現，畫面與旁白同幀對齊。

## Scenes (key · hero command)

| # | Key | Hero command |
| - | --- | ------------ |
| 1 | awk · 一行指令處理欄位式資料（開場 / 認識資料與流程） | `cat data.txt` / `cat data.csv` |
| 2 | print $0 印出整列 | `cat data.txt \| awk '{print $0}'` |
| 3 | $1 取第一個欄位 | `cat data.txt \| awk '{print $1}'` |
| 4 | $1, $3 一次印多欄 | `cat data.txt \| awk '{print $1, $3}'` |
| 5 | -F 指定欄位分隔符 | `cat data.csv \| awk -F, '{print $2}'` |
| 6 | NR 目前的列號 | `cat data.txt \| awk '{print NR, $1}'` |
| 7 | NF 這一列的欄位數 | `cat data.txt \| awk '{print NF}'` |
| 8 | /Eng/ 樣式比對才動作 | `cat data.txt \| awk '/Eng/{print $1}'` |
| 9 | $3 > 5000 用比較篩選 | `cat data.txt \| awk '$3 > 5000 {print $1, $3}'` |
| 10 | END 收尾時執行一次 | `cat data.txt \| awk 'END{print NR}'` |
| 11 | sum += $3 累加器求總和 | `cat data.txt \| awk '{sum += $3} END{print sum}'` |
| 12 | BEGIN 開頭先做一件事 | `cat data.txt \| awk 'BEGIN{print NR} END{print NR}'` |
| 13 | -v 從外部帶入變數 | `cat data.txt \| awk -v min=5000 '$3 > min {print $1, $3}'` |
| 14 | sum / NR 算出平均薪水 | `cat data.txt \| awk '{sum += $3} END{print sum / NR}'` |

## Duration

306.84s（約 5 分 7 秒）。

## A/V sync

sync verified (PASS) — J-cut on 13/13 transitions, mean 0.35s; min gap 0.995s; 0 voice overruns.

## Provenance

`awk/build/` holds the frozen record of this exact render: timeline/sync/jcut
reports (`timeline.json`, `sync_report.json`, `jcut_report.json`), the 5-gate
verdict (`verify.json`), a config snapshot (`config.toml`), the raw terminal
render (`terminal.mp4`) plus synthesized narration (`narration.mp3`), the lesson
source (`lesson/lesson.py` + `lesson/setup.sh`), the VHS tape (`demo.tape`) and
the build log (`build.log`). `clip/intermediate/` is SHARED scratch the next
build overwrites, so this snapshot is what keeps the clip reproducible.
`build/PROVENANCE.md` explains how to re-composite the final MP4 from these
artifacts without re-running vhs.

## Canonical source & full rebuild

The canonical source lesson lives in `clip/lessons/awk/`. A full rebuild is:

```bash
( cd clip && LESSON=awk python3 src/build.py && LESSON=awk bash src/setup_dirs.sh ) \
  && ( cd clip/intermediate && vhs demo.tape ) \
  && ( cd clip && .venv/bin/python src/overlay.py )
```
