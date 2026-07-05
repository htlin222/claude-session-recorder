# real-mode

Quick vertical (9:16) social-clip recorder for terminal demos. No ledger, no
narration, no panel — just `vhs <tape>` then one `ffmpeg pad` pass. Separate
from `session-recorder`'s deterministic pipeline on purpose: this is for a
short one-shot demo, not a narrated lesson.

## How it works

1. The VHS tape records at the CONTENT resolution (e.g. `1080x1350`, a 4:5
   frame) — not the final canvas.
2. `render.sh <tape>` runs `vhs`, then pads that footage into a `<width>x<width*16/9>`
   9:16 canvas, letterboxed with the Catppuccin Mocha background color
   (`#1e1e2e`) so the bars blend into the theme instead of showing as stark
   black.
3. Output: `<name>.mp4` (raw content) and `<name>-916.mp4` (final 9:16
   deliverable) next to the tape.

```bash
cd engine/experimental/real-mode
./render.sh nvim-demo.tape   # -> nvim-demo.mp4, nvim-demo-916.mp4
```

## Writing content for a new reel

Same shape as `nvim-demo.tape` / `lizard-demo.tape`:

```
# Title                (H1, exactly one line)
## Category one        (H2)
- content              (list — usually one line, comma/、-separated items)
## Category two         (H2)
- content
## Category three       (H2, optional — 2 groups is fine too)
- content
```

Two SEPARATE constraints — don't conflate "keep the clip short" with "keep
the content short", they're independent dials:

- **Line count is a duration dial, no real cap.** More lines just makes a
  longer clip (each one costs its typing time + the 0.5s breath). 5–7 lines
  (1 H1 + 2–3 H2+list groups) lands ~10–12s.
- At `FontSize 42` / `Height 1350` (measured line height ~52px, first line
  ~68px down), `(1350-68)/52 ≈ 24` lines fit before nvim starts
  **scrolling** — earlier lines get pushed off the top instead of the
  whole outline staying visible at once. Tested this at 30 lines expecting
  it to look broken; it doesn't — it reads as an ordinary, continuous
  scroll-up, same as typing a long file in a real terminal. So: **~24 is
  only the "whole thing fits on one screen" line**, not a usability limit —
  go past it on purpose if the reveal-then-scroll look is what you want for
  a longer outline.
