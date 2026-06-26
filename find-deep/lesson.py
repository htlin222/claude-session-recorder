"""Lesson: find-deep — 把 Unix find 從「會用」練到「精通」.

完整心智模型：起點目錄 + 述詞 (predicate) + 動作 (action)。場景由最安全的
過濾述詞，一路推進到會動到檔案的動作；-exec 用唯讀的 wc -l 示範，危險的
-delete 放在最後並在旁白明確警告。每個 star/ord token 的旗標文字都逐字寫進
該場景的某句旁白，面板才會貼著打字浮現。環境由 sibling setup.sh 建立的 app/ 樹
提供（多層 .py、大小寫混搭的 .JS、>1MB 的資料檔、回填時間戳、參考檔 .stamp、
空檔與空目錄、node_modules/、以及 .tmp）。
"""
from clipkit import S, R, CLR

SLUG = "find-deep"
TITLE = "find 深入教學 · 述詞、時間、路徑與動作全攻略"

SCRIPT = [
    # ── 0. 心智模型：起點 + 述詞 + 動作 ─────────────────────────────
    CLR(key="find · 述詞與動作的完整地圖"),
    S("find 是命令列裡最強大的尋檔工具，這一課我們把它徹底拆開來看。"),
    S("它的心智模型其實只有三個部分：一個起點目錄、一連串述詞，還有最後的動作。"),
    S("述詞負責過濾，動作負責處理，沒寫動作時，find 預設就是把結果印出來。"),
    S("我們先用 tree 看看待會兒要操作的 app 專案長什麼樣子。"),
    R("tree app"),
    S("裡面有原始碼、文件、紀錄檔、相依套件，還有一個刻意放大的資料檔。"),
    S("接下來，我們從最安全的過濾述詞開始，一路推進到會動到檔案的動作。"),

    # ── 1. -name ────────────────────────────────────────────────
    CLR(key="-name 依檔名比對", hero="find app -name '*.py'", toks=[
        ("app", "搜尋的起點，從這個目錄往下找", "path"),
        ("-name", "依檔名比對，支援 * 萬用字元", "star"),
        ("'*.py'", "只挑副檔名是 .py 的檔案", "path")]),
    S("第一個、也是最常用的述詞，就是依檔名搜尋。"),
    S("從 app 出發，用 -name 比對檔名，挑出所有副檔名是 py 的檔案。"),
    R("find app -name '*.py'"),
    S("整棵樹裡的 Python 檔，不管藏得多深，全都被列了出來。"),
    S("提醒一下，樣式記得加上引號，避免被 shell 搶先展開。"),

    # ── 2. -iname ───────────────────────────────────────────────
    CLR(key="-iname 忽略大小寫", hero="find app -iname '*.js'", toks=[
        ("app", "搜尋的起點目錄", "path"),
        ("-iname", "跟 -name 一樣，但忽略大小寫", "star"),
        ("'*.js'", "所有 js 檔，不分大小寫", "path")]),
    S("如果檔名的大小寫你記不太清楚，就改用 -iname。"),
    S("這次用 -iname 比對所有 js 檔，大寫的 JS 跟小寫的 js 會一起被抓到。"),
    R("find app -iname '*.js'"),
    S("你看，Main.JS、Helper.Js 跟 index.js，通通都被找了出來。"),

    # ── 3. -type d ──────────────────────────────────────────────
    CLR(key="-type 限定檔案或目錄", hero="find app -type d", toks=[
        ("app", "搜尋的起點目錄", "path"),
        ("-type d", "只列出目錄，d 就是 directory", "star")]),
    S("有時候我們只想看資料夾，不想被一堆檔案洗版。"),
    S("這次用 -type d，只列出 app 底下的目錄。"),
    R("find app -type d"),
    S("結果只剩一個個資料夾，檔案全都被濾掉了。"),

    # ── 4. -size ────────────────────────────────────────────────
    CLR(key="-size 依檔案大小過濾", hero="find app -type f -size +1M", toks=[
        ("app", "搜尋的起點目錄", "path"),
        ("-type f", "只看一般檔案", "ord"),
        ("-size", "依檔案大小過濾", "star"),
        ("+1M", "大於 1 MB，加號代表「以上」", "path")]),
    S("想揪出佔空間的大檔該怎麼做？"),
    S("先用 -type f 只看一般檔案，再加上 -size，配合 1M 找出大於一 MB 的檔案。"),
    R("find app -type f -size +1M"),
    S("只有那個刻意放大的資料檔，超過了門檻被挑出來。"),

    # ── 5. -empty ───────────────────────────────────────────────
    CLR(key="-empty 找空檔案與空目錄", hero="find app -empty", toks=[
        ("app", "搜尋的起點目錄", "path"),
        ("-empty", "命中空檔案，也命中空目錄", "star")]),
    S("專案裡常常有沒寫東西的佔位檔，或忘了清的空資料夾。"),
    S("用 -empty 一次就能把空檔案跟空目錄都找出來。"),
    R("find app -empty"),
    S("一個零位元組的檔案，和一個空蕩蕩的目錄，都被點名了。"),

    # ── 6. -maxdepth ────────────────────────────────────────────
    CLR(key="-maxdepth 限制往下深度", hero="find app -maxdepth 1 -type f", toks=[
        ("app", "搜尋的起點目錄", "path"),
        ("-maxdepth 1", "只往下找一層，不深入子目錄", "star"),
        ("-type f", "只看一般檔案", "ord")]),
    S("預設的 find 會把所有子目錄一路鑽到底。"),
    S("加上 -maxdepth 1，就只看最上面一層，再用 -type f 只留檔案。"),
    R("find app -maxdepth 1 -type f"),
    S("這次只列出 app 最頂層的那幾個檔案，深處的全都沒出現。"),

    # ── 7. -mindepth ────────────────────────────────────────────
    CLR(key="-mindepth 跳過最上層", hero="find app -mindepth 2 -name '*.py'", toks=[
        ("app", "搜尋的起點目錄", "path"),
        ("-mindepth 2", "至少要往下兩層才算數", "star"),
        ("-name '*.py'", "再依檔名比對 py 檔", "path")]),
    S("有了上限，當然也有下限。"),
    S("用 -mindepth 2，要求結果至少在第二層以下，再比對 py 檔名。"),
    R("find app -mindepth 2 -name '*.py'"),
    S("最頂層那個 main.py 被跳過了，只剩深處子目錄裡的原始碼。"),

    # ── 8. -mtime ───────────────────────────────────────────────
    CLR(key="-mtime 依修改時間", hero="find app -type f -mtime -1", toks=[
        ("app", "搜尋的起點目錄", "path"),
        ("-type f", "只看一般檔案", "ord"),
        ("-mtime -1", "最近一天內改過，減號代表「以內」", "star")]),
    S("接著換個維度，依照時間來篩。"),
    S("用 -type f 只看檔案，再用 -mtime -1，撈出最近一天內被改過的檔案。"),
    R("find app -type f -mtime -1"),
    S("整棵樹裡，只有剛剛動過的那幾個檔案被挑了出來。"),

    # ── 9. -newer ───────────────────────────────────────────────
    CLR(key="-newer 比參考檔還新", hero="find app -type f -newer app/.stamp", toks=[
        ("app", "搜尋的起點目錄", "path"),
        ("-type f", "只看一般檔案", "ord"),
        ("-newer", "比這個參考檔更新的才算", "star"),
        ("app/.stamp", "拿來比對時間的基準檔", "path")]),
    S("如果不想心算天數，也可以直接拿一個檔案當基準。"),
    S("用 -newer 搭配 app 裡的 .stamp 參考檔，找出比它還新的所有檔案。"),
    R("find app -type f -newer app/.stamp"),
    S("凡是在那個時間點之後改過的檔案，全都浮上來了。"),

    # ── 10. -path ───────────────────────────────────────────────
    CLR(key="-path 比對整段路徑", hero="find app -path '*/logs/*'", toks=[
        ("app", "搜尋的起點目錄", "path"),
        ("-path", "比對的是整段路徑，不只是檔名", "star"),
        ("'*/logs/*'", "路徑中任何一段是 logs 就命中", "path")]),
    S("有時我們要找的，是位在某個特定資料夾底下的東西。"),
    S("這時改用 -path，讓樣式去比對整段路徑，鎖定 logs 目錄裡的檔案。"),
    R("find app -path '*/logs/*'"),
    S("不論檔名叫什麼，只要路徑經過 logs，就會被收進結果。"),

    # ── 11. -prune ──────────────────────────────────────────────
    CLR(key="-prune 整個目錄跳過",
        hero="find app -name node_modules -prune -o -type f -print", toks=[
        ("app", "搜尋的起點目錄", "path"),
        ("-name node_modules", "先比對到名為 node_modules 的目錄", "path"),
        ("-prune", "命中就把整棵子樹直接跳過", "star"),
        ("-o", "否則就切到另一個分支", "path"),
        ("-type f -print", "印出其餘的一般檔案", "path")]),
    S("像 node_modules 這種又大又沒必要掃的目錄，最好整個跳過。"),
    S("用 -prune，一旦比對到 node_modules 就剪掉整棵子樹，其餘檔案照常印出。"),
    R("find app -name node_modules -prune -o -type f -print"),
    S("結果裡完全看不到相依套件的內容，搜尋也快了不少。"),

    # ── 12. -not ────────────────────────────────────────────────
    CLR(key="-not 反向選擇", hero="find app -type f -not -name '*.py'", toks=[
        ("app", "搜尋的起點目錄", "path"),
        ("-type f", "只看一般檔案", "ord"),
        ("-not", "把後面的條件整個反過來", "star"),
        ("-name '*.py'", "原本是比對 py 檔名", "path")]),
    S("述詞也可以反過來用，找出「不符合」的那些。"),
    S("用 -type f 只看檔案，再用 -not 把 -name 的條件反轉，排除掉所有 py 檔。"),
    R("find app -type f -not -name '*.py'"),
    S("剩下的都是非 Python 的檔案，文件、設定、紀錄一個不漏。"),

    # ── 13. -exec（唯讀動作）─────────────────────────────────────
    CLR(key="-exec 對每個結果執行命令（唯讀）",
        hero="find app -name '*.log' -exec wc -l {} +", toks=[
        ("app", "搜尋的起點目錄", "path"),
        ("-name '*.log'", "先挑出所有 log 檔", "path"),
        ("-exec", "對每個結果執行指定的命令", "star"),
        ("wc -l {} +", "用 wc -l 數行數，{} 代入檔名", "path")]),
    S("過濾完之後，我們終於要對結果做點事，這就輪到動作登場。"),
    S("用 -exec 對每個 log 檔執行命令，這裡跑唯讀的 wc -l 只數行數，不會更動檔案。"),
    R("find app -name '*.log' -exec wc -l {} +"),
    S("結尾的加號會把多個檔名併成一次呼叫，效率比一個一個跑高得多。"),

    # ── 14. -delete（危險動作，最後示範）────────────────────────
    CLR(key="-delete 直接刪除（危險！最後示範）",
        hero="find app -name '*.tmp' -delete", toks=[
        ("app", "搜尋的起點目錄", "path"),
        ("-name '*.tmp'", "先精準鎖定 tmp 暫存檔", "path"),
        ("-delete", "直接刪除，沒有資源回收筒，務必小心", "star")]),
    S("最後一個動作最危險，請務必小心使用。"),
    S("用 -delete 會直接刪掉比對到的檔案，沒有資源回收筒、也救不回來。"),
    S("所以刪之前，強烈建議先把 -delete 拿掉、單純印出結果確認一遍。"),
    R("find app -name '*.tmp' -delete"),
    S("確認過範圍只有 tmp 暫存檔，這才安心地讓它一次清乾淨。"),
    S("從述詞到動作，這套地圖在手，你就能用 find 精準地搞定任何尋檔任務了。"),
]
