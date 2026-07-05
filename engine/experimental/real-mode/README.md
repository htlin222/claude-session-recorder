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
