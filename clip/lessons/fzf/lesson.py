"""Lesson: fzf — 用「過濾模式」(-f) 學模糊搜尋，全程不開 TUI.

A third lesson on the SAME tool-agnostic engine. Everything fzf-specific lives
here and in the sibling setup.sh; the engine (src/build.py + src/overlay.py)
never learns what fzf is.

關鍵設計：全程只用 fzf 的「非互動過濾模式」 -f / --filter，讓 fzf 讀 stdin、印出
依分數排序的比對結果、自己結束、不開全螢幕介面 —— 每個 R() 都餵固定輸入
（pool.txt / data.csv / proj/），輸出穩定可重現。每一幕的 star token 就是當場要教
的旗標或運算子，旁白會逐字唸到它，面板才會貼著打字浮現。
"""
from lesson import S, R, CLR

SLUG = "fzf"
TITLE = "fzf 教學 · 用過濾模式 (-f) 玩轉模糊搜尋"

SCRIPT = [
    # ---- intro tour (bare CLR, no hero) ----
    CLR(key="fzf · 用過濾模式學模糊搜尋（不開 TUI）"),
    S("fzf 是一個命令列的模糊搜尋器，平常會開一個全螢幕的互動視窗。"),
    S("但這堂課，我們全程只用它的過濾模式，讓每一次輸出都穩定又好示範。"),
    S("先準備好幾份固定的資料，一份是 pool.txt，裡面是單字和路徑的清單。"),
    S("另一份是 data.csv，還有一個叫 proj 的小檔案樹。"),
    S("我們就用這些固定的輸入，一步步把 fzf 的過濾本領拆開來看。"),

    # ---- 1) -f filter mode ----
    CLR(key="-f 過濾模式：字元依序就算命中",
        hero="cat pool.txt | fzf -f 'sap'", toks=[
        ("fzf", "命令列模糊搜尋器", "path"),
        ("-f", "filter 模式：只過濾、印結果、不開全螢幕", "star"),
        ("'sap'", "查詢字串", "path")]),
    S("第一招，就是最基本的過濾模式。"),
    S("我們用 cat 把 pool.txt 倒進管線，再加上關鍵的 -f，讓 fzf 只印出比對結果就結束。"),
    R("cat pool.txt | fzf -f 'sap'"),
    S("你會發現，只要查詢的字元依序出現，就算中間不連續也算命中。"),

    # ---- 2) score sort + head ----
    CLR(key="分數排序：最佳比對排最前面",
        hero="cat pool.txt | fzf -f 'ap' | head -3", toks=[
        ("'ap'", "查詢字串", "path"),
        ("head -3", "只留下分數最高的前三筆", "star")]),
    S("模糊比對的結果，其實是有分數排序的。"),
    S("我們改用 ap 當查詢，再用 head -3 只留下排在最前面的三筆。"),
    R("cat pool.txt | fzf -f 'ap' | head -3"),
    S("排在最上面的，就是 fzf 認為最貼近、分數最高的比對。"),

    # ---- 3) exact match (--exact; 'word equivalent) ----
    CLR(key="精確比對：--exact（等同前置單引號 'word）",
        hero="cat pool.txt | fzf --exact -f 'main'", toks=[
        ("fzf", "模糊搜尋器", "path"),
        ("--exact", "整段查詢都要精確、連續出現", "star"),
        ("'main'", "查詢字串", "path")]),
    S("如果不想要模糊，只想要精確比對呢？"),
    S("加上 --exact，就要求查詢字串必須完整、連續地出現，效果等同在字前加一個單引號。"),
    R("cat pool.txt | fzf --exact -f 'main'"),
    S("這次只剩下真的含有 main 這整段字的項目。"),
    S("那些只是字元剛好依序出現的，全都被擋在外面了。"),

    # ---- 4) ^prefix anchor ----
    CLR(key="^src 前綴錨點",
        hero="cat pool.txt | fzf -f '^src'", toks=[
        ("fzf", "模糊搜尋器", "path"),
        ("^src", "脫字號＝前綴錨點，開頭必須是 src", "star")]),
    S("接著看 extended-search 的錨點運算子。"),
    S("用脫字號開頭的 ^src，表示比對的開頭一定要是 src。"),
    R("cat pool.txt | fzf -f '^src'"),
    S("只有路徑開頭是 src 的那幾筆被留了下來。"),
    S("錨在開頭，就能精準地框住一整類前綴。"),

    # ---- 5) suffix$ anchor ----
    CLR(key=".py$ 後綴錨點",
        hero="cat pool.txt | fzf -f '.py$'", toks=[
        ("fzf", "模糊搜尋器", "path"),
        (".py$", "錢字號＝後綴錨點，結尾必須是 .py", "star")]),
    S("有開頭的錨點，當然也有結尾的錨點。"),
    S("在字尾加一個錢字號，寫成 .py$，就只比對結尾是 .py 的項目。"),
    R("cat pool.txt | fzf -f '.py$'"),
    S("所有的 Python 檔，乾乾淨淨地被挑了出來。"),

    # ---- 6) !negation ----
    CLR(key="!test 排除（negation）",
        hero="cat pool.txt | fzf -f '!test'", toks=[
        ("fzf", "模糊搜尋器", "path"),
        ("!test", "驚嘆號＝排除，濾掉含有 test 的項目", "star")]),
    S("有時候我們想反過來，排除掉某些東西。"),
    S("在查詢前面加一個驚嘆號，寫成 !test，就會濾掉所有含有 test 的項目。"),
    R("cat pool.txt | fzf -f '!test'"),
    S("你看，那些測試檔，全都被排除在外了。"),
    S("negation 很適合用來把雜訊一次清掉。"),

    # ---- 7) OR ----
    CLR(key="md$ | py$ 任一條件 (OR)",
        hero="cat pool.txt | fzf -f 'md$ | py$'", toks=[
        ("fzf", "模糊搜尋器", "path"),
        ("md$ | py$", "直線＝或，符合任一條件就算數", "star")]),
    S("多個條件，也可以用「或」串起來。"),
    S("中間放一個直線，寫成 md$ | py$，代表結尾是 md 或者是 py 都算數。"),
    R("cat pool.txt | fzf -f 'md$ | py$'"),
    S("兩種副檔名的檔案，這一次一起被收了進來。"),

    # ---- 8) -i ignore case ----
    CLR(key="-i 忽略大小寫",
        hero="cat pool.txt | fzf -i -f 'readme'", toks=[
        ("-i", "強制忽略大小寫", "star"),
        ("'readme'", "查詢字串", "path")]),
    S("再來談談大小寫。"),
    S("加上 -i，就強制忽略大小寫，readme 不管大寫小寫都會一起抓到。"),
    R("cat pool.txt | fzf -i -f 'readme'"),
    S("大寫的 README 和小寫的 readme，果然都出現了。"),
    S("當你不確定來源檔名怎麼拼時，這個選項特別好用。"),

    # ---- 9) +i force case-sensitive ----
    CLR(key="+i 強制區分大小寫",
        hero="cat pool.txt | fzf +i -f 'README'", toks=[
        ("+i", "強制區分大小寫", "star"),
        ("'README'", "查詢字串", "path")]),
    S("反過來，如果想嚴格區分大小寫呢？"),
    S("改用加號的 +i，強制區分大小寫，這次就只認大寫的 README。"),
    R("cat pool.txt | fzf +i -f 'README'"),
    S("小寫那一筆被擋掉了，只剩大小寫完全相符的結果。"),

    # ---- 10) --tac reverse input ----
    CLR(key="--tac 反轉輸入順序",
        hero="cat pool.txt | fzf --tac -f 'log'", toks=[
        ("--tac", "先把輸入每一行反轉再比對", "star"),
        ("'log'", "查詢字串", "path")]),
    S("fzf 也能調整讀入資料的順序。"),
    S("加上 --tac，會先把輸入的每一行反轉過來，再進行比對。"),
    R("cat pool.txt | fzf --tac -f 'log'"),
    S("同樣的幾筆比對結果，出現的順序整個顛倒了過來。"),
    S("處理像日誌這種由舊到新的輸入時，這招很方便。"),

    # ---- 11) --nth field matching ----
    CLR(key="--nth 只比對指定欄位",
        hero="cat data.csv | fzf -d , --nth 2 -f 'alice'", toks=[
        ("-d ,", "以逗號當作欄位分隔", "ord"),
        ("--nth 2", "只拿第二欄來比對", "star"),
        ("'alice'", "查詢字串", "path")]),
    S("如果輸入是有欄位的資料呢？"),
    S("這份 CSV 先用 -d , 切出欄位，再用 --nth 2 告訴 fzf 只拿第二欄來比對。"),
    R("cat data.csv | fzf -d , --nth 2 -f 'alice'"),
    S("只有第二欄真的叫 alice 的那一列被選中了。"),
    S("第三欄雖然也出現 alice，但因為不在比對範圍內，就被忽略掉。"),

    # ---- 12) --no-sort ----
    CLR(key="--no-sort 保留原始輸入順序",
        hero="cat pool.txt | fzf --no-sort -f 'py'", toks=[
        ("--no-sort", "不依分數排序，保留輸入順序", "star"),
        ("'py'", "查詢字串", "path")]),
    S("預設的 fzf 會幫你依分數重新排序。"),
    S("但有時你想保留資料原本的順序，就加上 --no-sort。"),
    R("cat pool.txt | fzf --no-sort -f 'py'"),
    S("結果照著輸入原來的排列出現，完全沒有被重排過。"),
    S("當輸入本身的順序就有意義時，這個選項就派得上用場。"),

    # ---- 13) real pipeline: find | fzf ----
    CLR(key="真實管線：find 的輸出接給 fzf",
        hero="find proj -type f | fzf -f 'srcmain'", toks=[
        ("find proj -type f", "列出專案裡所有檔案", "star"),
        ("fzf", "把路徑交給 fzf 過濾", "path"),
        ("'srcmain'", "模糊查詢", "path")]),
    S("最後，我們把它接回真實的工作流。"),
    S("用 find proj -type f 列出專案裡所有檔案，再用管線交給 fzf 過濾。"),
    R("find proj -type f | fzf -f 'srcmain'"),
    S("fzf 立刻從一堆路徑裡，挑出我們要的那一個檔案。"),
    S("即使查詢字元散落在路徑各處，模糊比對還是一次命中。"),
    S("從今天起，你就能用過濾模式，把 fzf 的模糊搜尋玩得又準又穩。"),
]
