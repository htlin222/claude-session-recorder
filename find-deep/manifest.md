# find 深入教學 · 述詞、時間、路徑與動作全攻略

**Title:** find 深入教學 · 述詞、時間、路徑與動作全攻略

**Audience:** Command-line users who already "know" `find` but want to master it — developers, sysadmins, and power users who want a complete mental model (start dir + predicate + action) rather than a grab-bag of flags.

## Summary

A 1920×1080 CLI screencast that takes Unix `find` from "can use it" to "fluent". It builds one mental model — a start directory, a chain of predicates that filter, and a final action that processes — and walks through it scene by scene, progressing from the safest filtering predicates all the way to the file-touching actions. A live VHS terminal runs each command on the left while an explainshell-style panel on the right reveals each command's tokens as they are typed, all narrated in continuous Traditional Chinese. The read-only `-exec wc -l` demonstrates actions safely; the dangerous `-delete` is deliberately saved for last, with an explicit spoken warning that there is no trash can and no undo.

## Scenes (key · hero command)

| # | Scene key | Hero command |
|---|-----------|--------------|
| 0 | find · 述詞與動作的完整地圖 | _(intro / mental model + `tree app`)_ |
| 1 | -name 依檔名比對 | `find app -name '*.py'` |
| 2 | -iname 忽略大小寫 | `find app -iname '*.js'` |
| 3 | -type 限定檔案或目錄 | `find app -type d` |
| 4 | -size 依檔案大小過濾 | `find app -type f -size +1M` |
| 5 | -empty 找空檔案與空目錄 | `find app -empty` |
| 6 | -maxdepth 限制往下深度 | `find app -maxdepth 1 -type f` |
| 7 | -mindepth 跳過最上層 | `find app -mindepth 2 -name '*.py'` |
| 8 | -mtime 依修改時間 | `find app -type f -mtime -1` |
| 9 | -newer 比參考檔還新 | `find app -type f -newer app/.stamp` |
| 10 | -path 比對整段路徑 | `find app -path '*/logs/*'` |
| 11 | -prune 整個目錄跳過 | `find app -name node_modules -prune -o -type f -print` |
| 12 | -not 反向選擇 | `find app -type f -not -name '*.py'` |
| 13 | -exec 對每個結果執行命令（唯讀） | `find app -name '*.log' -exec wc -l {} +` |
| 14 | -delete 直接刪除（危險！最後示範） | `find app -name '*.tmp' -delete` |

## Final duration

**304.96s** (≈ 5m 05s)

## Files

- `find-deep.mp4` — the finished screencast
- `find-deep.srt` — external subtitle track
- `find-deep.html` — offline self-contained HTML player

## Source & re-rendering

The source lesson lives in `clip/lessons/find-deep/` (`lesson.py` + `setup.sh`). It can be re-rendered with:

```bash
( cd clip && LESSON=find-deep python3 src/build.py && LESSON=find-deep bash src/setup_dirs.sh ) && ( cd clip/intermediate && vhs demo.tape ) && ( cd clip && .venv/bin/python src/overlay.py )
```
