"""Lesson: grep — 用樣式 (pattern) 在文字裡精準命中.

A third lesson exercising the SAME tool-agnostic engine. Every explain sentence
names its flag literally (-i / -n / -c / -v / -w / -o / -E / -r / -rl / -A 1 /
-C 1) so the side panel reveals each token in typing-sync. The commands all feed
a fixed sample tree (logs/app.log, logs/access.log, src/) built by setup.sh, so
the output is stable, non-interactive and self-terminating.
"""
from clipkit import S, R, CLR

SLUG = "grep"
TITLE = "grep 教學 · 用樣式搜尋在文字裡精準命中"

SCRIPT = [
    CLR(key="grep · 用樣式在文字裡搜尋"),
    S("grep 是終端機裡最常用的搜尋工具，它把含有某個樣式的每一行挑出來。"),
    S("開始之前，先認識一下我們的範例資料夾。"),
    R("tree logs src"),
    S("有一個 logs 目錄，裡面放著應用程式的紀錄檔，還有一個 src 原始碼目錄。"),
    S("我們主要會搜尋的，是這份 app.log 紀錄檔。"),
    R("cat logs/app.log"),
    S("裡面混著 INFO、WARN、ERROR 等不同等級的訊息，正好拿來練習搜尋。"),

    CLR(key="基本比對 · grep 樣式 檔案", hero="grep ERROR logs/app.log", toks=[
        ("grep", "用樣式搜尋文字的工具", "path"),
        ("ERROR", "要尋找的樣式，這裡找含 ERROR 的行", "star"),
        ("logs/app.log", "要搜尋的目標檔案", "path")]),
    S("先從最基本的用法開始：一個樣式，加上一個檔案。"),
    S("我們在 app.log 裡面，找出所有含有 ERROR 這個字的行。"),
    R("grep ERROR logs/app.log"),
    S("每一行只要出現 ERROR，就被原封不動地印了出來。"),
    S("這就是 grep 的核心：給它樣式跟檔案，它替你逐行過濾。"),

    CLR(key="-i 忽略大小寫", hero="grep -i error logs/app.log", toks=[
        ("-i", "忽略大小寫，大寫小寫一視同仁", "star"),
        ("error", "這次用小寫 error 當樣式", "path"),
        ("logs/app.log", "目標檔案", "path")]),
    S("剛剛的搜尋分大小寫，所以小寫的 error 會被漏掉。"),
    S("這時候加上 -i，就能忽略大小寫，讓大寫小寫一起命中。"),
    R("grep -i error logs/app.log"),
    S("你看，這次連小寫的 error 那一行也被抓出來了。"),
    S("面對人寫的紀錄檔，大小寫往往不一致，這個旗標很實用。"),

    CLR(key="-n 顯示行號", hero="grep -n ERROR logs/app.log", toks=[
        ("-n", "在每行前面標上行號", "star"),
        ("ERROR", "要搜尋的樣式", "path"),
        ("logs/app.log", "目標檔案", "path")]),
    S("找到了結果，常常還想知道它在檔案的第幾行。"),
    S("加上 -n，grep 就會在每一行前面標上行號。"),
    R("grep -n ERROR logs/app.log"),
    S("現在每個命中的前面都有行號，要跳去編輯就方便多了。"),
    S("很多編輯器也吃這種「檔名冒號行號」的格式，可以直接跳轉。"),

    CLR(key="-c 只算數量", hero="grep -c ERROR logs/app.log", toks=[
        ("-c", "只回報命中的行數，不印內容", "star"),
        ("ERROR", "要計數的樣式", "path"),
        ("logs/app.log", "目標檔案", "path")]),
    S("有時候我們不在乎內容，只想知道命中了幾次。"),
    S("把 -c 加上去，grep 就只回報命中的行數。"),
    R("grep -c ERROR logs/app.log"),
    S("它直接給出一個數字，省去自己用眼睛數的麻煩。"),
    S("拿來監看錯誤數量、或寫進腳本做判斷，都很方便。"),

    CLR(key="-v 反向選取", hero="grep -v INFO logs/app.log", toks=[
        ("-v", "反向選取，印出不含樣式的行", "star"),
        ("INFO", "要排除掉的樣式", "path"),
        ("logs/app.log", "目標檔案", "path")]),
    S("反過來想，有時我們要的是「不含」某個樣式的行。"),
    S("用 -v 做反向選取，這裡把所有的 INFO 雜訊都濾掉。"),
    R("grep -v INFO logs/app.log"),
    S("剩下的全是比較值得注意的非 INFO 訊息。"),
    S("想從一堆雜訊裡只留下重點時，反向選取特別好用。"),

    CLR(key="-w 整詞比對", hero="grep -w id logs/app.log", toks=[
        ("-w", "整詞比對，只配對獨立的單字", "star"),
        ("id", "要當成完整單字比對的 id", "path"),
        ("logs/app.log", "目標檔案", "path")]),
    S("直接搜尋短字 id，連 idle 和 identifier 都會被一起抓到。"),
    S("加上 -w 做整詞比對，就只配對獨立成詞的 id。"),
    R("grep -w id logs/app.log"),
    S("這次 idle 和 identifier 都被排除，只剩真正的 id。"),
    S("搜尋短字、又怕被別的單字夾帶時，整詞比對能少踩很多坑。"),

    CLR(key="-o 只印命中片段", hero="grep -o 'user=[a-z]*' logs/app.log",
        toks=[
        ("-o", "只印出命中的片段，而非整行", "star"),
        ("'user=[a-z]*'", "比對 user= 後面接的小寫字母", "path"),
        ("logs/app.log", "目標檔案", "path")]),
    S("如果我只想抽出命中的那一小段，而不是整行呢？"),
    S("用 -o 搭配樣式，就能把每個 user 等於誰單獨抽出來。"),
    R("grep -o 'user=[a-z]*' logs/app.log"),
    S("結果是一串乾淨的 user 欄位，很適合接著做後續處理。"),
    S("把它接到 sort 或 uniq，馬上就能統計出現過哪些使用者。"),

    CLR(key="-E 延伸正規表示式", hero="grep -E 'ERROR|WARN' logs/app.log",
        toks=[
        ("-E", "啟用延伸正規表示式，支援 | 等語法", "star"),
        ("'ERROR|WARN'", "用直線同時比對兩種樣式", "path"),
        ("logs/app.log", "目標檔案", "path")]),
    S("想一次找兩種樣式，可以靠正規表示式的「或」。"),
    S("用 -E 啟用延伸正規表示式，再用直線把 ERROR 跟 WARN 串起來。"),
    R("grep -E 'ERROR|WARN' logs/app.log"),
    S("這下子警告和錯誤兩種等級的訊息，都一次撈了出來。"),
    S("少了延伸模式，這個直線還得加反斜線跳脫，寫起來囉嗦多了。"),

    CLR(key="-r 遞迴搜尋目錄", hero="grep -r TODO src", toks=[
        ("-r", "遞迴搜尋整個目錄樹", "star"),
        ("TODO", "要尋找的樣式", "path"),
        ("src", "搜尋的起點目錄", "path")]),
    S("到目前為止都在搜尋單一檔案，但其實 grep 也能搜整個目錄。"),
    S("加上 -r 做遞迴搜尋，把 src 底下所有檔案裡的 TODO 都找出來。"),
    R("grep -r TODO src"),
    S("輸出會在每一行前面，標明這個 TODO 是來自哪個檔案。"),
    S("不必自己一個一個檔案點開，整棵樹一次就掃完了。"),

    CLR(key="-rl 只列出檔名", hero="grep -rl TODO src", toks=[
        ("-rl", "遞迴搜尋並只列出命中的檔名", "star"),
        ("TODO", "要尋找的樣式", "path"),
        ("src", "搜尋的起點目錄", "path")]),
    S("如果檔案很多，我可能只想知道「哪些檔案」有命中。"),
    S("把旗標合併成 -rl，就在遞迴搜尋的同時只列出命中的檔名。"),
    R("grep -rl TODO src"),
    S("結果精簡成一份檔名清單，一眼就看出該去改哪幾個檔。"),

    CLR(key="-A 命中後的文脈", hero="grep -A 1 ERROR logs/app.log", toks=[
        ("-A 1", "印出命中行，再多帶後面 1 行", "star"),
        ("ERROR", "要搜尋的樣式", "path"),
        ("logs/app.log", "目標檔案", "path")]),
    S("光看命中那一行，有時資訊不夠，還想看它後面發生了什麼。"),
    S("用 -A 1，在每個命中之後，多印出後面的 1 行當作文脈。"),
    R("grep -A 1 ERROR logs/app.log"),
    S("這樣每個錯誤的後續處理動作，也一併呈現在眼前。"),
    S("不同命中之間，grep 還會用一條分隔線幫你斷開。"),

    CLR(key="-C 命中前後的文脈", hero="grep -C 1 ERROR logs/app.log", toks=[
        ("-C 1", "印出命中行的前後各 1 行", "star"),
        ("ERROR", "要搜尋的樣式", "path"),
        ("logs/app.log", "目標檔案", "path")]),
    S("最後，如果前因後果都想看，就要前後文脈一起帶。"),
    S("用 -C 1，把每個命中行的前後各 1 行都一起印出來。"),
    R("grep -C 1 ERROR logs/app.log"),
    S("命中行被夾在上下文之間，整起事件的脈絡就清楚多了。"),
    S("掌握這幾個旗標，你就能用 grep 在文字海裡又快又準地命中目標了。"),
]