- **Per-line wrap limit** at `Width 1080` (exceeding this wraps mid-line
  and looks broken, separate from the screen's line-count limit above):
  **~42 ASCII chars/line** (incl. the `#`/`##`/`-` prefix), **~21 CJK
  chars/line** (CJK renders double-width).
- **Pacing reference** (content only, excluding the prefix) — use this to
  estimate a clip's total length, not to cap content: total ≈ 0.5s
  (lead-in) + 1.5s (tail) + `n_lines`×0.5s (breath) + sum of each line's
  typing time below. Content around 12–20 ASCII chars or 4–7 CJK chars
  per line keeps each line's typing to roughly 0.5–0.9s if you *do* want a
  ~10s clip; go longer per line (or add more lines) for a longer one.

  | | typing time/line |
  | --- | --- |
  | ASCII | ~45ms/char |
  | CJK | ~135ms/char (3x ASCII) |
- `<name>.sfx` must have exactly as many lines as the tape has `Type`
  lines, same order: H1 → `Hero.aiff`, H2 → `Glass.aiff`, list → `Tink.aiff`
  (H3 → `Pop.aiff`, reserved — neither demo has used one yet).

## Optional per-line sound effects: `<name>.sfx`

If `<name>.sfx` exists next to the tape, `render.sh` mixes a macOS system
sound (from `/System/Library/Sounds/`) onto the output for each line — no
sfx file, silent output, unchanged from before. It's just an ordered list
of sound names, one per typed line, no timestamps:

```
Hero.aiff
Glass.aiff
Tink.aiff
```

`gen_onsets.py` computes each line's actual onset — no manual calibration.
**Why not hardcoded timestamps** (the first approach, and why it got
replaced): VHS re-renders the *same* tape with measurably different total
duration run to run (observed 8.96s vs 10.36s for `lizard-demo.tape`,
unchanged) — a timestamp picked off one render is already wrong on the
next. Worse, CJK characters render roughly 3x slower per character than
ASCII in this typing model (not documented anywhere — found empirically by
watching a CJK demo drift ~1.5s behind an English-calibrated timeline).
Hand-probing frames to find each line's start (`ffmpeg -ss T -update 1
-vframes 1 probe.png`, nudge `T`, repeat) works but doesn't scale and has
to be redone per render.

Instead, `gen_onsets.py <tape> <content.mp4>`:
1. reads the tape's own `Sleep` constants — the lead-in right after `Show`,
   the breath before every `Type`, the tail after the closing `Escape` —
   which ARE exact wall-clock waits, unlike typing speed;
2. weights each line by character count (CJK chars at 3x, matching the
   empirical ratio above);
3. takes the ACTUAL measured duration of whatever `vhs` just rendered
   (`ffprobe` on `$out`, post-render — not predicted), subtracts the fixed
   Sleep time, and divides what's left across lines proportional to weight.

So onsets are re-derived from this specific render's real timing every time
`render.sh` runs, rather than assuming a fixed model — self-correcting for
the run-to-run drift instead of fighting it. It's not frame-accurate (own
measured error: within roughly a second on a ~10s clip with 6-7 lines) —
good enough for a background ding under fast typing, not a hard sync
target. A genuinely frame-accurate version would need to read the rendered
video's own pixels (the way `session-recorder`'s `detect_anchors.py` does
for real capture) — real implementation work, not done here; this module
stays in "close enough, always automatic" territory on purpose.

`nvim-demo.sfx` / `lizard-demo.sfx` give each markdown heading level its own
sound as it starts — H1 `Hero.aiff`, H2 `Glass.aiff`, H3 `Pop.aiff`
(reserved, neither demo happens to use an H3), list items `Tink.aiff`.

`nvim-demo.tape` puts a `Sleep 500ms` breath before every line's `Type` (the
first one right after `Show`) — without it, lines ran into each other with
no room to read each heading before the next one started. `gen_onsets.py`
assumes this exact convention (lead-in, then one uniform breath before
every line, then a tail) — a tape structured differently needs the parser
adjusted, not just new numbers.

## nvim demos: an isolated XDG config, not `-u <initfile>`

`nvim-demo.tape` just runs plain `nvim <file>` — no `-u` flag at all.
`render.sh` instead exports `XDG_CONFIG_HOME` / `XDG_DATA_HOME` /
`XDG_STATE_HOME` to point at `nvim-xdg/` before calling `vhs`, so nvim's
*entire* runtimepath is this module's own isolated config — it never reads
or writes anything under the real `~/.config/nvim`, `~/.local/share/nvim`,
etc. `nvim-xdg/config/nvim/init.lua` is the whole config: no swapfile, no
autoindent creep, line numbers, and a hand-rolled `colors/catppuccin-mocha.lua`
(real Catppuccin Mocha hex values, not the builtin `habamax` scheme, which
doesn't share the palette) so nvim's own highlighting actually matches the
terminal's `Set Theme "Catppuccin Mocha"`.

Three traps found while building this, in case the isolation is ever
loosened back to `-u <initfile>` or similar:

- **`-u <initfile>` alone isn't isolated.** Neovim's own `defaults.lua` runs
  `filetype plugin on` for anything except `-u NONE`, which scans
  `$XDG_CONFIG_HOME/nvim/ftplugin/<filetype>/*.lua` — if that's still the
  real one, a broken personal `require()` in `ftplugin/markdown/autocmd.lua`
  crashed every take whose target file happened to be `*.md`, even with
  `--noplugin` also passed. Redirecting the whole XDG trio (rather than
  passing `-u`) sidesteps this at the source: the real config is never on
  runtimepath to begin with.
- **Swap-file recovery prompts eat keystrokes.** A stray `.swp` from a
  killed/crashed take makes the next one open on an `E325 ATTENTION` prompt,
  silently swallowing the scripted `i` and everything typed after as
  normal-mode commands. `vim.o.swapfile = false` in `init.lua` prevents new
  ones; the isolated `$XDG_STATE_HOME` also means a stray one can't
  accumulate under the real config's swap directory.
- **A long setup Ex command eats seconds if typed at demo speed.** Not an
  issue now that styling lives in `init.lua` instead of being typed as a
  `:set ...` command after launch — worth remembering if a future tape
  needs one: `Set TypingSpeed` can be changed mid-tape, so drop it to `0ms`
  for a long one-off command line, then restore it.
