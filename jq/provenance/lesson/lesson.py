"""Lesson: jq — 用過濾器 (filter) 在命令列裡解析 JSON.

Same tool-agnostic engine as rsync/find; only this file + setup.sh are jq-
specific. Each scene teaches one jq filter, from `.` to `@csv`, by dissecting a
`cat data.json | jq '<filter>'` pipeline. The explain sentence right before each
R() names the scene's filter token VERBATIM (e.g. a scene teaching `select` has
an S() containing "select"), so the panel reveal lands in typing-sync.
"""
from lesson import S, R, CLR

SLUG = "jq"
TITLE = "jq 教學 · 用過濾器在命令列裡解析 JSON"

SCRIPT = [
    CLR(key="jq · 在命令列裡解析 JSON"),
    S("不管是 API 回應、設定檔還是日誌，我們每天都在跟 JSON 打交道。"),
    S("jq 是命令列上的 JSON 處理器，用過濾器就能把想要的資料挑出來。"),
    S("先來看看這次要操作的 data.json 長什麼樣子。"),
    R("cat data.json"),
    S("這是一個陣列，裡面有三個人，各自帶著姓名、年齡、標籤，還有巢狀的所在城市。"),
    S("接下來，我們從最簡單的過濾器開始，一層一層往下深入。"),

    CLR(key="identity：一個點 . 原樣輸出", hero="cat data.json | jq '.'", toks=[
        ("data.json", "要解析的 JSON 檔", "path"),
        ("'.'", "identity：把輸入原封不動輸出", "star")]),
    S("第一個、也是最基本的過濾器，叫做 identity。"),
    S("它就是一個單獨的句點，把讀進來的內容原封不動地輸出。"),
    R("cat data.json | jq '.'"),
    S("輸出和輸入一模一樣，但已經被 jq 重新縮排、上了顏色。"),
    S("光是這樣，jq 就已經是個好用的 JSON 美化工具了。"),

    CLR(key=".[0] 取陣列第一個元素", hero="cat data.json | jq '.[0]'", toks=[
        ("data.json", "JSON 陣列", "path"),
        (".[0]", "取陣列的第 0 個元素", "star")]),
    S("資料是一個陣列，我們常常只想看其中一筆。"),
    S("用 .[0] 就能取出陣列的第一個元素，索引從零開始算。"),
    R("cat data.json | jq '.[0]'"),
    S("回傳的是第一個人，也就是 Ada 那一筆完整的物件。"),
    S("把零換成一或二，就能取到後面的元素。"),

    CLR(key=".name 取出欄位值", hero="cat data.json | jq '.[0].name'", toks=[
        ("data.json", "來源", "path"),
        (".name", "取出物件的 name 欄位值", "star")]),
    S("拿到一個物件之後，下一步就是讀它的欄位。"),
    S("在後面接上 .name，就能取出這個物件的 name 欄位值。"),
    R("cat data.json | jq '.[0].name'"),
    S("乾淨俐落，直接回傳字串 Ada。"),

    CLR(key=".loc.city 鑽進巢狀欄位",
        hero="cat data.json | jq '.[0].loc.city'", toks=[
        ("data.json", "來源", "path"),
        (".loc.city", "一路鑽進巢狀物件取出城市", "star")]),
    S("欄位裡面還有欄位，這就是巢狀結構。"),
    S("把鍵用點串起來寫成 .loc.city，就能一路鑽到最裡層。"),
    R("cat data.json | jq '.[0].loc.city'"),
    S("跳過中間的 loc 物件，直接拿到城市 Taipei。"),

    CLR(key=".[] 把陣列逐個攤開", hero="cat data.json | jq '.[]'", toks=[
        ("data.json", "JSON 陣列", "path"),
        (".[]", "把陣列攤開成一連串元素", "star")]),
    S("前面都只取一筆，現在我們想一次處理全部。"),
    S("用 .[] 可以把陣列攤開，變成一個個獨立的元素往下流。"),
    R("cat data.json | jq '.[]'"),
    S("三個物件被逐一輸出，這正是後面所有操作的基礎。"),

    CLR(key="| 用管線把過濾器接起來",
        hero="cat data.json | jq '.[] | .name'", toks=[
        (".[]", "先把陣列攤開", "path"),
        ("|", "把左邊的輸出接到右邊的過濾器", "star"),
        (".name", "逐一取出 name", "path")]),
    S("攤開之後，我們想對每個元素再多做一次過濾。"),
    S("jq 內部也有管線，用 | 就能把左邊的輸出送進右邊的過濾器。"),
    R("cat data.json | jq '.[] | .name'"),
    S("陣列被攤開後逐一取出 name，三個名字一次到位。"),

    CLR(key="select(...) 依條件篩選",
        hero="cat data.json | jq '.[] | select(.age > 30)'", toks=[
        (".[]", "逐個元素", "path"),
        ("select", "只保留條件成立的元素", "star"),
        (".age >", "條件：年齡大於", "path"),
        ("30", "門檻值 30", "path")]),
    S("有了管線，就能做更有用的事，例如依條件篩選。"),
    S("這次我們想留下年齡大於三十歲的人。"),
    S("把每個元素丟給 select，它只會保留條件成立的那些。"),
    R("cat data.json | jq '.[] | select(.age > 30)'"),
    S("二十八歲的 Linus 被濾掉，只剩下 Ada 和 Grace。"),

    CLR(key="map(...) 對整個陣列逐項轉換",
        hero="cat data.json | jq 'map(.age)'", toks=[
        ("data.json", "來源陣列", "path"),
        ("map", "對陣列每個元素套用過濾器", "star"),
        (".age", "取出年齡", "path")]),
    S("select 是篩選，那如果想轉換每一筆呢？"),
    S("這時候就輪到 map 出場了。"),
    S("map 會對陣列裡每個元素套用同一個過濾器，再收回成一個新陣列。"),
    R("cat data.json | jq 'map(.age)'"),
    S("三個人的年齡被抽出來，整齊地放進一個新陣列。"),

    CLR(key="keys 列出物件的所有鍵",
        hero="cat data.json | jq '.[0] | keys'", toks=[
        (".[0]", "先取第一個物件", "path"),
        ("keys", "列出物件所有的鍵", "star")]),
    S("面對陌生的 JSON，我們常想先知道它有哪些欄位。"),
    S("先取出第一個物件，再用管線接給下一個過濾器。"),
    S("keys 會把這個物件所有的鍵，排序後列成一個陣列。"),
    R("cat data.json | jq '.[0] | keys'"),
    S("age、loc、name、tags 四個鍵一目了然。"),

    CLR(key="length 量長度與元素數",
        hero="cat data.json | jq 'length'", toks=[
        ("data.json", "來源", "path"),
        ("length", "量陣列長度或物件鍵數", "star")]),
    S("知道有哪些欄位之後，數量也常常很重要。"),
    S("給陣列數元素、給物件數鍵、給字串數字元，jq 都用同一招。"),
    S("這個萬用的過濾器就叫 length，這裡我們量整個陣列。"),
    R("cat data.json | jq 'length'"),
    S("回傳 3，正好就是陣列裡的人數。"),

    CLR(key="-r 輸出純文字、去掉引號",
        hero="cat data.json | jq -r '.[].name'", toks=[
        ("data.json", "來源", "path"),
        ("-r", "raw 輸出：去掉字串的引號", "star"),
        (".[].name", "逐一取出 name", "path")]),
    S("預設 jq 輸出字串時，會幫你加上雙引號。"),
    S("如果要把結果接給其他指令，那些引號往往很礙事。"),
    S("加上 -r 旗標，就會輸出純文字、去掉外層的引號。"),
    R("cat data.json | jq -r '.[].name'"),
    S("三個名字變成乾淨的純文字，可以直接餵給下一個工具。"),

    CLR(key="-c 每筆壓成一行",
        hero="cat data.json | jq -c '.[]'", toks=[
        ("data.json", "來源", "path"),
        ("-c", "compact：每個結果壓成一行", "star"),
        (".[]", "逐個輸出元素", "path")]),
    S("jq 預設會把輸出展開成多行，方便閱讀。"),
    S("但有時候我們想要每筆一行的緊湊格式，例如做成 JSON Lines。"),
    S("這時加上 -c，就會把每個結果壓成單獨一行。"),
    R("cat data.json | jq -c '.[]'"),
    S("三個物件各自縮成一行，最適合逐行處理或寫進檔案。"),

    CLR(key="@csv 把欄位組成 CSV",
        hero="cat data.json | jq -r '.[] | [.name, .age] | @csv'", toks=[
        (".[]", "逐個元素", "path"),
        ("[.name,", "挑出 name", "path"),
        (".age]", "與 age 兩欄", "path"),
        ("@csv", "把陣列組成一行 CSV", "star")]),
    S("最後，把 JSON 轉成試算表能讀的 CSV。"),
    S("先攤開陣列，再把要的欄位收進一個陣列。"),
    S("接著交給 @csv，它會自動加好逗號與引號，輸出標準的 CSV。"),
    R("cat data.json | jq -r '.[] | [.name, .age] | @csv'"),
    S("配合 -r 去掉外層引號，每個人就成了一列 CSV 資料。"),
    S("從一個點到 @csv，這些過濾器組合起來，就能應付日常大多數的 JSON 處理了。"),
]
