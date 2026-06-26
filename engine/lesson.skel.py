"""<TITLE> — the content for this clip (the ONLY file you normally edit).

Everything else in this folder (src/, config.toml) is the vendored engine.
See CLAUDE.md for the build steps and the hard rules. Build the SCRIPT below
from S()/R()/CLR(); token roles -> colour: ord=green, star=peach, path=mauve.
"""
from clipkit import S, R, CLR

SLUG = "myslug"
TITLE = "工具教學 · 一句話描述"

SCRIPT = [
    CLR(key="開場標題"),
    S("開場的一句旁白，介紹今天要教什麼。"),
    R("tool --help"),
    S("先看看它能做什麼。"),

    CLR(key="情境：教某個 flag", hero="tool --flag X", toks=[
        ("tool", "被教的工具", "path"),
        ("--flag", "這個 flag 做什麼", "star"),
        ("X", "參數說明", "path")]),
    S("引入這個情境的一句話。"),
    S("用 --flag 做某事的解說句，句中要出現 --flag。"),
    R("tool --flag X"),
    S("看結果，總結這個情境的一句話。"),
]
