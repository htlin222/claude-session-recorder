# rg (ripgrep) 教學 · 快又聰明的遞迴搜尋

**Audience:** Developers / command-line users who already know `grep` and want a
faster, smarter recursive code search. Narration is zh-TW; the on-screen commands
and output are language-neutral.

## Summary

A 1920×1080 teaching video (left = a VHS terminal running real `rg` commands,
right = an explainshell-style panel that dissects each command token by token)
with one continuous zh-TW narration, J-cut scene transitions, and sidecar `.srt`
subtitles. Starting from why `grep` falls short in large projects, it walks
through `rg`'s smart defaults and twelve everyday flags — one flag per scene —
each demonstrated on a small throwaway demo project so the viewer sees the exact
behaviour and reads the per-token explanation as the command is typed.

## Scenes (key · hero command)

| # | Key | Hero command |
|---|-----|--------------|
| 0 | rg · 用 Rust 寫成、快又聰明的遞迴搜尋 (intro) | `tree -a --dirsfirst -I '...'` |
| 1 | 最基本：rg 樣式，預設就遞迴搜尋整個資料夾 | `rg TODO` |
| 2 | -i：忽略大小寫，ERROR 與 error 一網打盡 | `rg -i error src/log.txt` |
| 3 | -w：只比對整個單字，避開 errorlog 這種子字串 | `rg -w error src/log.txt` |
| 4 | -n：標出行號（rg 在終端機本來就預設顯示） | `rg -n TODO src/main.py` |
| 5 | -l：只列出有命中的檔名，不印內容 | `rg -l TODO` |
| 6 | -c：每個檔數出命中幾次 | `rg -c TODO` |
| 7 | -t py：只搜尋某種檔案類型 | `rg -t py TODO` |
| 8 | -g：用萬用字元 glob 圈定要搜的檔 | `rg -g '*.md' TODO` |
| 9 | -F：把樣式當純字串，不解讀正規表達式 | `rg -F '3.14' src/utils/calc.py` |
| 10 | -v：反向，列出「不」含樣式的行 | `rg -v error src/log.txt` |
| 11 | --hidden：把預設略過的隱藏檔也納入搜尋 | `rg --hidden secret` |
| 12 | -C：連同上下文一起印（另有 -A 與 -B） | `rg -C1 'my error' src/log.txt` |

## Duration

Final: **297.36s** (≈ 4 min 57 s; terminal 269.48s, narration 281.76s, on target
for the 300±60 s window).

## A/V sync

sync verified (PASS) — J-cut on 12/12 transitions, mean 0.35s; min gap 0.995s; 0
voice overruns.

## Provenance

`rg/provenance/` holds the frozen record of this render — `verify.json` (the
5-gate PASS verdict), `timeline.json`, `sync_report.json`, `jcut_report.json`, a
`config.toml` snapshot, `terminal.mp4` + `narration.mp3`, a copy of
`lesson/lesson.py` + `lesson/setup.sh`, `build.log`, and `PROVENANCE.md`. This
folder is self-contained and portable: its own `CLAUDE.md` documents how to
rebuild from scratch —
`cd rg && python3 src/build.py && bash setup.sh && ( cd intermediate && vhs demo.tape ) && .venv/bin/python src/overlay.py`.
