# grep 教學 · 用樣式搜尋在文字裡精準命中

**Audience:** 終端機 / 命令列的初學到中階使用者 — 想學會用 `grep` 在紀錄檔與原始碼裡按樣式搜尋、過濾、計數與看文脈。

## Summary

這支約五分鐘的繁中教學影片，從最基本的「樣式 + 檔案」開始，帶你逐步走過 `grep` 最常用的旗標：忽略大小寫 (`-i`)、顯示行號 (`-n`)、只算數量 (`-c`)、反向選取 (`-v`)、整詞比對 (`-w`)、只印命中片段 (`-o`)、延伸正規表示式 (`-E`)、遞迴搜尋目錄 (`-r` / `-rl`)，以及命中前後的文脈 (`-A` / `-C`)。所有命令都餵給一份固定的範例樹（`logs/app.log`、`logs/access.log`、`src/`），輸出穩定、非互動、可自我終止。畫面左側是 VHS 終端逐情境跑命令，右側是 explainshell 風格側欄，命令逐 token 隨打字浮現解說，一條連續旁白把每個旗標逐字帶到，場景間以 1 秒定格加 crossfade 銜接。

## Scenes (key · hero command)

1. `grep · 用樣式在文字裡搜尋` — 導覽範例樹：`tree logs src` + `cat logs/app.log`
2. `基本比對 · grep 樣式 檔案` — `grep ERROR logs/app.log`
3. `-i 忽略大小寫` — `grep -i error logs/app.log`
4. `-n 顯示行號` — `grep -n ERROR logs/app.log`
5. `-c 只算數量` — `grep -c ERROR logs/app.log`
6. `-v 反向選取` — `grep -v INFO logs/app.log`
7. `-w 整詞比對` — `grep -w id logs/app.log`
8. `-o 只印命中片段` — `grep -o 'user=[a-z]*' logs/app.log`
9. `-E 延伸正規表示式` — `grep -E 'ERROR|WARN' logs/app.log`
10. `-r 遞迴搜尋目錄` — `grep -r TODO src`
11. `-rl 只列出檔名` — `grep -rl TODO src`
12. `-A 命中後的文脈` — `grep -A 1 ERROR logs/app.log`
13. `-C 命中前後的文脈` — `grep -C 1 ERROR logs/app.log`

## Duration

299.52s (final render)

## A/V sync

sync verified (PASS) — J-cut on 12/12 transitions, mean 0.35s; min gap 1s; 0 voice overruns

## Provenance

`grep/build/` holds the frozen record of this exact render: the timeline / sync / J-cut
reports (`timeline.json`, `sync_report.json`, `jcut_report.json`), the 5-gate verdict
(`verify.json`), a config snapshot (`config.toml`), the generated VHS tape (`demo.tape`),
the raw terminal render and synthesized narration (`terminal.mp4` + `narration.mp3`), a
copy of the lesson source (`lesson/`), and the build log (`build.log`). This snapshot is
required because `clip/intermediate/` is SHARED scratch that the next build overwrites —
without it this clip becomes unreproducible. `grep/build/PROVENANCE.md` indexes the bundle
and explains how to re-composite the final MP4 from it **without re-running vhs** (restore
the timeline / terminal / narration into `clip/intermediate/grep/`, then run `overlay.py`).

## Canonical source & full rebuild

The canonical source lesson lives in `clip/lessons/grep/` (`lesson.py` + `setup.sh`). A full
rebuild from source is:

```bash
( cd clip && LESSON=grep python3 src/build.py && LESSON=grep bash src/setup_dirs.sh ) \
  && ( cd clip/intermediate && vhs demo.tape ) \
  && ( cd clip && .venv/bin/python src/overlay.py )
```
