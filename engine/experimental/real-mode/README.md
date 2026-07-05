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

## nvim demos: use `-n -u NONE`, not `-u <initfile>`

`nvim-demo.tape` types into a real nvim, launched with `-n -u NONE`
(no swapfile, no vimrc at all) and applies styling (`syntax on`, line
numbers, `colorscheme habamax`) via an Ex command typed right after launch
— not via `-u init.vim`. Three traps that make this necessary, all hit
while building this demo:

- **`-u <initfile>` still isn't isolated.** Neovim's own `defaults.lua` runs
  `filetype plugin on` for anything except `-u NONE`, which pulls in
  `~/.config/nvim/ftplugin/<filetype>/*.lua` from the machine's REAL config
  regardless of what `-u` points to — e.g. a broken `require()` in a
  personal `ftplugin/markdown/autocmd.lua` crashed every take whose target
  file happened to be `*.md`, even with `--noplugin` also passed. `-u NONE`
  is the only flag that actually skips it.
- **Swap-file recovery prompts eat keystrokes.** A stray `.swp` from a
  killed/crashed take makes the next one open on an `E325 ATTENTION`
  prompt, silently swallowing the scripted `i` and everything typed after
  as normal-mode commands. Pass `-n` (must be a launch flag — `-u NONE`
  means no vimrc runs before the file loads, so `:set noswapfile` typed
  afterward is too late).
- **The setup Ex command must type at `TypingSpeed 0ms`.** It's long
  (multiple `:set` options chained with `|`); typing it at the same speed
  as the demo content silently ate several extra seconds. `Set TypingSpeed`
  can be changed mid-tape — drop it to `0ms` for that one line, then
  restore it before the real typing starts.
