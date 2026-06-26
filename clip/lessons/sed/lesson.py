"""Lesson: GNU sed — 全程用 gsed 串流編輯器一行改文字.

Same tool-agnostic engine, but this lesson deliberately teaches GNU sed and runs
EVERY command through `gsed` so the on-screen output matches what a Linux learner
sees. macOS ships BSD sed, whose \\b \\w \\+ and the `-i` syntax differ; the intro
says so and tells you to `brew install gnu-sed`. Everything flows through
`cat notes.txt | gsed '...'` over stdin/stdout — no `-i` in-place edit — so every
R() is deterministic, non-interactive and self-terminating. One scenario = one
idea; the scene's star token is named VERBATIM in a sentence so the panel reveal
lands in typing-sync. Env built by the sibling setup.sh (a 7-line notes.txt).
"""
from lesson import S, R, CLR

SLUG = "sed"
TITLE = "GNU sed 教學 · 用 gsed 串流編輯器一行改文字"

SCRIPT = [
    CLR(key="sed 是什麼？Linux 用 sed，macOS 請用 gsed"),
    S("sed 是 Linux 上標準的串流編輯器，能在管線裡一行指令就把文字改好。"),
    S("不過 macOS 內建的是 BSD 版本的 sed，行為跟 Linux 並不完全一樣。"),
    S("像單字邊界這類寫法，BSD sed 並不支援，輸出會跟教材對不上。"),
    S("所以這堂課全程改用 gsed，請先用 brew install gnu-sed 把它裝起來。"),
    S("我們先看看待會兒要操作的範例檔 notes.txt。"),
    R("cat notes.txt"),
    S("裡面有重複的 red、大小寫混合的 green、兩個日期，還有一行 TODO。"),

    CLR(key="s/old/new/ 取代每行第一個符合",
        hero="cat notes.txt | gsed 's/red/blue/'", toks=[
        ("cat notes.txt", "讀出檔案，用管線送進 gsed", "path"),
        ("gsed", "在 macOS 用 gsed 等於 GNU sed", "ord"),
        ("s/red/blue/", "取代指令：把每行第一個 red 換成 blue", "star")]),
    S("第一招，也是最核心的，就是用取代指令改字。"),
    S("我們用 gsed 執行 s/red/blue/，把每行第一個出現的 red 換成 blue。"),
    R("cat notes.txt | gsed 's/red/blue/'"),
    S("注意每一行只有第一個 red 被換掉，後面重複的 red 還留著。"),
    S("這就是 s 取代的預設行為，逐行而且只動第一個。"),

    CLR(key="/g 全域旗標，整行全部取代",
        hero="cat notes.txt | gsed 's/red/blue/g'", toks=[
        ("cat notes.txt", "讀檔送進 gsed", "path"),
        ("gsed", "GNU sed", "ord"),
        ("s/red/blue", "一樣是把 red 換成 blue", "path"),
        ("/g", "全域旗標，整行每個都換", "star")]),
    S("剛剛只換第一個，那如果想換整行所有的呢？"),
    S("在 gsed 的取代結尾補上 /g 旗標，就會變成全域取代。"),
    R("cat notes.txt | gsed 's/red/blue/g'"),
    S("這一次，那行裡的每個 red 都一起變成 blue 了。"),
    S("這個 /g 代表 global，是 sed 裡最常用的旗標之一。"),

    CLR(key="s///I 比對時忽略大小寫",
        hero="cat notes.txt | gsed 's/green/lime/gI'", toks=[
        ("cat notes.txt", "讀檔送進 gsed", "path"),
        ("gsed", "GNU sed", "ord"),
        ("/g", "全域取代", "ord"),
        ("I", "I 旗標：比對時忽略大小寫", "star")]),
    S("我們檔案裡的 green，有 green、Green、GREEN 三種大小寫。"),
    S("用 gsed 取代時加上 /g 全域，再補一個 I 旗標就會忽略大小寫。"),
    R("cat notes.txt | gsed 's/green/lime/gI'"),
    S("三種大小寫的 green，整行通通被換成了 lime。"),
    S("有了 I 這個旗標，比對時就不必再管大小寫。"),

    CLR(key="& 在替換裡引用整段匹配",
        hero="cat notes.txt | gsed 's/cat/[&]/'", toks=[
        ("cat notes.txt", "讀檔送進 gsed", "path"),
        ("gsed", "GNU sed", "ord"),
        ("s/cat/", "比對到 cat 這個字", "path"),
        ("&", "在替換字串裡代表整段匹配", "star")]),
    S("取代的時候，常常想把原本比對到的字一起留著。"),
    S("在 gsed 的替換字串裡，用 & 就能代表剛剛比對到的整段內容。"),
    R("cat notes.txt | gsed 's/cat/[&]/'"),
    S("你看，原本的 cat 被保留，外面多了一對中括號。"),
    S("有了 & 這個符號，就不必把比對到的字再重打一次。"),

    CLR(key="-E 啟用擴充正則表達式",
        hero="cat notes.txt | gsed -E 's/(cat|dog)/pet/g'", toks=[
        ("cat notes.txt", "讀檔送進 gsed", "path"),
        ("gsed", "GNU sed", "ord"),
        ("-E", "啟用擴充正則，括號與直線免跳脫", "star"),
        ("(cat|dog)", "cat 或 dog 都算符合", "path")]),
    S("接下來進入正則表達式的世界。"),
    S("gsed 預設的正則比較陽春，分組和選擇都得加跳脫很麻煩。"),
    S("加上 -E 啟用擴充正則，括號和直線就能直接寫，把 cat 或 dog 都換成 pet。"),
    R("cat notes.txt | gsed -E 's/(cat|dog)/pet/g'"),
    S("一個 cat、一個 dog，都被這個樣式抓到換成了 pet。"),

    CLR(key="\\1 反向參照括號抓到的內容",
        hero="cat notes.txt | gsed -E 's/([0-9]+)-([0-9]+)-([0-9]+)/\\3\\2\\1/'",
        toks=[
        ("cat notes.txt", "讀檔送進 gsed", "path"),
        ("gsed", "GNU sed", "ord"),
        ("-E", "擴充正則才好分組", "ord"),
        ("([0-9]+)", "用括號抓出一段數字", "path"),
        ("\\1", "反向參照：引用第一組括號的內容", "star")]),
    S("擴充正則還有一個殺手鐧，叫做反向參照。"),
    S("我們用 gsed -E 先把日期的三段數字，各自用括號分成一組。"),
    S("接著在替換字串用 \\1 引用第一組，再把三組數字對調順序。"),
    R("cat notes.txt | gsed -E 's/([0-9]+)-([0-9]+)-([0-9]+)/\\3\\2\\1/'"),
    S("原本年、月、日的順序，就這樣被對調重組了。"),

    CLR(key="\\b 整字比對（GNU 專屬，BSD 不支援）",
        hero="cat notes.txt | gsed 's/\\bcat\\b/fish/g'", toks=[
        ("cat notes.txt", "讀檔送進 gsed", "path"),
        ("gsed", "GNU sed", "ord"),
        ("\\bcat\\b", "用 \\b 框住，只比對獨立的單字 cat", "star"),
        ("/g", "全域取代", "ord")]),
    S("還記得剛剛 category 裡面的 cat，也一起被換掉了嗎？"),
    S("這次用 gsed 搭配 GNU 專屬的 \\b 單字邊界，把樣式寫成 \\bcat\\b。"),
    S("再加上 /g 全域取代，category 裡的 cat 就不會被波及。"),
    R("cat notes.txt | gsed 's/\\bcat\\b/fish/g'"),
    S("只有獨立的單字 cat 變成了 fish，category 完好無缺。"),

    CLR(key="-n 搭配 p 只印需要的行",
        hero="cat notes.txt | gsed -n '/date/p'", toks=[
        ("cat notes.txt", "讀檔送進 gsed", "path"),
        ("gsed", "GNU sed", "ord"),
        ("-n", "安靜模式，關掉每行自動印出", "star"),
        ("/date/", "只在符合 date 的行", "path"),
        ("p", "p 指令：把這行印出來", "star")]),
    S("到目前為止，gsed 都會把每一行都印出來。"),
    S("如果只想看特定幾行，就先用 -n 安靜模式關掉自動輸出。"),
    S("再用 p 指令，只把符合 date 的那幾行印出來。"),
    R("cat notes.txt | gsed -n '/date/p'"),
    S("整個檔案裡，只有提到 date 的那兩行被留了下來。"),

    CLR(key="2p 用單行位址點名某一行",
        hero="cat notes.txt | gsed -n '2p'", toks=[
        ("cat notes.txt", "讀檔送進 gsed", "path"),
        ("gsed", "GNU sed", "ord"),
        ("-n", "安靜模式", "ord"),
        ("2p", "行號位址：只印第 2 行", "star")]),
    S("除了用樣式比對，行號本身也可以當位址，直接點名某一行。"),
    S("我們一樣用 gsed -n 關掉自動輸出，再指定位址 2p。"),
    S("這裡的 2p 意思就是，只把第 2 行印出來。"),
    R("cat notes.txt | gsed -n '2p'"),
    S("畫面準確地只留下了第 2 行。"),

    CLR(key="2,4p 用範圍位址取一段",
        hero="cat notes.txt | gsed -n '2,4p'", toks=[
        ("cat notes.txt", "讀檔送進 gsed", "path"),
        ("gsed", "GNU sed", "ord"),
        ("-n", "安靜模式", "ord"),
        ("2,4p", "範圍位址：第 2 到第 4 行都印", "star")]),
    S("單一行號可以點名，那連續一整段呢？"),
    S("把位址寫成 2,4p，用逗號就能表示一個範圍。"),
    S("我們再用 gsed -n 搭配這個範圍位址，一次取出中間那幾行。"),
    R("cat notes.txt | gsed -n '2,4p'"),
    S("第 2、第 3、第 4 行，連續被印了出來。"),

    CLR(key="d 刪除符合的整行（會移除內容，最後示範）",
        hero="cat notes.txt | gsed '/TODO/d'", toks=[
        ("cat notes.txt", "讀檔送進 gsed", "path"),
        ("gsed", "GNU sed", "ord"),
        ("/TODO/", "位址：符合 TODO 的行", "path"),
        ("d", "d 指令：把整行從輸出刪掉", "star")]),
    S("最後一招會真的移除內容，所以放在最後示範。"),
    S("我們用 gsed 配上位址，再接一個 d 指令，刪掉符合的整行。"),
    S("這次比對含有 TODO 的那一行，把它整行刪除。"),
    R("cat notes.txt | gsed '/TODO/d'"),
    S("輸出裡那行 TODO 不見了，其餘內容原封不動。"),
    S("提醒一下，這裡只是把結果印到畫面，要加上 -i 才會真的寫回檔案，請務必小心。"),
    S("這一連串情境走完，你已經能用 gsed 一行指令搞定大部分的文字處理了。"),
]
