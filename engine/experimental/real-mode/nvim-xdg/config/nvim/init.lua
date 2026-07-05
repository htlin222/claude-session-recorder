-- Minimal nvim config for DETERMINISTIC VHS demos, fully self-contained.
--
-- This is NOT loaded via `-u`: render.sh points $XDG_CONFIG_HOME (and
-- $XDG_DATA_HOME / $XDG_STATE_HOME) at this nvim-xdg/ directory before
-- invoking vhs, so plain `nvim <file>` finds THIS as its one and only
-- config. Never reads, never touches, the real ~/.config/nvim — which
-- matters here: an earlier attempt at `-u <initfile>` still let Neovim's
-- own defaults.lua run `filetype plugin on`, and since $XDG_CONFIG_HOME
-- was still the real one, that pulled in a broken personal
-- ftplugin/markdown/autocmd.lua and crashed on any *.md target. Redirecting
-- the whole XDG config/data/state trio sidesteps that at the source: our
-- runtimepath never contains the real config, so there is nothing broken
-- for `filetype plugin on` to find.
vim.o.swapfile = false      -- no leftover .swp -> no swap-recovery prompt
                            -- eating the tape's scripted keystrokes
vim.o.shada = ""            -- don't read/write shada history either
-- autoindent (on by default, even here) makes each typed line inherit the
-- previous line's indent, so literal leading spaces in a `Type` COMPOUND.
vim.o.autoindent = false
vim.o.smartindent = false
vim.o.cindent = false
vim.o.indentexpr = ""
vim.o.expandtab = true
vim.o.number = true
vim.o.laststatus = 2
vim.cmd("syntax on")
vim.cmd("colorscheme catppuccin-mocha")
