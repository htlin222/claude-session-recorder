"""Lesson: awk — 用一行指令切欄位、篩選與彙總欄位式資料.

A third lesson on the SAME tool-agnostic engine. It teaches macOS 內建的
one-true-awk（非 GNU gawk），只用可攜寫法、無 gawk 擴充。每個 R() 都是
`cat data.<ext> | awk '...'`：輸入固定、非互動、會自我結束。每個場景只教一個
awk 觀念，star token 即該特性，並在「執行前那一句」旁白中逐字出現，讓右側
解說面板在打字時同步亮起（見三條 HARD RULE）。所有指令都不含雙引號與反斜線，
以符合引擎 `Type "{cmd}"` 的 tape 寫法。
"""
from clipkit import S, R, CLR

SLUG = "awk"
TITLE = "awk 教學 · 用一行指令切欄位、篩選與彙總資料"

SCRIPT = [
    # ---- intro tour: 認識資料與整體流程 ----
    CLR(key="awk · 一行指令處理欄位式資料"),
    S("awk 是一個逐列處理文字的小工具，特別擅長欄位式的資料。"),
    S("我們準備了一份員工資料，每一列是名字、部門和薪水，用空白分隔。"),
    S("先用 cat 把整份 data.txt 印出來看看。"),
    R("cat data.txt"),
    S("可以看到六位員工，三個欄位排得整整齊齊。"),
    S("另外還有一份逗號分隔的版本 data.csv，等一下示範分隔符時會用到。"),
    R("cat data.csv"),
    S("這份資料刻意設計過，薪水有的高於五千、有的低於五千，方便後面示範篩選。"),
    S("接下來，我們就用 awk 一個觀念一個觀念地把資料切開、篩選、再彙總。"),

    # ---- 1) print $0 ----
    CLR(key="print $0 印出整列", hero="cat data.txt | awk '{print $0}'", toks=[
        ("cat data.txt", "把每一列文字送進管線", "path"),
        ("awk", "逐列處理文字的工具", "ord"),
        ("print $0", "$0 代表一整列原始內容", "star")]),
    S("最基本的起手式，是把讀進來的每一列原樣印出。"),
    S("這次用 awk 搭配 print $0，把每一列原封不動地印出來。"),
    R("cat data.txt | awk '{print $0}'"),
    S("輸出和原始檔案一模一樣，代表 awk 真的逐列處理過了每一行。"),

    # ---- 2) $1 ----
    CLR(key="$1 取第一個欄位", hero="cat data.txt | awk '{print $1}'", toks=[
        ("cat data.txt", "資料來源", "path"),
        ("awk", "欄位處理工具", "ord"),
        ("$1", "第一個欄位，也就是名字", "star")]),
    S("awk 會自動把每一列依空白切成欄位，這正是它的看家本領。"),
    S("這次改用 awk 取出 $1，也就是每一列的第一個欄位。"),
    R("cat data.txt | awk '{print $1}'"),
    S("結果只剩下一串名字，部門和薪水都被留在後面沒印出來。"),
    S("這種只挑一欄的能力，正是處理欄位式資料最常用到的第一步。"),

    # ---- 3) $1, $3 一次多欄 ----
    CLR(key="$1, $3 一次印多欄", hero="cat data.txt | awk '{print $1, $3}'",
        toks=[
        ("cat data.txt", "資料來源", "path"),
        ("awk", "欄位處理工具", "ord"),
        ("$1, $3", "一次印出名字與薪水兩欄", "star")]),
    S("想同時看好幾欄時，把欄位用逗號隔開就行了。"),
    S("這次讓 awk 用 $1, $3，一次印出名字和薪水兩欄。"),
    R("cat data.txt | awk '{print $1, $3}'"),
    S("逗號會讓兩欄之間自動補上一個空白，看起來剛好對齊。"),

    # ---- 4) -F 分隔符 ----
    CLR(key="-F 指定欄位分隔符", hero="cat data.csv | awk -F, '{print $2}'", toks=[
        ("cat data.csv", "這次換成逗號分隔的 CSV", "path"),
        ("awk", "欄位處理工具", "ord"),
        ("-F", "指定欄位分隔符，這裡是逗號", "star"),
        ("$2", "印出第二欄，也就是部門", "path")]),
    S("如果資料不是用空白分隔，而是逗號呢？"),
    S("這次資料換成 CSV，用 awk -F 指定逗號當分隔符，再取出第二欄。"),
    R("cat data.csv | awk -F, '{print $2}'"),
    S("即使是逗號分隔的 CSV，部門欄位一樣被乾淨地切了出來。"),

    # ---- 5) NR 列號 ----
    CLR(key="NR 目前的列號", hero="cat data.txt | awk '{print NR, $1}'", toks=[
        ("cat data.txt", "資料來源", "path"),
        ("awk", "欄位處理工具", "ord"),
        ("NR", "目前處理到第幾列", "star"),
        ("$1", "同時印出名字", "path")]),
    S("awk 還準備了一些好用的內建變數。"),
    S("這次用 awk 印出 NR，看看目前處理到第幾列。"),
    R("cat data.txt | awk '{print NR, $1}'"),
    S("每一列前面都多了一個遞增的編號，就像幫資料加上行號一樣。"),

    # ---- 6) NF 欄數 ----
    CLR(key="NF 這一列的欄位數", hero="cat data.txt | awk '{print NF}'", toks=[
        ("cat data.txt", "資料來源", "path"),
        ("awk", "欄位處理工具", "ord"),
        ("NF", "這一列被切成幾個欄位", "star")]),
    S("另一個內建變數，會告訴你這一列總共有幾欄。"),
    S("這次用 awk 印出 NF，看看每一列被切成幾個欄位。"),
    R("cat data.txt | awk '{print NF}'"),
    S("每一列都印出三，因為我們的資料剛好都是三個欄位。"),
    S("當你不確定資料有幾欄，或想檢查格式有沒有跑掉時，這招特別好用。"),

    # ---- 7) /Eng/ 樣式比對 ----
    CLR(key="/Eng/ 樣式比對才動作", hero="cat data.txt | awk '/Eng/{print $1}'",
        toks=[
        ("cat data.txt", "資料來源", "path"),
        ("awk", "欄位處理工具", "ord"),
        ("/Eng/", "只對含有 Eng 的列動作", "star"),
        ("$1", "印出符合者的名字", "path")]),
    S("awk 也可以只挑出符合某個樣式的列來處理。"),
    S("這次讓 awk 只對符合 /Eng/ 的列動作，印出工程部門的人。"),
    R("cat data.txt | awk '/Eng/{print $1}'"),
    S("只有部門欄包含 Eng 的那幾位被留了下來，其餘的列都被跳過。"),
    S("斜線中間放的其實是正規表示式，所以樣式可以寫得比這更靈活。"),

    # ---- 8) $3 > 5000 比較 ----
    CLR(key="$3 > 5000 用比較篩選",
        hero="cat data.txt | awk '$3 > 5000 {print $1, $3}'", toks=[
        ("cat data.txt", "資料來源", "path"),
        ("awk", "欄位處理工具", "ord"),
        ("$3 > 5000", "用比較式當作篩選條件", "star")]),
    S("除了文字樣式，也可以直接拿欄位的數值來比大小。"),
    S("這次用 awk 加上條件 $3 > 5000，把薪水高於門檻的人篩出來。"),
    R("cat data.txt | awk '$3 > 5000 {print $1, $3}'"),
    S("只剩下薪水超過五千的人，其他人因為不符合條件被濾掉了。"),

    # ---- 9) END 收尾 ----
    CLR(key="END 收尾時執行一次", hero="cat data.txt | awk 'END{print NR}'", toks=[
        ("cat data.txt", "資料來源", "path"),
        ("awk", "欄位處理工具", "ord"),
        ("END", "資料全部讀完後才執行", "star"),
        ("NR", "這時剛好等於總列數", "ord")]),
    S("有些事情我們希望等到資料讀完才做一次。"),
    S("這次用 awk 的 END，等資料全部讀完後才印出 NR，也就是總列數。"),
    R("cat data.txt | awk 'END{print NR}'"),
    S("它只印出一個數字六，正是整份資料的列數。"),

    # ---- 10) sum += $3 累加 ----
    CLR(key="sum += $3 累加器求總和",
        hero="cat data.txt | awk '{sum += $3} END{print sum}'", toks=[
        ("cat data.txt", "資料來源", "path"),
        ("awk", "欄位處理工具", "ord"),
        ("sum += $3", "每讀一列就把薪水累加起來", "star"),
        ("END", "最後一次印出總和", "ord")]),
    S("把 END 和一個累加器搭在一起，就能做出彙總。"),
    S("這次讓 awk 用 sum += $3 一路累加，再用 END 印出薪水的總和。"),
    R("cat data.txt | awk '{sum += $3} END{print sum}'"),
    S("一行指令就把六個人的薪水加總起來，完全不用另外寫迴圈。"),
    S("累加器這個技巧，是用 awk 做各種統計彙總的核心。"),

    # ---- 11) BEGIN 開頭 ----
    CLR(key="BEGIN 開頭先做一件事",
        hero="cat data.txt | awk 'BEGIN{print NR} END{print NR}'", toks=[
        ("cat data.txt", "資料來源", "path"),
        ("awk", "欄位處理工具", "ord"),
        ("BEGIN", "讀資料前先執行一次", "star"),
        ("END", "讀完後再執行一次", "ord")]),
    S("和 END 相對的，是在最開頭執行的 BEGIN 區塊。"),
    S("這次用 awk 的 BEGIN 在開頭先跑一次，再用 END 在結尾跑一次。"),
    R("cat data.txt | awk 'BEGIN{print NR} END{print NR}'"),
    S("開頭印出零代表還沒讀任何列，結尾印出六代表全部讀完了。"),

    # ---- 12) -v 外部變數 ----
    CLR(key="-v 從外部帶入變數",
        hero="cat data.txt | awk -v min=5000 '$3 > min {print $1, $3}'", toks=[
        ("cat data.txt", "資料來源", "path"),
        ("awk", "欄位處理工具", "ord"),
        ("-v", "從外部把變數帶進 awk", "star"),
        ("min=5000", "這裡設定門檻變數 min", "path")]),
    S("如果門檻想從外面傳進來，而不是寫死在程式裡呢？"),
    S("這次用 awk -v 從外面帶進變數 min，把門檻設成五千。"),
    R("cat data.txt | awk -v min=5000 '$3 > min {print $1, $3}'"),
    S("結果和寫死數字時一樣，但現在只要改參數就能換門檻，更有彈性。"),
    S("寫成腳本時，這讓同一段 awk 可以重複套用在不同的條件上。"),

    # ---- 13) sum / NR 平均（capstone）----
    CLR(key="sum / NR 算出平均薪水",
        hero="cat data.txt | awk '{sum += $3} END{print sum / NR}'", toks=[
        ("cat data.txt", "資料來源", "path"),
        ("awk", "欄位處理工具", "ord"),
        ("sum += $3", "先把薪水逐列累加", "ord"),
        ("sum / NR", "總和除以列數就是平均", "star")]),
    S("最後把前面學到的東西串起來，算一個平均值。"),
    S("最後讓 awk 用 sum += $3 加總，再算 sum / NR，得到平均薪水。"),
    R("cat data.txt | awk '{sum += $3} END{print sum / NR}'"),
    S("總和除以列數，平均薪水一行就算了出來。"),
    S("把這些觀念組合起來，你就能用一行 awk 切欄位、篩選又彙總了。"),
]
