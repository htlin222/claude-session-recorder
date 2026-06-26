"""Lesson: tar — 把資料夾打包、壓縮、再解開的完整流程.

A third lesson on the same tool-agnostic engine. Teaches macOS 的 tar
（bsdtar）的可攜旗標：-c 建立、-f 指定檔名、-v 顯示過程、-t 列出、-r 追加、
-z gzip 壓縮、-czf 併寫、-tzf 列出壓縮檔、--exclude 過濾、-xzf -C 解開到指定
目錄。每個解說句都逐字帶到該情境的 star/ord 旗標文字，面板才會貼著打字浮現。
情境順序＝建立 → 列出 → 解開（安全順序）。環境由 sibling setup.sh 建立。
"""
from lesson import S, R, CLR

SLUG = "tar"
TITLE = "tar 打包教學 · 從建立、列出到解開"

SCRIPT = [
    CLR(key="tar · 把資料夾打包、壓縮、再解開"),
    S("tar 是 Unix 世界裡最經典的打包工具，能把整個資料夾收進一個檔案裡。"),
    S("動手之前，先看看待會要打包的 project 資料夾裡有什麼。"),
    R("tree project"),
    S("裡面有原始碼、文件，還有好幾個 log 紀錄檔。"),
    S("我們特地放了一個超過 1MB 的大檔，待會用來示範壓縮的效果。"),
    S("接著就照建立、列出、再解開的安全順序，把 tar 完整走一遍。"),

    CLR(key="-c 建立一個封存檔", hero="tar -c -f project.tar project", toks=[
        ("-c", "建立一個新的封存檔", "star"),
        ("-f", "指定輸出的封存檔名", "ord"),
        ("project.tar", "輸出的封存檔", "path"),
        ("project", "要打包的來源資料夾", "path")]),
    S("第一步，先學會用 tar 把一個資料夾打包成封存檔。"),
    S("這裡用 -c 建立一個全新的封存檔，再用 -f 指定輸出的檔名。"),
    R("tar -c -f project.tar project"),
    S("命令安安靜靜地跑完，project.tar 就生出來了。"),
    S("整個 project 資料夾，現在都被收進這一個檔案裡。"),
    S("這就是 tar 最核心的動作，把多個檔案聚成一包。"),

    CLR(key="-f 指定輸出的封存檔名", hero="tar -c -f docs.tar project/docs", toks=[
        ("-c", "建立封存檔", "ord"),
        ("-f", "指定輸出的檔名", "star"),
        ("docs.tar", "這次輸出叫 docs.tar", "path"),
        ("project/docs", "只打包 docs 子資料夾", "path")]),
    S("剛剛 -f 後面接的檔名，其實完全由你決定。"),
    S("這次一樣用 -c 建立，但用 -f 改叫 docs.tar，而且只打包 docs 子資料夾。"),
    R("tar -c -f docs.tar project/docs"),
    S("於是我們得到一個只裝文件的小封存檔。"),
    S("可見 -f 決定檔名，後面的路徑決定打包的範圍。"),

    CLR(key="-v 顯示打包過程", hero="tar -c -v -f project.tar project", toks=[
        ("-c", "建立封存檔", "ord"),
        ("-v", "顯示每個被打包的檔案", "star"),
        ("-f", "指定輸出檔名", "ord"),
        ("project.tar", "輸出的封存檔", "path"),
        ("project", "來源資料夾", "path")]),
    S("打包的時候，tar 預設是安靜的，不會印任何東西。"),
    S("想看清楚到底收了哪些檔，就加上 -v 顯示過程，再配合 -c 跟 -f。"),
    R("tar -c -v -f project.tar project"),
    S("這一次，每個被打包的檔案都一行一行印了出來。"),
    S("在打包大目錄時，-v 特別讓人安心。"),
    S("你能即時確認，沒有漏掉任何想要的檔案。"),

    CLR(key="-t 列出封存檔內容（不解開）", hero="tar -t -f project.tar", toks=[
        ("-t", "列出封存檔內容，但不解開", "star"),
        ("-f", "指定要讀取的封存檔", "ord"),
        ("project.tar", "要檢視的封存檔", "path")]),
    S("封存檔做好之後，怎麼在不解開的情況下看內容呢？"),
    S("答案是 -t，它會列出封存檔裡的清單，搭配 -f 指定要讀哪個檔。"),
    R("tar -t -f project.tar"),
    S("檔案清單整齊地列出來，但磁碟上沒有任何東西被解開。"),
    S("-t 是動手解壓之前，先檢查內容的好習慣。"),
    S("尤其拿到來路不明的封存檔時，更該先看一眼。"),

    CLR(key="-r 把檔案追加進既有封存檔", hero="tar -r -f project.tar notes.txt", toks=[
        ("-r", "把檔案追加到既有封存檔", "star"),
        ("-f", "指定目標封存檔", "ord"),
        ("project.tar", "要追加進去的封存檔", "path"),
        ("notes.txt", "新加入的檔案", "path")]),
    S("有時候封存檔已經建好，卻想再塞一個檔案進去。"),
    S("這時用 -r 把檔案追加到既有封存檔，一樣用 -f 指定目標。"),
    R("tar -r -f project.tar notes.txt"),
    S("notes.txt 就被接到 project.tar 的尾端了。"),
    S("要記得 -r 只能用在沒有壓縮的 tar 檔上。"),

    CLR(key="-z 邊打包邊用 gzip 壓縮", hero="tar -c -z -f project.tar.gz project", toks=[
        ("-c", "建立封存檔", "ord"),
        ("-z", "邊打包邊用 gzip 壓縮", "star"),
        ("-f", "指定輸出檔名", "ord"),
        ("project.tar.gz", "壓縮後的封存檔", "path"),
        ("project", "來源資料夾", "path")]),
    S("接下來談壓縮，讓封存檔的體積變得更小。"),
    S("加上 -z，就能邊打包邊用 gzip 壓縮，再配合 -c 跟 -f 輸出。"),
    R("tar -c -z -f project.tar.gz project"),
    S("這次的輸出多了 .gz 結尾，檔案明顯瘦了一圈。"),
    S("剛剛那個大檔，正好讓 -z 的壓縮效果看得很清楚。"),
    S("壓縮後的封存檔，傳輸或備份都更省空間。"),

    CLR(key="-czf 把常用旗標併成一串", hero="tar -czf project.tgz project", toks=[
        ("-czf", "建立、壓縮、指定檔名併成一串", "star"),
        ("project.tgz", "輸出的壓縮封存檔", "path"),
        ("project", "來源資料夾", "path")]),
    S("每次都要分開寫 -c、-z 跟 -f，其實有點囉嗦。"),
    S("tar 允許把它們併成一串，寫成 -czf，意思完全一樣。"),
    R("tar -czf project.tgz project"),
    S("一行就完成建立、壓縮、命名，輸出成 project.tgz。"),
    S("-czf 是日常打包最常見的縮寫寫法。"),
    S("把它記成肌肉記憶，之後會省下很多打字。"),

    CLR(key="-tzf 列出壓縮封存檔的內容", hero="tar -tzf project.tgz", toks=[
        ("-tzf", "列出壓縮封存檔的內容", "star"),
        ("project.tgz", "要檢視的壓縮封存檔", "path")]),
    S("那要列出一個已經壓縮過的封存檔呢？"),
    S("同樣把列出跟解壓縮併起來，用 -tzf 一次搞定。"),
    R("tar -tzf project.tgz"),
    S("壓縮檔裡的內容，照樣一覽無遺。"),
    S("確認清單沒問題，就能放心進行下一步。"),

    CLR(key="--exclude 打包時排除不要的檔",
        hero="tar -czf clean.tgz --exclude='*.log' project", toks=[
        ("-czf", "建立並壓縮", "ord"),
        ("clean.tgz", "乾淨版的輸出檔", "path"),
        ("--exclude", "排除符合樣式的檔案", "star"),
        ("'*.log'", "排除所有 .log 檔", "path"),
        ("project", "來源資料夾", "path")]),
    S("打包時，常常有些檔案根本不想收進去，比如那些 log。"),
    S("這時加上 --exclude，再配合 -czf，就能把符合樣式的檔案排除掉。"),
    R("tar -czf clean.tgz --exclude='*.log' project"),
    S("輸出的 clean.tgz，就是一個不含任何 log 的乾淨版本。"),
    S("--exclude 還可以重複使用，一次過濾掉多種不要的檔案。"),
    S("打包前先想清楚要排除什麼，封存檔會乾淨很多。"),

    CLR(key="-xzf -C 解開到指定目錄", hero="tar -xzf project.tgz -C restored", toks=[
        ("-xzf", "解開 gzip 壓縮的封存檔", "star"),
        ("project.tgz", "要解開的壓縮封存檔", "path"),
        ("-C", "解開到指定的目錄", "ord"),
        ("restored", "解開的目標資料夾", "path")]),
    S("最後一步，把壓縮封存檔解開，驗證內容是不是完整。"),
    S("用 -xzf 解開 gzip 壓縮的封存檔，再用 -C 指定要解到哪個目錄。"),
    R("tar -xzf project.tgz -C restored"),
    S("所有檔案，都乖乖地還原到 restored 目錄底下了。"),
    S("有了 -C，就不會把一堆檔案灑得到處都是。"),
    S("從建立、列出到解開，tar 的完整流程就走完一輪了。"),
]
