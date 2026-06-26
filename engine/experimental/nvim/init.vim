" Minimal nvim config for DETERMINISTIC VHS code-typing demos.
" Three traps this avoids (all learned the hard way):
"   1. autoindent — nvim ships it ON (even with -u NONE), so each typed line
"      inherits the previous indent and your literal spaces COMPOUND. Off.
"   2. swap file — a leftover .swp makes nvim open with the swap-recovery prompt,
"      which silently EATS the first keystrokes (your `i` never enters insert,
"      and the code types as normal-mode commands). noswapfile.
"   3. (in the tape, not here) the terminal absorbs the very first keystroke, so
"      send a throwaway `Escape` before `i`.
set noautoindent nosmartindent nocindent indentexpr= expandtab
set noswapfile
filetype indent off
syntax on
set number laststatus=2
silent! colorscheme habamax
