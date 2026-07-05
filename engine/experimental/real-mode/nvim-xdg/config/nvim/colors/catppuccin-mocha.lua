-- Minimal, self-contained Catppuccin Mocha colorscheme.
-- Hand-rolled (not the catppuccin/nvim plugin — that isn't installed here
-- and this module intentionally never touches the real ~/.config/nvim to
-- borrow it) so `nvim`'s own highlighting matches the terminal's
-- "Catppuccin Mocha" VHS theme instead of falling back to a builtin scheme
-- like habamax that doesn't share the palette.
vim.cmd("hi clear")
if vim.fn.exists("syntax_on") == 1 then
  vim.cmd("syntax reset")
end
vim.o.termguicolors = true
vim.o.background = "dark"
vim.g.colors_name = "catppuccin-mocha"

-- https://catppuccin.com/palette — Mocha
local p = {
  rosewater = "#f5e0dc", flamingo = "#f2cdcd", pink = "#f5c2e7",
  mauve = "#cba6f7", red = "#f38ba8", maroon = "#eba0ac",
  peach = "#fab387", yellow = "#f9e2af", green = "#a6e3a1",
  teal = "#94e2d5", sky = "#89dceb", sapphire = "#74c7ec",
  blue = "#89b4fa", lavender = "#b4befe", text = "#cdd6f4",
  subtext1 = "#bac2de", subtext0 = "#a6adc8", overlay2 = "#9399b2",
  overlay1 = "#7f849c", overlay0 = "#6c7086", surface2 = "#585b70",
  surface1 = "#45475a", surface0 = "#313244", base = "#1e1e2e",
  mantle = "#181825", crust = "#11111b",
}

local hl = function(group, opts) vim.api.nvim_set_hl(0, group, opts) end

-- editor UI
hl("Normal", { fg = p.text, bg = p.base })
hl("NormalNC", { fg = p.text, bg = p.base })
hl("LineNr", { fg = p.surface2 })
hl("CursorLine", { bg = p.surface0 })
hl("CursorLineNr", { fg = p.lavender, bold = true })
hl("StatusLine", { fg = p.crust, bg = p.lavender, bold = true })
hl("StatusLineNC", { fg = p.text, bg = p.surface0 })
hl("VertSplit", { fg = p.surface0 })
hl("SignColumn", { bg = p.base })
hl("ColorColumn", { bg = p.surface0 })
hl("Cursor", { fg = p.base, bg = p.text })
hl("Visual", { bg = p.surface1 })
hl("Search", { fg = p.base, bg = p.yellow })
hl("IncSearch", { fg = p.base, bg = p.peach })
hl("Pmenu", { fg = p.text, bg = p.surface0 })
hl("PmenuSel", { fg = p.base, bg = p.lavender })
hl("NonText", { fg = p.surface1 })
hl("EndOfBuffer", { fg = p.surface1 })
hl("MatchParen", { fg = p.peach, bold = true })

-- syntax
hl("Comment", { fg = p.overlay1, italic = true })
hl("Constant", { fg = p.peach })
hl("String", { fg = p.green })
hl("Character", { fg = p.teal })
hl("Number", { fg = p.peach })
hl("Boolean", { fg = p.peach })
hl("Identifier", { fg = p.lavender })
hl("Function", { fg = p.blue, bold = true })
hl("Statement", { fg = p.mauve, bold = true })
hl("Conditional", { fg = p.mauve })
hl("Repeat", { fg = p.mauve })
hl("Keyword", { fg = p.mauve })
hl("Operator", { fg = p.sky })
hl("PreProc", { fg = p.yellow })
hl("Include", { fg = p.mauve })
hl("Define", { fg = p.mauve })
hl("Macro", { fg = p.mauve })
hl("Type", { fg = p.yellow })
hl("StorageClass", { fg = p.yellow })
hl("Structure", { fg = p.yellow })
hl("Special", { fg = p.pink })
hl("Underlined", { fg = p.blue, underline = true })
hl("Error", { fg = p.red, bold = true })
hl("Todo", { fg = p.base, bg = p.yellow, bold = true })
hl("Delimiter", { fg = p.overlay2 })

-- markdown
hl("markdownH1", { fg = p.red, bold = true })
hl("markdownH2", { fg = p.peach, bold = true })
hl("markdownH3", { fg = p.yellow, bold = true })
hl("markdownH4", { fg = p.green, bold = true })
hl("markdownH1Delimiter", { fg = p.overlay0 })
hl("markdownH2Delimiter", { fg = p.overlay0 })
hl("markdownH3Delimiter", { fg = p.overlay0 })
hl("markdownCode", { fg = p.teal })
hl("markdownCodeBlock", { fg = p.teal })
hl("markdownListMarker", { fg = p.mauve })
hl("markdownLinkText", { fg = p.blue, underline = true })
hl("markdownUrl", { fg = p.overlay2, italic = true })
hl("markdownBold", { fg = p.peach, bold = true })
hl("markdownItalic", { fg = p.yellow, italic = true })
