# GNU sed 教學 · 用 gsed 串流編輯器一行改文字

**Audience:** 已會基本 shell 與管線、想學文字串流編輯的使用者，特別是 macOS 上想學
Linux 標準 `sed` 行為的學習者（macOS 內建 BSD sed，本課全程改用 `gsed` / GNU sed，
輸出才與 Linux 教材一致）。

## Summary

一支約五分鐘的 CLI 教學影片：左側 VHS 終端逐情境跑命令，右側 explainshell 風格側欄
隨打字浮現、逐 token 拆解，配上一條連續繁體中文旁白。內容從「為何在 macOS 要用
`gsed`」講起，接著用同一個 7 行 `notes.txt` 範例檔，一個情境教一個概念，循序帶過 GNU
sed 最核心的招式：`s///` 取代、`/g` 全域、`I` 忽略大小寫、`&` 引用匹配、`-E` 擴充正則、
`\1` 反向參照、`\b` 整字邊界，以及 `-n` 搭配 `p`、單行/範圍位址與 `d` 刪除行。全程走
stdin/stdout（不用 `-i` 就地編輯），每個示範都是確定性、非互動、會自行結束的。

## Scenes (key · hero command)

1. sed 是什麼？Linux 用 sed，macOS 請用 gsed · `cat notes.txt`
2. s/old/new/ 取代每行第一個符合 · `cat notes.txt | gsed 's/red/blue/'`
3. /g 全域旗標，整行全部取代 · `cat notes.txt | gsed 's/red/blue/g'`
4. s///I 比對時忽略大小寫 · `cat notes.txt | gsed 's/green/lime/gI'`
5. & 在替換裡引用整段匹配 · `cat notes.txt | gsed 's/cat/[&]/'`
6. -E 啟用擴充正則表達式 · `cat notes.txt | gsed -E 's/(cat|dog)/pet/g'`
7. \1 反向參照括號抓到的內容 · `cat notes.txt | gsed -E 's/([0-9]+)-([0-9]+)-([0-9]+)/\3\2\1/'`
8. \b 整字比對（GNU 專屬，BSD 不支援） · `cat notes.txt | gsed 's/\bcat\b/fish/g'`
9. -n 搭配 p 只印需要的行 · `cat notes.txt | gsed -n '/date/p'`
10. 2p 用單行位址點名某一行 · `cat notes.txt | gsed -n '2p'`
11. 2,4p 用範圍位址取一段 · `cat notes.txt | gsed -n '2,4p'`
12. d 刪除符合的整行（會移除內容，最後示範） · `cat notes.txt | gsed '/TODO/d'`

## Duration

Final: **297.68s** (≈ 4 分 58 秒)

## A/V sync

sync verified (PASS) — J-cut on 11/11 transitions, mean 0.35s; min gap 0.992s; 0 voice overruns

## Provenance

`sed/build/` holds the frozen record of this render — the timeline / sync / jcut
reports (`timeline.json`, `sync_report.json`, `jcut_report.json`), the 5-gate
`verify.json`, a snapshot of the build config (`config.toml`), the raw
`terminal.mp4` + `narration.mp3`, the lesson source (`lesson/`), and `build.log`.
Because `clip/intermediate/` is SHARED scratch that the next build overwrites,
this snapshot is what keeps the clip reproducible. `build/PROVENANCE.md` explains
how to re-composite the final video from these artifacts **without re-running
vhs** (restore `timeline.json` / `terminal.mp4` / `narration.mp3` into
`clip/intermediate/sed/`, then run `overlay.py`).

## Source & full rebuild

The canonical source lesson lives in `clip/lessons/sed/`. A full rebuild (re-runs
vhs) is:

```bash
( cd clip && LESSON=sed python3 src/build.py && LESSON=sed bash src/setup_dirs.sh ) && ( cd clip/intermediate && vhs demo.tape ) && ( cd clip && .venv/bin/python src/overlay.py )
```
