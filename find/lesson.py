"""Lesson: find — 用述詞 (predicate) 在目錄樹裡精準定位檔案.

A second, non-rsync lesson that exercises the SAME engine to prove it is
tool-agnostic: only this file + setup.sh differ from the rsync lesson. The
explain sentences name each predicate literally (-name / -type / -iname /
-size / -maxdepth / -mtime) so the panel reveals it in typing sync.
"""
from clipkit import S, R, CLR

SLUG = "find"
TITLE = "find 教學 · 用述詞精準定位檔案"

SCRIPT = [
    CLR(key="find · 在目錄樹裡找檔案"),
    S("我們有一個叫做 proj 的專案目錄，裡面層層疊疊。"),
    S("先用 tree 看看它長什麼樣子。"),
    R("tree proj"),
    S("有原始碼、文件、紀錄檔，還有一個比較大的資料檔。"),
    S("接下來，我們用 find 一步步把想要的檔案挑出來。"),

    CLR(key="-name 依檔名比對", hero="find proj -name '*.py'", toks=[
        ("proj", "搜尋的起點，從這個目錄往下找", "path"),
        ("-name", "依檔名比對，支援 * 萬用字元", "star"),
        ("'*.py'", "只挑副檔名是 .py 的檔案", "path")]),
    S("第一招，也是最常用的，就是依檔名搜尋。"),
    S("從 proj 出發，用 -name 比對檔名，找出所有的 .py 檔。"),
    R("find proj -name '*.py'"),
    S("整棵目錄樹裡的 Python 檔，不管藏多深，都被列了出來。"),

    CLR(key="-type d 只看目錄", hero="find proj -type d", toks=[
        ("proj", "搜尋的起點目錄", "path"),
        ("-type d", "只列出目錄，d 就是 directory", "star")]),
    S("有時候我們只想看資料夾，不想看到檔案。"),
    S("這次用 -type d，只列出 proj 底下的目錄。"),
    R("find proj -type d"),
    S("結果只剩一個個資料夾，檔案都被濾掉了。"),

    CLR(key="-iname 忽略大小寫", hero="find proj -iname 'readme*'", toks=[
        ("proj", "搜尋的起點目錄", "path"),
        ("-iname", "跟 -name 一樣，但忽略大小寫", "star"),
        ("'readme*'", "開頭是 readme 的檔名，不分大小寫", "path")]),
    S("檔名大小寫記不清楚時，就改用 -iname。"),
    S("用 -iname 比對 readme 開頭的檔名，大寫小寫都會一起抓到。"),
    R("find proj -iname 'readme*'"),
    S("你看，README 跟 readme 兩種寫法，都被找出來了。"),

    CLR(key="-size 依大小過濾", hero="find proj -type f -size +1M", toks=[
        ("proj", "搜尋的起點目錄", "path"),
        ("-type f", "只看一般檔案", "ord"),
        ("-size", "依檔案大小過濾", "star"),
        ("+1M", "大於 1 MB，加號代表「以上」", "path")]),
    S("想揪出佔空間的大檔呢？"),
    S("先用 -type f 只看檔案，再加上 -size，配合 1M 找出大於 1MB 的檔案。"),
    R("find proj -type f -size +1M"),
    S("只有那個大的資料檔，超過了門檻被列出來。"),

    CLR(key="-maxdepth 限制深度", hero="find proj -maxdepth 1", toks=[
        ("proj", "搜尋的起點目錄", "path"),
        ("-maxdepth 1", "只往下找一層，不深入子目錄", "star")]),
    S("預設的 find 會把所有子目錄一路找到底。"),
    S("加上 -maxdepth 1，就只看 proj 的第一層，不再往下鑽。"),
    R("find proj -maxdepth 1"),
    S("這次只列出最上層的項目，深處的檔案都沒有出現。"),

    CLR(key="-mtime 依修改時間", hero="find proj -type f -mtime -1", toks=[
        ("proj", "搜尋的起點目錄", "path"),
        ("-type f", "只看一般檔案", "ord"),
        ("-mtime -1", "最近 1 天內被修改過，減號代表「以內」", "star")]),
    S("最後，找出最近剛動過的檔案。"),
    S("用 -type f 只看檔案，再用 -mtime -1，篩出最近一天內改過的檔案。"),
    R("find proj -type f -mtime -1"),
    S("剛剛更新過的那幾個檔案，正好被挑了出來。"),
    S("掌握這幾個述詞，你就能用 find 精準定位任何檔案了。"),
]
