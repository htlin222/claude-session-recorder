# fzf 教學 · 用過濾模式 (-f) 玩轉模糊搜尋

**Title:** fzf 教學 · 用過濾模式 (-f) 玩轉模糊搜尋

**Audience:** Command-line users who have seen `fzf`'s full-screen interactive picker but want to truly understand its matching engine — developers, sysadmins, and power users who want stable, reproducible, scriptable fuzzy filtering rather than just an interactive TUI.

## Summary

A 1920×1080 CLI screencast that teaches `fzf` entirely through its non-interactive filter mode (`-f` / `--filter`), so it never opens the full-screen TUI and every output is stable and reproducible. By feeding fixed inputs (`pool.txt`, `data.csv`, a small `proj/` file tree) into `fzf -f`, each scene isolates one piece of the matching engine: basic subsequence fuzzy matching, score-ordered results, exact matching, prefix/suffix anchors, negation, OR, case sensitivity, input reversal, field-restricted matching, sort suppression, and finally a real `find | fzf` pipeline. A live VHS terminal runs each command on the left while an explainshell-style panel on the right reveals each command's tokens as they are typed, all narrated in continuous Traditional Chinese, with the scene's star flag spoken verbatim so the panel annotation appears in sync with the typing.

## Scenes (key · hero command)

| # | Scene key | Hero command |
|---|-----------|--------------|
| 0 | fzf · 用過濾模式學模糊搜尋（不開 TUI） | _(intro / fixed inputs: `pool.txt`, `data.csv`, `proj/`)_ |
| 1 | -f 過濾模式：字元依序就算命中 | `cat pool.txt \| fzf -f 'sap'` |
| 2 | 分數排序：最佳比對排最前面 | `cat pool.txt \| fzf -f 'ap' \| head -3` |
| 3 | 精確比對：--exact（等同前置單引號 'word） | `cat pool.txt \| fzf --exact -f 'main'` |
| 4 | ^src 前綴錨點 | `cat pool.txt \| fzf -f '^src'` |
| 5 | .py$ 後綴錨點 | `cat pool.txt \| fzf -f '.py$'` |
| 6 | !test 排除（negation） | `cat pool.txt \| fzf -f '!test'` |
| 7 | md$ \| py$ 任一條件 (OR) | `cat pool.txt \| fzf -f 'md$ \| py$'` |
| 8 | -i 忽略大小寫 | `cat pool.txt \| fzf -i -f 'readme'` |
| 9 | +i 強制區分大小寫 | `cat pool.txt \| fzf +i -f 'README'` |
| 10 | --tac 反轉輸入順序 | `cat pool.txt \| fzf --tac -f 'log'` |
| 11 | --nth 只比對指定欄位 | `cat data.csv \| fzf -d , --nth 2 -f 'alice'` |
| 12 | --no-sort 保留原始輸入順序 | `cat pool.txt \| fzf --no-sort -f 'py'` |
| 13 | 真實管線：find 的輸出接給 fzf | `find proj -type f \| fzf -f 'srcmain'` |

## Final duration

**282.56s** (≈ 4m 43s)

## A/V sync

SYNC NOT VERIFIED — desynced (24/13 clears, method=detect) (review before publishing)

## Files

- `fzf.mp4` — the finished screencast
- `fzf.srt` — external subtitle track
- `fzf.html` — offline self-contained HTML player

## Source & re-rendering

The source lesson lives in `clip/lessons/fzf/` (`lesson.py` + `setup.sh`). It can be re-rendered with:

```bash
( cd clip && LESSON=fzf python3 src/build.py && LESSON=fzf bash src/setup_dirs.sh ) && ( cd clip/intermediate && vhs demo.tape ) && ( cd clip && .venv/bin/python src/overlay.py )
```
