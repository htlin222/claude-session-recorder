# ifconfig 教學 · 在 macOS 上查看網路介面與欄位

**Title:** ifconfig 教學 · 在 macOS 上查看網路介面與欄位

**Audience:** macOS command-line users — developers, sysadmins, and students — who want to read their machine's network configuration from the terminal and understand, field by field, what every line of `ifconfig` output means. Linux users are served too: the lesson explicitly flags where the BSD `ifconfig` diverges from Linux and points them at `ip addr`.

## Summary

A 1920×1080 CLI screencast that teaches `ifconfig` on macOS entirely through read-only inspection — no interface is ever modified. A live VHS terminal on the left runs each command while an explainshell-style panel on the right dissects every token as it is typed, narrated in one continuous Traditional Chinese voice with J-cut scene transitions and a sidecar `.srt` track. After an intro that flags the BSD-vs-Linux differences (hex netmasks, `flags=…<…>`, `media` lines, and the `ghead` truncation helper), the scenes walk from listing interfaces (`-l`, `-a`) to the two interfaces every Mac has (`lo0`, `en0`), then field by field through an interface's output: `flags`, `mtu`, `inet`, `netmask`, `inet6`, `ether`, `status`, and `media`. Each scene's key field is spoken verbatim so the panel annotation lands in typing-sync.

## Scenes (key · hero command)

| # | Scene key | Hero command |
|---|-----------|--------------|
| 0 | ifconfig · 在 macOS 上檢視網路介面 | _(intro · BSD vs Linux, read-only, `ghead`)_ |
| 1 | -l：只列出所有介面的名字 | `ifconfig -l` |
| 2 | -a：印出每個介面的完整資訊 | `ifconfig -a \| ghead -n 14` |
| 3 | lo0：每台機器都有的回送介面 | `ifconfig lo0` |
| 4 | en0：對外連線的主要介面 | `ifconfig en0` |
| 5 | flags：介面的狀態旗標 UP/RUNNING | `ifconfig en0 \| ghead -n 1` |
| 6 | mtu：單一封包的最大位元組數 | `ifconfig en0 \| grep -o 'mtu [0-9]*'` |
| 7 | inet：這個介面的 IPv4 位址 | `ifconfig en0 \| grep 'inet '` |
| 8 | netmask：劃分網段的子網路遮罩 | `ifconfig en0 \| grep -o 'netmask 0x[0-9a-f]*'` |
| 9 | inet6：這個介面的 IPv6 位址 | `ifconfig en0 \| grep inet6` |
| 10 | ether：網路卡的 MAC 硬體位址 | `ifconfig en0 \| grep ether` |
| 11 | status：介面目前是否在線 | `ifconfig en0 \| grep status` |
| 12 | media：實體連線的速率與型態 | `ifconfig en0 \| grep media` |

## Final duration

**320.64s** (≈ 5m 21s)

## A/V sync

sync verified (PASS) — J-cut on 12/12 transitions, mean 0.35s; min gap 0.995s; 0 voice overruns

## Files

- `ifconfig.mp4` — the finished screencast
- `ifconfig.srt` — external subtitle track
- `ifconfig.html` — offline self-contained HTML player

## Provenance

`ifconfig/provenance/` holds the frozen record of this render: `verify.json` (the 5 gates), `timeline.json`, `sync_report.json`, `jcut_report.json`, a snapshot of `config.toml` and `build.log`, the regenerable-but-expensive `terminal.mp4` + `narration.mp3`, a copy of the lesson source (`lesson/lesson.py` + `lesson/setup.sh`), the generated `demo.tape`, and `PROVENANCE.md` (human index + how to re-composite without re-running vhs).

This folder is **self-contained & portable** — move it anywhere and it still builds. Its own `CLAUDE.md` documents the full rebuild:

```bash
cd ifconfig && python3 src/build.py && bash setup.sh && ( cd intermediate && vhs demo.tape ) && .venv/bin/python src/overlay.py
```
