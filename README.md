# vhs-demo — narrated, sync-verified terminal teaching videos

## Goal
Turn terminal activity into a polished 1920×1080 teaching video: a real terminal
on the **left**, an explainshell-style panel on the **right**, one continuous
zh-TW **narration**, J-cut scene transitions, and sidecar `.srt` subtitles — with
the audio↔video sync **machine-verified, never eyeballed**. One topic = one
**portable, self-contained folder** another agent can pick up and rebuild.

Three production paths exist today, plus a fourth in progress:
1. **CLI lesson** — type a command, dissect its flags token-by-token (rsync, jq,
   awk, sed→gsed, grep, find, tar, fzf, ssh, rg, ifconfig, df, cp …).
2. **mdp slideshow** — a Markdown deck as a terminal slideshow + a detail panel.
3. **nvim code-demo** — drive an editor to write & run code live.
4. **(WIP) live Claude Code session** — record a real `claude` TUI run and narrate
   it from hook timecodes + transcript. See *Roadmap*.

## Repo layout
```
engine/                 canonical render engine (TEMPLATE / source-of-truth)
  src/  clipkit.py(S/R/CLR + load_lesson) build.py overlay.py verify_sync.py
        bundle.py envcheck.py
  config.toml  lesson.skel.py  CLAUDE.tmpl.md  context/(sync-model etc)
  experimental/         slideshow/ (mdp), nvim/ (recipe), session-recorder/ (hooks)
<slug>/                 a PORTABLE clip: vendored src/ + lesson.py + config.toml +
                        setup.sh + CLAUDE.md + <slug>.mp4/.srt/.html + provenance/
.claude/
  settings.json         session-recorder hooks (timecode logging)
  workflows/clip.js     the /clip dynamic workflow
material/               drop topic material here for /clip
```
Each `<slug>/CLAUDE.md` is a complete per-clip handoff doc; `engine/CLAUDE.md`
documents the engine; `engine/context/sync-model.md` is the sync evolution log.

## Pipeline (per clip, run from its folder)
`build.py` (edge-tts narration + `demo.tape` + `timeline.json`) → `setup.sh`
(demo env) → `vhs demo.tape` (terminal.mp4) → `overlay.py` (panel + J-cut + fades
→ `<slug>.mp4`) → `verify_sync.py` (the 5 gates) → `bundle.py` (freeze
`provenance/`). The `/clip` workflow automates all of it (design → envcheck →
author → render → verify → deliver).

## How sync works (the core idea)
ONE continuous narration; on-screen actions are pinned to its **sentence
boundaries** (edge-tts gives a real timestamp per sentence). The terminal's real
**clear frames** are detected from the video so the panel switches on the exact
frame the screen clears. Sync is **loop-engineered**: `verify_sync.py` gates five
things and nothing ships silently —
1. structural sync (every scene locked to a real clear),
2. narration not cut, 3. duration ≈5±1 min,
4. J-cut never overruns the *incoming* voice, 5. no scene's voice overruns into
the *next* clip. A fixable desync auto-heals (guided/threshold clears → re-overlay).

---

## ⚠️ Gotchas (hard-won — read before changing anything)

### VHS
- **`Set TypingSpeed 45ms` ≈ 24ms/char real** (~half). The timing model uses
  `config.timing.ts=0.024`; don't derive it from the Set value.
- **`Hide`/`Show` cost zero timeline time** — use to clear/`setopt` invisibly.
- **zsh doesn't treat `#` as a comment interactively** → `setopt interactive_comments`
  in a hidden block first, else `zsh: command not found: #`.
- **Non-deterministic TUIs (claude): use `Wait[+Screen]@timeout /regex/`, not
  `Sleep`.** Pair with a **sentinel** the app prints when done.
- **The terminal eats the FIRST keystroke** after launching a TUI → send a
  throwaway `Escape` before `i`/input (cost us the nvim demo until found).

### nvim (code-demo)
- **`autoindent` is ON even with `-u NONE`** → typed indentation *compounds*. Use a
  tiny init with `set noautoindent nosmartindent nocindent indentexpr=`.
- **A leftover swap file** makes nvim open the recovery prompt, which **silently
  eats your keystrokes** → `set noswapfile`.
- `:set paste` is **deprecated/no-op in nvim 0.11** — don't rely on it.

