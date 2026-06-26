"""Lesson: sed — 用串流編輯器 (stream editor) 一行指令即時改文字.

Third lesson on the same tool-agnostic engine. Everything flows through
`cat notes.txt | sed '...'` over stdin/stdout — no -i in-place edit (BSD vs GNU
syntax differs), every R() is deterministic, non-interactive and self-terminating.
One scenario = one idea; the scene's star token is named VERBATIM in the sentence
right before its R() so the panel reveal lands in typing-sync. Target: BSD sed
(macOS built-in). Env built by the sibling setup.sh (a 7-line notes.txt).
"""
from lesson import S, R, CLR

SLUG = "sed"
TITLE = "sed 教學 · 用串流編輯器即時改文字"

SCRIPT = [
    CLR(key="sed · 串流編輯器，一行指令改文字"),
    S("sed 是 stream editor，串流編輯器，專門用一行指令批次改文字。"),
    S("它把文字一行一行讀進來，照你的規則改完，再從另一端吐出去。"),
    S("我們準備了一個小檔案 notes.txt，先用 cat 把它印出來看看。"),
    R("cat notes.txt"),
    S("裡面有重複的字、混合大小寫、兩個日期，還有一行待辦事項。"),
    S("接下來，我們把 notes.txt 餵給 sed，一個情境學一招。"),

    CLR(key="s/old/new/ 取代第一個符合", hero="cat notes.txt | sed 's/red/blue/'",
        toks=[
        ("cat notes.txt", "讀出檔案內容，用管線送給 sed", "path"),
        ("s/red/blue/", "取代指令：把 red 換成 blue", "star")]),
    S("第一招，也是最核心的，就是取代文字。"),
    S("取代的語法是 s 斜線 舊字 斜線 新字 斜線，sed 會逐行套用。"),
    S("這次用 s/red/blue/，把每行第一個 red 換成 blue。"),
    R("cat notes.txt | sed 's/red/blue/'"),
    S("注意，每行只有第一個 red 被換掉，後面的 red 還留著。"),

    CLR(key="/g 取代整行所有符合", hero="cat notes.txt | sed 's/red/blue/g'", toks=[
        ("cat notes.txt", "讀檔送進 sed", "path"),
        ("s/red/blue", "一樣是把 red 換成 blue", "path"),
        ("/g", "全域旗標，整行每個符合都換", "star")]),
    S("可是一行裡如果有好幾個 red，預設只會換掉第一個。"),
    S("想要全部換掉，就得加上全域旗標。"),
    S("在 s/red/blue 結尾補上 /g，整行所有的 red 都會一起換。"),
    R("cat notes.txt | sed 's/red/blue/g'"),
    S("這下子，同一行裡的 red 全部變成 blue 了。"),

    CLR(key="/I 比對時忽略大小寫", hero="cat notes.txt | sed 's/green/lime/I'", toks=[
        ("cat notes.txt", "讀檔送進 sed", "path"),
        ("s/green/lime", "把 green 換成 lime", "path"),
        ("/I", "忽略大小寫的比對旗標", "star")]),
    S("有時候同一個字，大小寫寫法並不一致。"),
    S("我們可以讓比對的時候忽略大小寫。"),
    S("在替換結尾加上 /I，sed 比對 green 時就不分大小寫。"),
    R("cat notes.txt | sed 's/green/lime/I'"),
    S("原本大寫開頭的 Green，因為忽略大小寫也被換成了 lime。"),

    CLR(key="& 在替換裡引用整段匹配", hero="cat notes.txt | sed 's/cat/[&]/'", toks=[
        ("cat notes.txt", "讀檔送進 sed", "path"),
        ("s/cat/", "比對到 cat 這個字", "path"),
        ("&", "在替換字串裡代表整段匹配", "star")]),
    S("替換的時候，常常想把原本比對到的字一起保留。"),
    S("sed 提供一個特別符號，用來代表整段匹配。"),
    S("這時用 & 就能在替換字串裡引用整段匹配。"),
    R("cat notes.txt | sed 's/cat/[&]/'"),
    S("你看，原本的 cat 被保留下來，外面多了一對中括號。"),

    CLR(key="-e 串接多個指令",
        hero="cat notes.txt | sed -e 's/red/blue/g' -e 's/dog/wolf/'", toks=[
        ("cat notes.txt", "讀檔送進 sed", "path"),
        ("-e", "串接第一個指令", "star"),
        ("'s/red/blue/g'", "第一個取代，全域換 red", "path"),
        ("-e", "再串接第二個指令", "ord"),
        ("'s/dog/wolf/'", "第二個取代，換掉 dog", "path")]),
    S("一條 sed 指令，常常想一次做好幾件事。"),
    S("這時不必開好幾個管線，用旗標串接起來就好。"),
    S("第一個 -e 把 red 換成 blue，第二個 -e 再把 dog 換成 wolf。"),
    R("cat notes.txt | sed -e 's/red/blue/g' -e 's/dog/wolf/'"),
    S("紅色全變藍色，第一隻 dog 也換成了 wolf。"),

    CLR(key="-E 啟用擴充正則表達式",
        hero="cat notes.txt | sed -E 's/(cat|dog)/pet/g'", toks=[
        ("cat notes.txt", "讀檔送進 sed", "path"),
        ("-E", "啟用擴充正則表達式", "star"),
        ("(cat|dog)", "括號加直線：cat 或 dog 都算符合", "path")]),
    S("sed 預設的正則比較陽春，分組和選擇要加跳脫很麻煩。"),
    S("換成擴充正則，寫起來就乾淨多了。"),
    S("加上 -E 啟用擴充正則表達式，括號和直線可以直接用。"),
    R("cat notes.txt | sed -E 's/(cat|dog)/pet/g'"),
    S("cat 和 dog 都被這個樣式抓到，一起換成了 pet。"),

    CLR(key="\\1 反向參照括號抓到的內容",
        hero="cat notes.txt | sed -E 's/([0-9]+)-([0-9]+)-([0-9]+)/\\3\\/\\2\\/\\1/'",
        toks=[
        ("cat notes.txt", "讀檔送進 sed", "path"),
        ("-E", "擴充正則才好寫分組", "ord"),
        ("([0-9]+)-([0-9]+)-([0-9]+)", "把日期三段數字各自分組", "path"),
        ("\\1", "反向參照：引用第一組抓到的內容", "star")]),
    S("擴充正則還有一個殺手鐧，叫做反向參照。"),
    S("我們把日期的三段數字，各自用括號分成一組。"),
    S("一樣靠 -E 擴充正則，這裡的 \\1 會引用第一組括號抓到的數字。"),
    R("cat notes.txt | sed -E 's/([0-9]+)-([0-9]+)-([0-9]+)/\\3\\/\\2\\/\\1/'"),
    S("年、月、日的順序，就這樣被對調重組了。"),

    CLR(key="-n 搭配 p 只印需要的行", hero="cat notes.txt | sed -n '/date/p'", toks=[
        ("cat notes.txt", "讀檔送進 sed", "path"),
        ("-n", "安靜模式，關掉自動輸出", "star"),
        ("/date/", "位址：符合 date 的行", "path"),
        ("p", "印出目前這一行", "star")]),
    S("到目前為止，sed 都會把每一行都印出來。"),
    S("如果只想看特定幾行，就要先把自動輸出關掉。"),
    S("用 -n 關掉自動輸出，再用 p 只印出符合 date 的那行。"),
    R("cat notes.txt | sed -n '/date/p'"),
    S("整個檔案裡，只有提到 date 的那兩行被印了出來。"),

    CLR(key="1p 與 $p 抓第一行和最後一行",
        hero="cat notes.txt | sed -n '1p;$p'", toks=[
        ("cat notes.txt", "讀檔送進 sed", "path"),
        ("-n", "安靜模式，關掉自動輸出", "ord"),
        ("1p", "行位址 1，印出第一行", "star"),
        ("$p", "錢字號代表最後一行，印出它", "star")]),
    S("行號也可以當作位址，直接點名某一行。"),
    S("我們來抓檔案的第一行和最後一行。"),
    S("同樣搭配 -n，用 1p 抓第一行，再用 $p 抓最後一行。"),
    R("cat notes.txt | sed -n '1p;$p'"),
    S("頭尾兩行被挑了出來，中間的內容全部略過。"),

    CLR(key="2,4p 用範圍位址取一段", hero="cat notes.txt | sed -n '2,4p'", toks=[
        ("cat notes.txt", "讀檔送進 sed", "path"),
        ("-n", "安靜模式，關掉自動輸出", "ord"),
        ("2,4p", "範圍位址：第二到第四行都印", "star")]),
    S("位址也可以是一個範圍，框出連續的好幾行。"),
    S("範圍的寫法是起始行，逗號，再接結束行。"),
    S("再搭配 -n，用 2,4p 這個範圍位址，把第二到第四行一次印出。"),
    R("cat notes.txt | sed -n '2,4p'"),
    S("第二、三、四這三行，剛好被框了出來。"),

    CLR(key="4,5 s/// 只在指定行做取代",
        hero="cat notes.txt | sed '4,5 s/date/DATE/'", toks=[
        ("cat notes.txt", "讀檔送進 sed", "path"),
        ("4,5", "位址限定：只作用在第四到第五行", "star"),
        ("s/date/DATE/", "把 date 換成大寫 DATE", "path")]),
    S("位址不只能搭配印出，也能限定取代的範圍。"),
    S("把位址寫在取代指令前面，就只會作用在那幾行。"),
    S("這次在取代前面加上 4,5，只在第四到第五行把 date 換成大寫。"),
    R("cat notes.txt | sed '4,5 s/date/DATE/'"),
    S("指定範圍裡，第五行的 date 被改成了大寫 DATE，其他行原封不動。"),

    CLR(key="d 刪除符合的整行", hero="cat notes.txt | sed '/TODO/d'", toks=[
        ("cat notes.txt", "讀檔送進 sed", "path"),
        ("/TODO/", "位址：符合 TODO 的行", "path"),
        ("d", "刪除指令，把整行從輸出移除", "star")]),
    S("最後一招，是直接把整行刪掉。"),
    S("刪除用的指令很短，就是一個字母。"),
    S("只要在位址後面接上 d，符合的整行就會從輸出被刪掉。"),
    R("cat notes.txt | sed '/TODO/d'"),
    S("那行待辦事項 TODO，就這樣從輸出裡消失了。"),
    S("十二個情境走完，你已經能用 sed 一行指令搞定大部分文字處理了。"),
]
