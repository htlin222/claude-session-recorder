Output lizard-demo.mp4

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
Type "nvim lizards.md"
Enter
Sleep 1s

Escape
Sleep 300ms
Type "i"
Sleep 400ms
Show
Sleep 500ms

Type "# 蜥蜴的分類"
Enter
Sleep 500ms
Type "## 壁虎科"
Enter
Sleep 500ms
Type "- 守宮、截趾虎"
Enter
Enter
Sleep 500ms
Type "## 鬣蜥科"
Enter
Sleep 500ms
Type "- 綠鬣蜥、環頸蜥"
Enter
Enter
Sleep 500ms
Type "## 石龍子科"
Enter
Sleep 500ms
Type "- 藍尾石龍子"

Escape
Sleep 1.5s
