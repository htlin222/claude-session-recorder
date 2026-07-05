Output nvim-demo.mp4

Set FontSize 42
Set Width 1080
Set Height 1350
Set Theme "Catppuccin Mocha"
Set TypingSpeed 45ms

Env PS1 "❯ "
Env PROMPT "❯ "

# Everything through entering insert mode is Hidden — the recording opens
# straight on the (chrome-free, empty) buffer, not the launch command.
Hide
Type "clear"
Enter

# Plain nvim — no -u override needed. render.sh points XDG_CONFIG_HOME (and
# XDG_DATA_HOME/XDG_STATE_HOME) at nvim-xdg/ before calling `vhs`, so this
# picks up ONLY nvim-xdg/config/nvim/init.lua: real Catppuccin Mocha colors,
# line numbers, no swapfile — never touches ~/.config/nvim.
Type "nvim hypokalemia.md"
Enter
Sleep 1s

Escape
Sleep 300ms
Type "i"
Sleep 400ms
Show

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
