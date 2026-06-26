"""Lesson: rg (ripgrep) — 快又聰明的遞迴搜尋.

Same tool-agnostic engine as jq/grep; only this file + setup.sh are rg-specific.
Each scene teaches ONE everyday rg flag by dissecting a `rg <flags> <pattern>
<path>` command. The explain sentence right before each R() names that scene's
flag token VERBATIM (e.g. the -w scene has an S() containing "-w"), so the panel
reveal lands in typing-sync. rg is written in Rust and prints identical output on
macOS and Linux, so nothing here is BSD/GNU-sensitive. The demo tree lives in
intermediate/ and deliberately uses extensions that dodge .gitignore so rg's
default ignore-filtering never eats a file; only the --hidden scene relies on a
genuinely hidden dotfile.
"""
from clipkit import S, R, CLR

SLUG = "rg"
TITLE = "rg (ripgrep) 教學 · 快又聰明的遞迴搜尋"

SCRIPT = [
    CLR(key="rg · 用 Rust 寫成、快又聰明的遞迴搜尋"),
    S("我們每天都在程式碼裡找東西，grep 雖然萬用，但在大專案裡遞迴搜尋常常又慢、又會掃進一堆不該碰的檔案。"),
    S("rg，也就是 ripgrep，用 Rust 寫成，速度極快，而且預設行為非常聰明。"),
    S("它會自動略過被 gitignore 命中的檔案和隱藏檔，讓結果又乾淨又快。"),
    S("rg 跨平台、輸出一致，在 macOS 和 Linux 上敲同一個指令，看到的結果都一樣。"),
    S("先用 tree 把這支教學用的小專案巡一遍。"),
    S("裡面有一個 src 原始碼資料夾、兩份 Markdown 文件、一個純文字筆記，還有一個用點開頭的隱藏檔，待會都會輪流登場。"),
    R("tree -a --dirsfirst -I 'audio|*.tape|*.json|*.mp4|__pycache__'"),

    CLR(key="最基本：rg 樣式，預設就遞迴搜尋整個資料夾",
        hero="rg TODO", toks=[
        ("rg", "ripgrep 指令本體", "path"),
        ("TODO", "要搜尋的樣式，預設遞迴掃整個資料夾", "star")]),
    S("最基本的用法，就是直接把一個樣式交給 rg，而且連路徑都不必指定。"),
    S("因為 rg 預設就會從目前的資料夾往下，遞迴搜尋每一個檔案。"),
    S("我們就用它來找出散落在專案各處的 TODO 標記。"),
    R("rg TODO"),
    S("一瞬間，它就在五個檔案裡找出六個 TODO，還自動分檔分組、標上行號與顏色。"),

    CLR(key="-i：忽略大小寫，ERROR 與 error 一網打盡",
        hero="rg -i error src/log.txt", toks=[
        ("-i", "忽略大小寫", "star"),
        ("error", "要搜尋的樣式", "path"),
        ("src/log.txt", "這次只搜這個檔", "path")]),
    S("預設的搜尋會區分大小寫，所以小寫的 error 是抓不到大寫 ERROR 的。"),
    S("想把兩種寫法一網打盡，只要加上 -i 讓比對忽略大小寫。"),
    R("rg -i error src/log.txt"),
    S("現在 error、複數的 errors、甚至大寫的 FATAL ERROR，全都被一起撈了出來。"),
    S("處理大小寫不一致的日誌時，這個旗標幾乎是必備。"),

    CLR(key="-w：只比對整個單字，避開 errorlog 這種子字串",
        hero="rg -w error src/log.txt", toks=[
        ("-w", "只比對完整的單字邊界", "star"),
        ("error", "要搜尋的樣式", "path"),
        ("src/log.txt", "目標檔", "path")]),
    S("不過放寬之後，我們有時又會撈到太多東西。"),
    S("如果只想要剛好是某個單字的結果，就加上 -w 比對完整的單字邊界。"),
    R("rg -w error src/log.txt"),
    S("errors 和 errorlog 這類把 error 包在裡面的子字串，這次通通被排除。"),
    S("最後只剩兩行，裡頭的 error 都是堂堂正正、獨立的一個字。"),

    CLR(key="-n：標出行號（rg 在終端機本來就預設顯示）",
        hero="rg -n TODO src/main.py", toks=[
        ("-n", "強制顯示行號", "star"),
        ("TODO", "要搜尋的樣式", "path"),
        ("src/main.py", "目標檔", "path")]),
    S("你可能注意到了，剛剛在終端機裡 rg 本來就會幫每個結果標上行號。"),
    S("但只要把輸出接進管線或寫進檔案，那些行號預設就會消失。"),
    S("想無論如何都保留行號，就明確加上 -n。"),
    R("rg -n TODO src/main.py"),
    S("main.py 裡的兩個 TODO，清楚地落在第二行和第八行。"),

    CLR(key="-l：只列出有命中的檔名，不印內容",
        hero="rg -l TODO", toks=[
        ("-l", "只印出包含樣式的檔名", "star"),
        ("TODO", "要搜尋的樣式", "path")]),
    S("有時候我們根本不在乎命中的內容，只想知道是哪些檔案中了。"),
    S("這時加上 -l，rg 就只印出包含樣式的檔名，一個檔案一行。"),
    R("rg -l TODO"),
    S("五個含有 TODO 的檔名乾淨地列了出來。"),
    S("這份清單很適合再用管線餵給其他指令，例如一次打開全部檔案。"),

    CLR(key="-c：每個檔數出命中幾次",
        hero="rg -c TODO", toks=[
        ("-c", "逐檔數出符合的行數", "star"),
        ("TODO", "要搜尋的樣式", "path")]),
    S("反過來，如果我們想知道每個檔案各命中幾次呢？"),
    S("把旗標換成 -c，rg 就會逐檔數出符合的行數，而不是把每一行印出來。"),
    R("rg -c TODO"),
    S("結果一目了然，main.py 有兩筆，其餘每個檔案各一筆。"),
    S("要快速盤點某個關鍵字在專案裡的分布，這招特別好用。"),

    CLR(key="-t py：只搜尋某種檔案類型",
        hero="rg -t py TODO", toks=[
        ("-t", "依檔案類型過濾", "star"),
        ("py", "Python 這個內建類型", "path"),
        ("TODO", "要搜尋的樣式", "path")]),
    S("在前後端混在一起的專案裡，我們常常只想搜某一種語言的檔案。"),
    S("用 -t 指定檔案類型，後面接 py，就只在 Python 原始碼裡搜尋。"),
    R("rg -t py TODO"),
    S("兩份 Markdown 和那個純文字筆記都被跳過，只剩兩個 .py 檔的結果。"),
    S("rg 內建了上百種類型，從 js、go 到 html 都能直接指定。"),

    CLR(key="-g：用萬用字元 glob 圈定要搜的檔",
        hero="rg -g '*.md' TODO", toks=[
        ("-g", "用 glob 樣式圈定檔名", "star"),
        ("'*.md'", "只匹配 .md 結尾的檔", "path"),
        ("TODO", "要搜尋的樣式", "path")]),
    S("如果內建類型不夠用，也可以自己用萬用字元圈出想搜的檔。"),
    S("加上-g再給一個萬用字元樣式，例如星號點md，就只鎖定副檔名是點md的檔。"),
    R("rg -g '*.md' TODO"),
    S("這一次，只有那兩份說明文件被掃到。"),
    S("這個-g也可以反過來用驚嘆號排除檔案，彈性比固定類型更高。"),

    CLR(key="-F：把樣式當純字串，不解讀正規表達式",
        hero="rg -F '3.14' src/utils/calc.py", toks=[
        ("-F", "把樣式視為固定純文字", "star"),
        ("'3.14'", "要找的字面字串", "path"),
        ("src/utils/calc.py", "目標檔", "path")]),
    S("rg 的樣式預設會被當成正規表達式，所以一個句點其實代表任意一個字元。"),
    S("當你只想老老實實地找一個含點的字串，就用-F把樣式視為固定純文字。"),
    R("rg -F '3.14' src/utils/calc.py"),
    S("這樣那個句點就不再是萬用字元，而是老老實實地比對字面上的數字。"),
    S("搜尋含有大量符號的程式碼或設定值時，用-F就能省去一堆跳脫字元。"),

    CLR(key="-v：反向，列出「不」含樣式的行",
        hero="rg -v error src/log.txt", toks=[
        ("-v", "反轉比對，留下不符合的行", "star"),
        ("error", "要排除的樣式", "path"),
        ("src/log.txt", "目標檔", "path")]),
    S("到目前為止我們都在找有命中的行，但偶爾相反才是重點。"),
    S("想找出沒有命中的那些行，就補上代表反向的-v就好。"),
    R("rg -v error src/log.txt"),
    S("所有含有小寫錯誤字樣的行都被濾掉，剩下的全是沒出錯的正常紀錄。"),
    S("想從日誌裡挑出雜訊、或排除某個模式時，這個旗標很順手。"),

    CLR(key="--hidden：把預設略過的隱藏檔也納入搜尋",
        hero="rg --hidden secret", toks=[
        ("--hidden", "連用點開頭的隱藏檔一起搜", "star"),
        ("secret", "要搜尋的樣式", "path")]),
    S("還記得開頭那個用點開頭的隱藏檔嗎？"),
    S("為了避免雜訊，它預設會直接略過所有隱藏檔。"),
    S("想把它們也一起搜進來，就得在指令裡補上--hidden才行。"),
    R("rg --hidden secret"),
    S("於是，連那個藏起來的隱藏檔，裡頭的內容都被一字不漏地翻了出來。"),
    S("如果連那些被忽略規則擋掉的檔案也想一起搜，還有一個更徹底的--no-ignore可以搭配。"),

    CLR(key="-C：連同上下文一起印（另有 -A 與 -B）",
        hero="rg -C1 'my error' src/log.txt", toks=[
        ("-C1", "印出命中行的前後各一行脈絡", "star"),
        ("'my error'", "要搜尋的樣式", "path"),
        ("src/log.txt", "目標檔", "path")]),
    S("最後，比對到的那一行，常常得連同上下文一起看才有意義。"),
    S("用-C1就能把命中行的前後各一行脈絡一起帶出來，而只想看後面或前面，則分別有-A和-B。"),
    R("rg -C1 'my error' src/log.txt"),
    S("命中的那一行上下各補了一行，這筆錯誤的來龍去脈瞬間清楚起來。"),
    S("從預設的遞迴搜尋，到這一連串好記的旗標，就是平常用 rg 時最常派上用場的招式了。"),
]
