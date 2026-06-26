# experimental/ — new clip TYPES (proven prototypes)

Beyond the "type a CLI command, explain its flags" lessons, the VHS terminal can
drive *any* TUI. These are standalone proofs that other clip shapes work, kept
separate from the main engine until they earn integration into `/clip`.

## slideshow/ — terminal slide deck (mdp)
`slideshow.py` runs a Markdown deck through **mdp** as a fullscreen terminal
presentation (left pane), advanced by timed `Space` keypresses, with a **detail
panel** on the right that elaborates each slide, plus one continuous zh-TW
narration. Output: `../../mdp-demo/mdp-demo.mp4`.

Why it's its own pipeline: the main engine anchors the panel to detected screen
**clears**, but mdp slide transitions are redraws, not clears. Here WE drive the
slides, so the panel switches on those same predicted `Space` times — and with no
typing during the show there's no per-char drift, so predicted == real. Run:
`clip/.venv/bin/python slideshow/slideshow.py`.

## nvim/ — live code-editing demo
`init.vim` + `demo.tape`: a PROVEN recipe for VHS driving **nvim** to type code
into a file and run it. Render: `cd nvim && vhs demo.tape` (-> out.mp4). Three
traps it solves (see comments in both files):
1. **autoindent** is ON by default (even `-u NONE`) → typed indentation compounds.
   The init sets `noautoindent`.
2. a leftover **swap file** makes nvim open the swap-recovery prompt, which eats
   the first keystrokes (your `i` never enters insert). The init sets `noswapfile`.
3. the terminal **absorbs the very first keystroke** → send a throwaway `Escape`
   before `i` in the tape.

Result: `def fib` typed live in INSERT mode with correct indentation, saved with
`:wq`, then run → `[0, 1, 1, 2, 3, 5, 8, 13, 21, 34]`.

## Status
Both are working prototypes, not yet `/clip` modes. Natural next step: fold the
slideshow into the engine as a `SLIDE()`/slideshow lesson type, and the nvim
recipe into a `code-demo` lesson type, so `/clip` can produce them too.
