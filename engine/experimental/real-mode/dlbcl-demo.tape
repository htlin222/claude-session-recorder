Output dlbcl-demo.mp4

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
Type "nvim dlbcl.md"
Enter
Sleep 1s

Escape
Sleep 300ms
Type "i"
Sleep 400ms
Show
Sleep 500ms

Type "# Frontline Treatment of DLBCL"
Enter
Sleep 500ms
Type "## Standard Regimen"
Enter
Sleep 500ms
Type "- R-CHOP x6, 21-day cycles"
Enter
Enter
Sleep 500ms
Type "## Risk Stratification"
Enter
Sleep 500ms
Type "- IPI score guides intensity"
Enter
Enter
Sleep 500ms
Type "## Low Risk (IPI 0-1)"
Enter
Sleep 500ms
Type "- R-CHOP x6, no extra therapy"
Enter
Enter
Sleep 500ms
Type "## Intermediate Risk (IPI 2-3)"
Enter
Sleep 500ms
Type "- R-CHOP x6 + consider CNS ppx"
Enter
Enter
Sleep 500ms
Type "## High Risk (IPI 4-5)"
Enter
Sleep 500ms
Type "- R-CHOP x6 + CNS prophylaxis"
Enter
Enter
Sleep 500ms
Type "## CNS-IPI High Risk Sites"
Enter
Sleep 500ms
Type "- Testis, breast, kidney, adrenal"
Enter
Enter
Sleep 500ms
Type "## CNS Prophylaxis"
Enter
Sleep 500ms
Type "- IT MTX or high-dose IV MTX"
Enter
Enter
Sleep 500ms
Type "## Double-Hit Lymphoma"
Enter
Sleep 500ms
Type "- MYC + BCL2/BCL6 rearranged"
Enter
Enter
Sleep 500ms
Type "## Double-Hit Regimen"
Enter
Sleep 500ms
Type "- DA-EPOCH-R over R-CHOP"
Enter
Enter
Sleep 500ms
Type "## Elderly or Frail"
Enter
Sleep 500ms
Type "- R-mini-CHOP, reduced dose"
Enter
Enter
Sleep 500ms
Type "## Bulky Disease"
Enter
Sleep 500ms
Type "- Over 7.5cm, consider RT"
Enter
Enter
Sleep 500ms
Type "## Interim Response"
Enter
Sleep 500ms
Type "- PET-CT after cycles 2-4"
Enter
Enter
Sleep 500ms
Type "## Deauville Score"
Enter
Sleep 500ms
Type "- 1-3 negative, 4-5 positive"
Enter
Enter
Sleep 500ms
Type "## Primary Refractory"
Enter
Sleep 500ms
Type "- CAR-T cell therapy"
Enter
Enter
Sleep 500ms
Type "## Relapsed Disease"
Enter
Sleep 500ms
Type "- Salvage chemo, then ASCT"

Escape
Sleep 1.5s
