Output nvim-demo.mp4

Set FontSize 42
Set Width 1080
Set Height 1350
Set Theme "Catppuccin Mocha"
Set TypingSpeed 45ms

Env PS1 "❯ "
Env PROMPT "❯ "

Hide
Type "clear"
Enter
Show
Sleep 500ms

# -u NONE, not a real vimrc file: Neovim's own defaults.lua runs "filetype
# plugin on" for anything BESIDES `-u NONE`, which pulls in this machine's
# ~/.config/nvim/ftplugin/markdown/autocmd.lua (broken require, crashes into
# a "-- More --" error prompt) purely because the file is named *.md — even
# with --noplugin and even pointing -u at an isolated init.vim. -u NONE is
# the only flag that actually skips that. Styling is applied by hand below
# instead of via init.vim.
Type "nvim -n -u NONE hypokalemia.md"
Enter
Sleep 1s

Escape
Sleep 300ms
Set TypingSpeed 0ms
Type ":set noautoindent nosmartindent nocindent indentexpr= expandtab | filetype indent off | syntax on | set number laststatus=2 | colorscheme habamax"
Enter
Sleep 300ms
Set TypingSpeed 45ms

Type "i"
Sleep 400ms

Type "# Treatment of Hypokalemia"
Enter
Enter
Type "## Mild (3.0-3.5 mEq/L)"
Enter
Type "- Oral KCl 40-60 mEq/day"
Enter
Enter
Type "## Severe (<3.0 mEq/L)"
Enter
Type "- IV KCl 10-20 mEq/hr"
Enter
Type "- Cardiac monitoring"

Escape
Sleep 1.5s
