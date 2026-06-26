# ssh 教學 · 不連線也能學的本機金鑰與設定

**Audience**: 開發者與系統管理員 — 任何想把 SSH 的「本機、可重現、不連線」那一半學紮實的人；
不需要遠端主機、不需要網路，也不會動到你真正的 `~/.ssh`。

## Summary

一支 1920×1080、全程 zh-TW 連續旁白的教學影片：左側是 VHS 終端機實際敲指令，右側是
explainshell 風格的面板，逐 token 拆解每一條指令。它只教 SSH 工具家族裡不需連線的部分 ——
查版本、產生 ed25519 金鑰對、分辨私鑰與公鑰、從私鑰推回公鑰、指紋與 randomart、`~/.ssh/config`
的 `Host` 區塊格式，最後用 `ssh -G` 印出解析後的有效設定卻完全不連線。所有示範都跑在拋棄式的
`intermediate/` 沙盒裡，新鮮金鑰是現場生成的，輸出的形狀穩定可教，scene 之間以 J-cut 轉場，
並附 sidecar `.srt` 字幕。

## Scenes (key · hero command)

| # | Key | Hero command |
|---|-----|--------------|
| 0 | ssh · 不連線也能學的金鑰與設定（標題卡） | — |
| 1 | ssh -V：查 OpenSSH 版本 | `ssh -V` |
| 2 | ssh-keygen -t：產生 ed25519 金鑰對 | `ssh-keygen -t ed25519 -C 'me@host' -f ./id_demo -N ''` |
| 3 | 私鑰 id_demo：絕對不能外流 | `gcat id_demo` |
| 4 | 公鑰 id_demo.pub：可以公開分享 | `gcat id_demo.pub` |
| 5 | ssh-keygen -y：從私鑰推回公鑰 | `ssh-keygen -y -f id_demo` |
| 6 | ssh-keygen -l：算金鑰指紋 | `ssh-keygen -l -f id_demo.pub` |
| 7 | -E md5：換成舊式指紋格式 | `ssh-keygen -l -E md5 -f id_demo.pub` |
| 8 | ssh-keygen -v：畫出指紋的 randomart | `ssh-keygen -lv -f id_demo.pub` |
| 9 | ~/.ssh/config：用 Host 區塊描述主機 | `gcat config` |
| 10 | ssh -G：印出解析後的有效設定（不連線） | `ssh -G web -F ./config` |
| 11 | ssh-keygen -R：從 known_hosts 移除主機（破壞性） | `ssh-keygen -R oldserver -f known_hosts` |

11 command scenes (+ 1 title card), 11 transitions.

## Duration

Final: **302.52s** (≈5:03, within the 300±60s target).

## A/V sync

sync verified (PASS) — J-cut on 11/11 transitions, mean 0.35s; min gap 1s; 0 voice overruns.

## Provenance

`ssh/provenance/` holds the frozen record of this render — `verify.json` (the 5 gates:
structural sync, narration-not-cut, duration, J-cut clips, voice overruns; all PASS),
the timeline/sync/J-cut reports, a snapshot of `config.toml`, the raw `terminal.mp4` +
`narration.mp3` (re-composite without re-running vhs), a copy of `lesson.py` + `setup.sh`,
`build.log`, and `PROVENANCE.md` as the human index. This folder is **self-contained &
portable**: its own `CLAUDE.md` documents how to rebuild from scratch —
`cd ssh && python3 src/build.py && bash setup.sh && ( cd intermediate && vhs demo.tape ) && .venv/bin/python src/overlay.py`.