### mdp (slideshow)
- Slide transitions are **redraws, not clears** → `detect_clears` doesn't apply;
  anchor the panel to the **predicted `Space` times** (we drive them, so it's exact;
  no typing during the show ⇒ no drift).
- **Anchor the ending to the VOICE**, not the terminal length, and **don't `q`**
  (quitting shows the shell). Hold the last slide `END_HOLD` after the voice, then
  fade — a fixed tail gave a 7s silent ending / risked clipping the last word.

### Sync / J-cut
- **J-cut belongs at the TRANSITION, not in-scene.** v1 (in-scene, voice ahead of
  the command) desynced badly. Transition-level (incoming intro voice leads its
  video into the previous scene's silent hold) is correct.
- **Every scene must hold its still frame until ITS OWN voice finishes** (adaptive
  `end_pad`), else a long-narration scene bleeds into the next clip. This and the
  J-cut-overrun are two opposite failures on the same transition — both gated.
- **Sparse output** (`fzf -f`, single-line results) makes the screen dip near-empty
  mid-scene → `detect_clears` over-counts. Falls back to **guided** selection (pick
  the N drops nearest the predicted scene times).

### edge-tts / narration
- It splits the SRT **1:1 on `。！？`** — so each `S()` must be ONE complete
  sentence ending in `。！？`, no mid-sentence `。`. A mismatch aborts the build
  ("cue/sentence mismatch").
- Every `star`/`ord` panel token's flag text must appear **verbatim** in one of
  that scene's `S()` sentences, or the reveal falls out of typing-sync.

### macOS BSD vs Linux/GNU
- Default `sed`/`awk`/`date`/`stat`/`grep` are **BSD/variant** and differ from
  Linux (BSD `sed` silently ignores `\w`/`\b`, `\t` in replacements; `df` has no
  `-T`; etc.). Teach the **GNU variant** (`gsed`/`gawk`/`gdate`) or the strict POSIX
  subset, and **probe deterministically with `engine/src/envcheck.py`** (the `/clip`
  EnvCheck phase). Never show output that would differ on Linux without flagging it.

### ffmpeg / rendering
- This build has **no `libass`/`drawtext`/`subtitles`** → text (panel + subs) is
  drawn as **Pillow PNGs and `overlay`-ed**; subtitles ship as a sidecar `.srt`.
- Don't stack dozens of `overlay` filters — **flatten each layer to one video first**
  (concat demuxer), then a single overlay pass (~12s vs minutes).
- `ffmpeg` is aliased to `ffmpeg-bar`; scripts use the absolute
  `/opt/homebrew/bin/ffmpeg`.

### Claude Code hooks (session-recorder)
- **No timestamp in the hook payload** — capture your own (`time.time()`).
- **Every** payload carries `transcript_path` → the full conversation; the **Stop**
  hook's **last assistant message** is the turn's conclusion (the headline to narrate).
- Settings are read at **startup** → new hooks apply to a *fresh* session, not the
  running one.

### git / portability
- **`build/` is in most global gitignores** → the provenance folder is named
  **`provenance/`** (don't use `build/`).
- Track source + small text provenance; **media (`*.mp4/.mp3/.srt/.html`) and
  scratch (`intermediate/`, `.venv/`) are gitignored** and regenerate from the lesson.
- Portability cost: each slug **vendors a copy** of `engine/src` → fix engine bugs
  in `engine/` then propagate to slugs.
- Two self-inflicted bugs worth remembering: a **shared `intermediate/`** broke
  parallel renders (now per-folder); and `open(p,"w").write(open(p).read()…)`
  **truncates before it reads** — always read first, then write.

---

## Roadmap — the "majestic Claude Code tutorial"
We have the teaching scaffolding. The remaining piece is filming Claude Code
*itself* live. Plan (VHS-based, reuses everything):
1. **Stop sentinel** — `timelog.py` prints a marker on Stop so VHS can `Wait` on it.
2. **Session tape** — launch `claude`, drive prompts, `Wait@timeout /sentinel/`
   between turns (no guessed `Sleep`); VHS records the real TUI.
3. **overlay "session mode"** — anchor the panel to the **hook timecodes** (not
   clear-detection) and use the **event / Stop-message** panel; narration from
   `gen_voiceover.py`. (A course-assembly/montage layer is a later nicety.)

## Status
14 portable clips rendered + verified PASS; engine + `/clip` workflow + 3 clip-type
prototypes + the session-recorder all built and committed. See git log.
