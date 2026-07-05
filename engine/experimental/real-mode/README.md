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

## Optional per-line sound effects: `<name>.cues`

If `<name>.cues` exists next to the tape, `render.sh` mixes a macOS system
sound (from `/System/Library/Sounds/`) onto the output at each listed
timestamp — no cues file, silent output, unchanged from before. One
`<seconds> <Sound.aiff>` pair per line, timed to when that line STARTS
typing (not when it finishes — the sound plays under the typing, not after
it):

```
0.50 Hero.aiff
2.17 Glass.aiff
3.71 Tink.aiff
```

`nvim-demo.tape` puts a `Sleep 500ms` breath before every line's `Type` (the
first one right after `Show`) — without it, lines ran into each other with
no room to read each heading before the next one started.

`nvim-demo.cues` gives each markdown heading level (and list items) their
own sound right as they start being typed — H1 `Hero.aiff`, H2
`Glass.aiff`, H3 `Pop.aiff` (reserved, unused by this particular demo),
list items `Tink.aiff`.

Timestamps were found empirically, not read off the tape's `Set
TypingSpeed` — with no `Sleep` between a line's `Type` and its `Enter`,
VHS's own frame quantization makes exact keystroke arithmetic unreliable
past ~100ms. Line N's start is line N-1's completion (the gap between
`Enter` and the next `Type` is near zero), so the workflow: render once
with no cues file, then binary-search a handful of `ffmpeg -i out.mp4 -ss T
-update 1 -vframes 1 probe.png` frame grabs around each expected line-
completion time until each line reads as
just-finished, and use those `T`s. Good enough for a sound that's flavor,
not a hard sync target — re-derive the same way if the script text changes.

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
