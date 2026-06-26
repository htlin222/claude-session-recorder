"""Lesson: rg (ripgrep) — 快又聰明的遞迴搜尋.

Same tool-agnostic engine as jq/grep; only this file + setup.sh are rg-specific.
Each scene teaches ONE everyday rg flag by dissecting a `rg <flags> <pattern>
<path>` command. The explain sentence right before each R() names that scene's
flag token (e.g. the -w scene's pre-R sentence contains "-w"), so the panel
reveal lands in typing-sync. rg is written in Rust and prints identical output on
macOS and Linux, so nothing here is BSD/GNU-sensitive.

NOTE on narration spacing: edge-tts (the zh-TW voice) inserts a pronounced pause
around a space-delimited ASCII flag like " -F " / " --hidden ", and its subtitle
splitter then cuts an extra cue there, desyncing build.py. So flags are written
WITHOUT surrounding spaces (e.g. 「補上-F」) in the spoken sentences; the on-screen
typed command (the hero/R string) keeps normal spacing and is unaffected.
"""
from clipkit import S, R, CLR

SLUG = "rg"
TITLE = "rg (ripgrep) 教學 · 快又聰明的遞迴搜尋"

SCRIPT = [
    CLR(key="rg · 用 Rust 寫成、快又聰明的遞迴搜尋"),
    S("我們每天都在程式碼裡找東西，grep 雖然萬用，但在大專案裡常常又慢、又會掃進一堆不該碰的檔案。"),
    S("rg，也就是 ripgrep，用 Rust 寫成，速度極快，預設行為又聰明。"),
    S("它跨平台、輸出一致，還會自動略過隱藏檔和被忽略規則擋掉的檔案。"),
    S("比起傳統工具，它預設就避開雜訊，速度往往還快上好幾倍。"),
    S("先用 tree 把這支教學用的小專案巡一遍。"),
    S("裡面有原始碼、幾份文件，還有一個用點開頭的隱藏檔，待會都會輪流登場。"),
    R("tree -a --dirsfirst -I 'audio|*.tape|*.json|*.mp4|__pycache__'"),

    CLR(key="最基本：rg 樣式，預設就遞迴搜尋整個資料夾",
        hero="rg TODO", toks=[
        ("rg", "ripgrep 指令本體", "path"),
        ("TODO", "要搜尋的樣式，預設遞迴掃整個資料夾", "star")]),
    S("最基本的用法，就是直接把一個樣式交給 rg，連路徑都不必指定。"),
    S("因為它預設就會從目前資料夾往下，遞迴搜尋每個檔案裡的 TODO。"),
    R("rg TODO"),
    S("一瞬間，它就在五個檔案裡找出六個 TODO，還自動標上了行號與顏色。"),
    S("完全不必先進到每個子資料夾，這就是預設遞迴的方便之處。"),

    CLR(key="-i：忽略大小寫，ERROR 與 error 一網打盡",
        hero="rg -i error src/log.txt", toks=[
        ("-i", "忽略大小寫", "star"),
        ("error", "要搜尋的樣式", "path"),
        ("src/log.txt", "這次只搜這個檔", "path")]),
    S("預設搜尋會區分大小寫，所以小寫的 error 抓不到大寫的那種寫法。"),
    S("想兩種一起抓，就加上-i忽略大小寫。"),
    R("rg -i error src/log.txt"),
    S("現在不論大小寫，error、複數的 errors，連大寫的都被一起撈了出來。"),

    CLR(key="-w：只比對整個單字，避開 errorlog 這種子字串",
        hero="rg -w error src/log.txt", toks=[
        ("-w", "只比對完整的單字邊界", "star"),
        ("error", "要搜尋的樣式", "path"),
        ("src/log.txt", "目標檔", "path")]),
    S("不過放寬之後，有時又會撈到太多。"),
    S("只想要剛好是那個單字，就加上-w比對完整的單字邊界。"),
    R("rg -w error src/log.txt"),
    S("errors 和 errorlog 這類子字串都被排除，只剩獨立成詞的兩行。"),
    S("要精準找一個變數名或關鍵字時，這一招特別實用。"),

    CLR(key="-n：標出行號（rg 在終端機本來就預設顯示）",
        hero="rg -n TODO src/main.py", toks=[
        ("-n", "強制顯示行號", "star"),
        ("TODO", "要搜尋的樣式", "path"),
        ("src/main.py", "目標檔", "path")]),
    S("在終端機裡，rg 本來就會幫每個結果標上行號。"),
    S("但接進管線後行號會消失，這時補上-n就能強制保留。"),
    R("rg -n TODO src/main.py"),
    S("這個檔裡的兩個 TODO，清楚地落在第二行和第八行。"),

    CLR(key="-l：只列出有命中的檔名，不印內容",
        hero="rg -l TODO", toks=[
        ("-l", "只印出包含樣式的檔名", "star"),
        ("TODO", "要搜尋的樣式", "path")]),
    S("有時候我們只想知道哪些檔案中了，根本不在乎內容。"),
    S("這時加上-l，就只印出包含樣式的檔名，一個檔案一行。"),
    R("rg -l TODO"),
    S("五個含有 TODO 的檔名乾淨地列出，很適合再餵給別的指令。"),
    S("例如把這份清單接給編輯器，一次打開所有命中的檔案。"),

    CLR(key="-c：每個檔數出命中幾次",
        hero="rg -c TODO", toks=[
        ("-c", "逐檔數出符合的行數", "star"),
        ("TODO", "要搜尋的樣式", "path")]),
    S("反過來，如果想知道每個檔案各命中幾次呢？"),
    S("把旗標換成-c，就會逐檔數出符合的行數，而不是印出每一行。"),
    R("rg -c TODO"),
    S("有的檔兩筆、有的一筆，關鍵字的分布一目了然。"),

    CLR(key="-t py：只搜尋某種檔案類型",
        hero="rg -t py TODO", toks=[
        ("-t", "依檔案類型過濾", "star"),
        ("py", "Python 這個內建類型", "path"),
        ("TODO", "要搜尋的樣式", "path")]),
    S("在前後端混在一起的專案裡，常常只想搜某一種語言。"),
    S("用-t指定檔案類型、後面接 py，就只在 Python 原始碼裡搜尋。"),
    R("rg -t py TODO"),
    S("文件和純文字筆記都被跳過，只剩兩個程式檔的結果。"),
    S("它內建了上百種類型，常見的程式語言幾乎都涵蓋。"),

    CLR(key="-g：用萬用字元 glob 圈定要搜的檔",
        hero="rg -g '*.md' TODO", toks=[
        ("-g", "用 glob 樣式圈定檔名", "star"),
        ("'*.md'", "只匹配 .md 結尾的檔", "path"),
        ("TODO", "要搜尋的樣式", "path")]),
    S("內建類型不夠用時，也能自己用萬用字元圈定檔名。"),
    S("加上-g再給一個樣式，例如星號點md，就只鎖定那種副檔名。"),
    R("rg -g '*.md' TODO"),
    S("這一次，只有那兩份說明文件被掃到。"),

    CLR(key="-F：把樣式當純字串，不解讀正規表達式",
        hero="rg -F '3.14' src/utils/calc.py", toks=[
        ("-F", "把樣式視為固定純文字", "star"),
        ("'3.14'", "要找的字面字串", "path"),
        ("src/utils/calc.py", "目標檔", "path")]),
    S("預設情況下，樣式會被當成正規表達式，一個句點其實代表任意字元。"),
    S("想原原本本地找一個含點的字串，就用-F把它當成固定純文字。"),
    R("rg -F '3.14' src/utils/calc.py"),
    S("這樣那個句點不再是萬用字元，只會精準對到字面上的數字。"),

    CLR(key="-v：反向，列出「不」含樣式的行",
        hero="rg -v error src/log.txt", toks=[
        ("-v", "反轉比對，留下不符合的行", "star"),
        ("error", "要排除的樣式", "path"),
        ("src/log.txt", "目標檔", "path")]),
    S("有時候我們關心的，反而是沒命中的那些行。"),
    S("補上代表反向的-v，就會列出所有不含樣式的行。"),
    R("rg -v error src/log.txt"),
    S("含有錯誤字樣的行全被濾掉，剩下都是沒出錯的正常紀錄。"),
    S("想從日誌裡濾掉雜訊，或是排除某個模式，都很順手。"),

    CLR(key="--hidden：把預設略過的隱藏檔也納入搜尋",
        hero="rg --hidden secret", toks=[
        ("--hidden", "連用點開頭的隱藏檔一起搜", "star"),
        ("secret", "要搜尋的樣式", "path")]),
    S("還記得開頭那個用點開頭的隱藏檔嗎？"),
    S("它預設會被略過，要在指令裡補上--hidden才會被一起搜。"),
    R("rg --hidden secret"),
    S("於是，連藏起來的隱藏檔，裡頭的內容也被一字不漏地翻了出來。"),

    CLR(key="-C：連同上下文一起印（另有 -A 與 -B）",
        hero="rg -C1 'my error' src/log.txt", toks=[
        ("-C1", "印出命中行的前後各一行脈絡", "star"),
        ("'my error'", "要搜尋的樣式", "path"),
        ("src/log.txt", "目標檔", "path")]),
    S("最後，命中的那一行，常常得連同上下文一起看才有意義。"),
    S("用-C1就能帶出前後各一行脈絡，而只想看單邊則分別有-A和-B。"),
    R("rg -C1 'my error' src/log.txt"),
    S("命中那行的上下各補了一行，這筆錯誤的來龍去脈瞬間清楚起來。"),
    S("從預設的遞迴搜尋，到這一連串好記的旗標，就是平常用 rg 最常派上用場的招式了。"),
]
