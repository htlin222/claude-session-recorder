# jq 教學 · 用過濾器在命令列裡解析 JSON

**Title:** jq 教學 · 用過濾器在命令列裡解析 JSON

**Audience:** Command-line users who already meet JSON every day — in API responses, config files, and logs — and want to stop eyeballing or hand-grepping it. Developers, sysadmins, and power users who want a dependable mental model of `jq`'s filter language so they can slice, reshape, and reformat JSON in a single pipeline.

## Summary

A 1920×1080 CLI screencast that teaches `jq` purely through filters, dissecting a `cat data.json | jq '<filter>'` pipeline one concept at a time. Working from a single fixed `data.json` (an array of three people, each with name, age, tags, and a nested location), each scene isolates one filter and builds on the last: identity (`.`), array indexing (`.[0]`), field access (`.name`), nested drilling (`.loc.city`), array explosion (`.[]`), the internal pipe (`|`), conditional `select`, `map`, `keys`, `length`, and the output flags `-r` (raw) and `-c` (compact), finishing with `@csv` to turn JSON into spreadsheet-ready rows. A live VHS terminal runs each command on the left while an explainshell-style panel on the right reveals each command's tokens as they are typed, all narrated in continuous Traditional Chinese, with the scene's star filter spoken verbatim so the panel annotation lands in typing-sync.

## Scenes (key · hero command)

| # | Scene key | Hero command |
|---|-----------|--------------|
| 0 | jq · 在命令列裡解析 JSON | _(intro · fixed input: `data.json`)_ |
| 1 | identity：一個點 . 原樣輸出 | `cat data.json \| jq '.'` |
| 2 | .[0] 取陣列第一個元素 | `cat data.json \| jq '.[0]'` |
| 3 | .name 取出欄位值 | `cat data.json \| jq '.[0].name'` |
| 4 | .loc.city 鑽進巢狀欄位 | `cat data.json \| jq '.[0].loc.city'` |
| 5 | .[] 把陣列逐個攤開 | `cat data.json \| jq '.[]'` |
| 6 | \| 用管線把過濾器接起來 | `cat data.json \| jq '.[] \| .name'` |
| 7 | select(...) 依條件篩選 | `cat data.json \| jq '.[] \| select(.age > 30)'` |
| 8 | map(...) 對整個陣列逐項轉換 | `cat data.json \| jq 'map(.age)'` |
| 9 | keys 列出物件的所有鍵 | `cat data.json \| jq '.[0] \| keys'` |
| 10 | length 量長度與元素數 | `cat data.json \| jq 'length'` |
| 11 | -r 輸出純文字、去掉引號 | `cat data.json \| jq -r '.[].name'` |
| 12 | -c 每筆壓成一行 | `cat data.json \| jq -c '.[]'` |
| 13 | @csv 把欄位組成 CSV | `cat data.json \| jq -r '.[] \| [.name, .age] \| @csv'` |

## Final duration

**298.56s** (≈ 4m 59s)

## A/V sync

sync verified (PASS) — J-cut on 13/13 transitions, mean 0.35s; min gap 0.995s; 0 voice overruns

## Files

- `jq.mp4` — the finished screencast
- `jq.srt` — external subtitle track
- `jq.html` — offline self-contained HTML player
- `provenance/` — frozen record of this render (see below)

## Provenance

`jq/provenance/` holds the frozen record of this render — the timeline / sync / J-cut
reports (`timeline.json`, `sync_report.json`, `jcut_report.json`), the 5-gate
`verify.json`, a snapshot of the `config.toml` this clip was built with, the
`terminal.mp4` + `narration.mp3`, the lesson source (`lesson/`), and `build.log`.
`provenance/PROVENANCE.md` explains how to re-composite the clip from this bundle
without re-running vhs (restore `terminal.mp4`, `narration.mp3`, and `timeline.json`
into the shared scratch, then re-run `overlay.py`). This snapshot exists because
`clip/intermediate/` is shared scratch that the next build overwrites — without it
the clip would become unreproducible the moment another lesson renders.

> Note: the bundle lives in `provenance/`, not `build/` — `src/bundle.py`
> deliberately uses `provenance/` because `build/` sits in most global gitignores
> (this matches the sibling `fzf/` clip).

## Source & re-rendering

The canonical source lesson lives in `clip/lessons/jq/` (`lesson.py` + `setup.sh`).
A full rebuild from source is:

```bash
( cd clip && LESSON=jq python3 src/build.py && LESSON=jq bash src/setup_dirs.sh ) && ( cd clip/intermediate && vhs demo.tape ) && ( cd clip && .venv/bin/python src/overlay.py )
```
